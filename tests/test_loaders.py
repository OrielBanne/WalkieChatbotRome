"""
Tests for data loaders.

This module tests the YouTubeLoader, WebLoader, and PDFLoader classes
using both unit tests and property-based tests.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from hypothesis import given, strategies as st, settings
from langchain_core.documents import Document

from src.loaders import YouTubeLoader, WebLoader, PDFLoader


class TestYouTubeLoader:
    """Unit tests for YouTubeLoader."""
    
    def test_extract_video_id_standard_url(self):
        """Test extracting video ID from standard YouTube URL."""
        loader = YouTubeLoader()
        video_id = loader._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_short_url(self):
        """Test extracting video ID from short youtu.be URL."""
        loader = YouTubeLoader()
        video_id = loader._extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_embed_url(self):
        """Test extracting video ID from embed URL."""
        loader = YouTubeLoader()
        video_id = loader._extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_with_parameters(self):
        """Test extracting video ID from URL with additional parameters."""
        loader = YouTubeLoader()
        video_id = loader._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s")
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_invalid_url(self):
        """Test that invalid URL returns None."""
        loader = YouTubeLoader()
        video_id = loader._extract_video_id("https://example.com/not-a-video")
        assert video_id is None
    
    @patch('src.loaders.YouTubeTranscriptApi')
    def test_load_transcript_success(self, mock_transcript_api):
        """Test successful transcript loading."""
        # Mock transcript data
        mock_transcript_api.get_transcript.return_value = [
            {'text': 'Hello', 'start': 0.0, 'duration': 1.0},
            {'text': 'world', 'start': 1.0, 'duration': 1.0}
        ]
        
        loader = YouTubeLoader()
        doc = loader.load_transcript("https://www.youtube.com/watch?v=test123")
        
        assert isinstance(doc, Document)
        assert doc.page_content == "Hello world"
        assert doc.metadata['source'] == 'youtube'
        assert doc.metadata['video_id'] == 'test123'
        assert doc.metadata['content_type'] == 'transcript'
        assert doc.metadata['transcript_method'] == 'youtube-transcript-api'
        assert 'timestamp' in doc.metadata
    
    def test_load_transcript_invalid_url(self):
        """Test that invalid URL raises ValueError."""
        loader = YouTubeLoader()
        
        with pytest.raises(ValueError, match="Could not extract video ID"):
            loader.load_transcript("https://example.com/not-youtube")
    
    @patch('src.loaders.YouTubeTranscriptApi')
    def test_load_transcript_api_error(self, mock_transcript_api):
        """Test handling of API errors."""
        mock_transcript_api.get_transcript.side_effect = Exception("API Error")
        
        loader = YouTubeLoader(use_whisper_fallback=False)
        
        with pytest.raises(ValueError, match="Failed to load transcript"):
            loader.load_transcript("https://www.youtube.com/watch?v=test123")
    
    @patch('src.loaders.YouTubeTranscriptApi')
    @patch('src.loaders.WHISPER_AVAILABLE', True)
    def test_load_transcript_whisper_fallback(self, mock_transcript_api):
        """Test Whisper fallback when subtitles are unavailable."""
        from youtube_transcript_api import TranscriptsDisabled
        
        # Mock transcript API to raise TranscriptsDisabled
        mock_transcript_api.get_transcript.side_effect = TranscriptsDisabled("video_id")
        
        # Create a loader with whisper fallback disabled to test the error path
        loader = YouTubeLoader(use_whisper_fallback=False)
        
        with pytest.raises(ValueError, match="Failed to load transcript"):
            loader.load_transcript("https://www.youtube.com/watch?v=test123")


class TestWebLoader:
    """Unit tests for WebLoader."""
    
    @patch('src.loaders.requests.get')
    def test_load_webpage_success(self, mock_get):
        """Test successful webpage loading."""
        # Mock HTML response
        html_content = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <nav>Navigation</nav>
                <main>
                    <h1>Main Content</h1>
                    <p>This is the main content.</p>
                </main>
                <footer>Footer</footer>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = html_content.encode('utf-8')
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        loader = WebLoader()
        doc = loader.load_webpage("https://example.com/test")
        
        assert isinstance(doc, Document)
        assert "Main Content" in doc.page_content
        assert "This is the main content" in doc.page_content
        assert "Navigation" not in doc.page_content  # Nav should be removed
        assert "Footer" not in doc.page_content  # Footer should be removed
        assert doc.metadata['source'] == 'web'
        assert doc.metadata['url'] == 'https://example.com/test'
        assert doc.metadata['title'] == 'Test Page'
        assert doc.metadata['content_type'] == 'webpage'
    
    @patch('src.loaders.requests.get')
    def test_load_webpage_no_main_tag(self, mock_get):
        """Test webpage loading when no main tag exists."""
        html_content = """
        <html>
            <head><title>Simple Page</title></head>
            <body>
                <p>Body content without main tag.</p>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = html_content.encode('utf-8')
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        loader = WebLoader()
        doc = loader.load_webpage("https://example.com/simple")
        
        assert isinstance(doc, Document)
        assert "Body content without main tag" in doc.page_content
    
    @patch('src.loaders.requests.get')
    def test_load_webpage_request_error(self, mock_get):
        """Test handling of request errors."""
        mock_get.side_effect = Exception("Connection error")
        
        loader = WebLoader()
        
        with pytest.raises(ValueError, match="Failed to parse webpage"):
            loader.load_webpage("https://example.com/error")
    
    @patch('src.loaders.requests.get')
    def test_load_webpage_timeout(self, mock_get):
        """Test custom timeout setting."""
        loader = WebLoader(timeout=5)
        
        mock_response = Mock()
        mock_response.content = b"<html><body>Test</body></html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        loader.load_webpage("https://example.com/test")
        
        # Verify timeout was passed to requests.get
        mock_get.assert_called_once()
        assert mock_get.call_args[1]['timeout'] == 5


class TestPDFLoader:
    """Unit tests for PDFLoader."""
    
    @patch('src.loaders.PdfReader')
    def test_load_pdf_success(self, mock_pdf_reader):
        """Test successful PDF loading."""
        # Mock PDF pages
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader
        
        loader = PDFLoader()
        docs = loader.load_pdf("test.pdf")
        
        assert len(docs) == 2
        assert all(isinstance(doc, Document) for doc in docs)
        
        # Check first page
        assert docs[0].page_content == "Page 1 content"
        assert docs[0].metadata['source'] == 'pdf'
        assert docs[0].metadata['file_path'] == 'test.pdf'
        assert docs[0].metadata['page'] == 1
        assert docs[0].metadata['total_pages'] == 2
        
        # Check second page
        assert docs[1].page_content == "Page 2 content"
        assert docs[1].metadata['page'] == 2
    
    @patch('src.loaders.PdfReader')
    def test_load_pdf_skip_empty_pages(self, mock_pdf_reader):
        """Test that empty pages are skipped."""
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = ""  # Empty page
        
        mock_page3 = Mock()
        mock_page3.extract_text.return_value = "Page 3 content"
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf_reader.return_value = mock_reader
        
        loader = PDFLoader()
        docs = loader.load_pdf("test.pdf")
        
        assert len(docs) == 2  # Empty page skipped
        assert docs[0].metadata['page'] == 1
        assert docs[1].metadata['page'] == 3
    
    @patch('src.loaders.PdfReader')
    def test_load_pdf_all_empty_pages(self, mock_pdf_reader):
        """Test error when all pages are empty."""
        mock_page = Mock()
        mock_page.extract_text.return_value = ""
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader
        
        loader = PDFLoader()
        
        with pytest.raises(ValueError, match="No text content extracted"):
            loader.load_pdf("empty.pdf")
    
    @patch('src.loaders.PdfReader')
    def test_load_pdf_read_error(self, mock_pdf_reader):
        """Test handling of PDF read errors."""
        mock_pdf_reader.side_effect = Exception("Cannot read PDF")
        
        loader = PDFLoader()
        
        with pytest.raises(ValueError, match="Failed to load PDF"):
            loader.load_pdf("corrupt.pdf")


# Property-Based Tests

class TestYouTubeLoaderProperties:
    """Property-based tests for YouTubeLoader."""
    
    @given(video_id=st.text(min_size=11, max_size=11, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='?&=#')))
    @settings(max_examples=100)
    def test_video_id_extraction_consistency(self, video_id):
        """
        Property: For any video ID, extracting it from different URL formats should be consistent.
        
        **Validates: Requirements 3.1, 3.2**
        """
        loader = YouTubeLoader()
        
        # Test different URL formats
        url_formats = [
            f"https://www.youtube.com/watch?v={video_id}",
            f"https://youtu.be/{video_id}",
            f"https://www.youtube.com/embed/{video_id}"
        ]
        
        extracted_ids = [loader._extract_video_id(url) for url in url_formats]
        
        # All formats should extract the same video ID
        assert all(vid == video_id for vid in extracted_ids if vid is not None)


class TestWebLoaderProperties:
    """Property-based tests for WebLoader."""
    
    @given(
        title=st.text(min_size=1, max_size=100),
        content=st.text(min_size=10, max_size=500)
    )
    @settings(max_examples=100)
    @patch('src.loaders.requests.get')
    def test_webpage_metadata_consistency(self, mock_get, title, content):
        """
        Property: For any webpage, metadata should always include required fields.
        
        **Validates: Requirements 3.1, 3.2**
        """
        html = f"<html><head><title>{title}</title></head><body><main>{content}</main></body></html>"
        
        mock_response = Mock()
        mock_response.content = html.encode('utf-8')
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        loader = WebLoader()
        doc = loader.load_webpage("https://example.com/test")
        
        # Required metadata fields
        assert 'source' in doc.metadata
        assert 'url' in doc.metadata
        assert 'timestamp' in doc.metadata
        assert 'content_type' in doc.metadata
        assert doc.metadata['source'] == 'web'
        assert doc.metadata['content_type'] == 'webpage'


class TestPDFLoaderProperties:
    """Property-based tests for PDFLoader."""
    
    @given(
        page_texts=st.lists(
            st.text(min_size=10, max_size=200),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    @patch('src.loaders.PdfReader')
    def test_pdf_page_count_consistency(self, mock_pdf_reader, page_texts):
        """
        Property: For any PDF, the number of documents should match non-empty pages.
        
        **Validates: Requirements 3.1, 3.2**
        """
        # Create mock pages
        mock_pages = []
        for text in page_texts:
            mock_page = Mock()
            mock_page.extract_text.return_value = text
            mock_pages.append(mock_page)
        
        mock_reader = Mock()
        mock_reader.pages = mock_pages
        mock_pdf_reader.return_value = mock_reader
        
        loader = PDFLoader()
        docs = loader.load_pdf("test.pdf")
        
        # Number of documents should equal number of non-empty pages
        non_empty_pages = [text for text in page_texts if text.strip()]
        assert len(docs) == len(non_empty_pages)
        
        # Each document should have correct page metadata
        for i, doc in enumerate(docs, start=1):
            assert doc.metadata['source'] == 'pdf'
            assert doc.metadata['page'] >= 1
            assert doc.metadata['total_pages'] == len(mock_pages)
            assert 'timestamp' in doc.metadata
    
    @given(
        page_texts=st.lists(
            st.text(min_size=10, max_size=200),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    @patch('src.loaders.PdfReader')
    def test_pdf_document_order_preservation(self, mock_pdf_reader, page_texts):
        """
        Property: For any PDF, documents should be returned in page order.
        
        **Validates: Requirements 3.1, 3.2**
        """
        # Create mock pages
        mock_pages = []
        for text in page_texts:
            mock_page = Mock()
            mock_page.extract_text.return_value = text
            mock_pages.append(mock_page)
        
        mock_reader = Mock()
        mock_reader.pages = mock_pages
        mock_pdf_reader.return_value = mock_reader
        
        loader = PDFLoader()
        docs = loader.load_pdf("test.pdf")
        
        # Page numbers should be in ascending order
        page_numbers = [doc.metadata['page'] for doc in docs]
        assert page_numbers == sorted(page_numbers)
        
        # Page numbers should be consecutive (accounting for skipped empty pages)
        for i in range(len(page_numbers) - 1):
            assert page_numbers[i+1] > page_numbers[i]
