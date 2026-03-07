"""
Data loaders for ingesting content from various sources.

This module provides loader classes for extracting content from YouTube videos,
web pages, and PDF documents, returning LangChain Document objects with metadata.
"""

from typing import List, Optional
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import re

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from langchain_core.documents import Document
import requests

# Optional Whisper import for fallback
try:
    import whisper
    import yt_dlp
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


class YouTubeLoader:
    """
    Loader for extracting transcripts from YouTube videos.
    
    Uses youtube-transcript-api to fetch video subtitles and returns
    them as LangChain Document objects with video metadata.
    Falls back to Whisper for transcription if subtitles are unavailable.
    """
    
    def __init__(self, use_whisper_fallback: bool = True, whisper_model: str = "base", filter_ads: bool = True):
        """
        Initialize the YouTube loader.
        
        Args:
            use_whisper_fallback: Whether to use Whisper as fallback (default: True)
            whisper_model: Whisper model size to use (tiny, base, small, medium, large)
            filter_ads: Whether to filter out common ad/sponsored content patterns (default: True)
        """
        self.use_whisper_fallback = use_whisper_fallback and WHISPER_AVAILABLE
        self.whisper_model = whisper_model
        self.filter_ads = filter_ads
        self._whisper = None
    
    @staticmethod
    def _filter_sponsored_content(text: str) -> str:
        """
        Filter out common sponsored/commercial content patterns from transcript.
        
        This removes common phrases associated with sponsorships, ads, and promotional content.
        
        Args:
            text: Original transcript text
            
        Returns:
            Filtered text with sponsored content removed
        """
        # Common sponsored content patterns (case-insensitive)
        ad_patterns = [
            r'this video is sponsored by[\s\S]{0,200}?(?=\.|$)',
            r'today\'?s sponsor is[\s\S]{0,200}?(?=\.|$)',
            r'brought to you by[\s\S]{0,200}?(?=\.|$)',
            r'thanks to our sponsor[\s\S]{0,200}?(?=\.|$)',
            r'special thanks to[\s\S]{0,200}?for sponsoring',
            r'use code[\s\S]{0,100}?for[\s\S]{0,50}?(?:discount|off)',
            r'visit[\s\S]{0,100}?\.com[\s\S]{0,50}?(?:for|to get)',
            r'check out the link in the description[\s\S]{0,100}?(?=\.|$)',
            r'link in the description below[\s\S]{0,100}?(?=\.|$)',
            r'don\'?t forget to (?:like and subscribe|subscribe|like this video)[\s\S]{0,100}?(?=\.|!|$)',
            r'smash that like button[\s\S]{0,100}?(?=\.|!|$)',
            r'hit the (?:notification bell|bell icon)[\s\S]{0,100}?(?=\.|!|$)',
            r'subscribe to (?:my|our) channel[\s\S]{0,100}?(?=\.|!|$)',
            r'follow (?:me|us) on[\s\S]{0,100}?(?:instagram|twitter|facebook|tiktok|social media)[\s\S]{0,100}?(?=\.|!|$)',
        ]
        
        filtered_text = text
        for pattern in ad_patterns:
            filtered_text = re.sub(pattern, '', filtered_text, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        filtered_text = re.sub(r'\s+', ' ', filtered_text).strip()
        
        return filtered_text
    
    @staticmethod
    def _extract_video_id(video_url: str) -> Optional[str]:
        """
        Extract the video ID from a YouTube URL.
        
        Args:
            video_url: YouTube video URL (various formats supported)
            
        Returns:
            Video ID string or None if not found
        """
        # Handle different YouTube URL formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
            r'youtube\.com\/embed\/([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, video_url)
            if match:
                return match.group(1)
        
        # Try parsing as query parameter
        try:
            parsed = urlparse(video_url)
            if 'youtube.com' in parsed.netloc:
                query_params = parse_qs(parsed.query)
                if 'v' in query_params:
                    return query_params['v'][0]
        except Exception:
            pass
        
        return None
    
    def _transcribe_with_whisper(self, video_url: str, video_id: str) -> str:
        """
        Transcribe YouTube video audio using Whisper.
        
        Args:
            video_url: URL of the YouTube video
            video_id: YouTube video ID
            
        Returns:
            Transcribed text
            
        Raises:
            ValueError: If transcription fails
        """
        if not WHISPER_AVAILABLE:
            raise ValueError("Whisper is not available. Install with: pip install openai-whisper yt-dlp")
        
        try:
            import tempfile
            import os
            
            # Load Whisper model (lazy loading)
            if self._whisper is None:
                self._whisper = whisper.load_model(self.whisper_model)
            
            # Download audio using yt-dlp
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_file = os.path.join(temp_dir, f"{video_id}.mp3")
                
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(temp_dir, video_id),
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                
                # Transcribe with Whisper
                result = self._whisper.transcribe(audio_file)
                return result['text']
                
        except Exception as e:
            raise ValueError(f"Failed to transcribe video with Whisper: {str(e)}")
    
    def load_transcript(self, video_url: str) -> Document:
        """
        Load transcript from a YouTube video.
        
        Attempts to fetch subtitles using youtube-transcript-api first.
        If subtitles are unavailable, falls back to Whisper transcription.
        
        Args:
            video_url: URL of the YouTube video
            
        Returns:
            LangChain Document with transcript text and metadata
            
        Raises:
            ValueError: If video ID cannot be extracted or transcript unavailable
        """
        video_id = self._extract_video_id(video_url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {video_url}")
        
        transcript_method = 'youtube-transcript-api'
        
        try:
            # Try to fetch transcript using youtube-transcript-api
            # Note: API changed - now requires instantiation and uses fetch() method
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id, languages=['en'])
            
            # Combine transcript segments into full text
            # transcript is a FetchedTranscript object with items that have .text attribute
            full_text = " ".join([entry.text for entry in transcript])
            
            # Filter out sponsored/commercial content if enabled
            if self.filter_ads:
                full_text = self._filter_sponsored_content(full_text)
            
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            # Fallback to Whisper if subtitles are unavailable
            if self.use_whisper_fallback:
                try:
                    full_text = self._transcribe_with_whisper(video_url, video_id)
                    transcript_method = 'whisper'
                    
                    # Filter out sponsored/commercial content if enabled
                    if self.filter_ads:
                        full_text = self._filter_sponsored_content(full_text)
                except Exception as whisper_error:
                    raise ValueError(
                        f"Failed to load transcript for video {video_id}. "
                        f"Subtitles unavailable: {str(e)}. "
                        f"Whisper fallback failed: {str(whisper_error)}"
                    )
            else:
                raise ValueError(f"Failed to load transcript for video {video_id}: {str(e)}")
        
        except Exception as e:
            raise ValueError(f"Failed to load transcript for video {video_id}: {str(e)}")
        
        # Create metadata
        metadata = {
            'source': 'youtube',
            'url': video_url,
            'video_id': video_id,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'transcript',
            'transcript_method': transcript_method
        }
        
        return Document(page_content=full_text, metadata=metadata)


class WebLoader:
    """
    Loader for extracting content from web pages.
    
    Uses BeautifulSoup to parse HTML and extract main content,
    filtering out navigation, ads, and other non-content elements.
    """
    
    def __init__(self, timeout: int = 10):
        """
        Initialize the web loader.
        
        Args:
            timeout: Request timeout in seconds (default: 10)
        """
        self.timeout = timeout
    
    def load_webpage(self, url: str) -> Document:
        """
        Load content from a web page.
        
        Args:
            url: URL of the web page to load
            
        Returns:
            LangChain Document with page content and metadata
            
        Raises:
            ValueError: If page cannot be fetched or parsed
        """
        try:
            # Fetch the page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script, style, and navigation elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Extract text from main content areas
            # Try to find main content container
            main_content = None
            for tag in ['main', 'article', 'div[role="main"]']:
                main_content = soup.find(tag)
                if main_content:
                    break
            
            # If no main content found, use body
            if not main_content:
                main_content = soup.find('body')
            
            # Extract text
            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ''
            
            # Create metadata
            metadata = {
                'source': 'web',
                'url': url,
                'title': title_text,
                'timestamp': datetime.now().isoformat(),
                'content_type': 'webpage'
            }
            
            return Document(page_content=text, metadata=metadata)
            
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch webpage {url}: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse webpage {url}: {str(e)}")


class PDFLoader:
    """
    Loader for extracting text from PDF documents.
    
    Uses PyPDF2 to extract text from PDF files, returning one Document
    per page with page number metadata.
    """
    
    def load_pdf(self, file_path: str) -> List[Document]:
        """
        Load text content from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of LangChain Documents, one per page
            
        Raises:
            ValueError: If PDF cannot be read or parsed
        """
        try:
            # Open and read PDF
            reader = PdfReader(file_path)
            
            documents = []
            
            # Extract text from each page
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                
                # Skip empty pages
                if not text or not text.strip():
                    continue
                
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Create metadata
                metadata = {
                    'source': 'pdf',
                    'file_path': file_path,
                    'page': page_num,
                    'total_pages': len(reader.pages),
                    'timestamp': datetime.now().isoformat(),
                    'content_type': 'pdf'
                }
                
                documents.append(Document(page_content=text, metadata=metadata))
            
            if not documents:
                raise ValueError(f"No text content extracted from PDF: {file_path}")
            
            return documents
            
        except Exception as e:
            raise ValueError(f"Failed to load PDF {file_path}: {str(e)}")
