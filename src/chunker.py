"""
Text chunker for splitting documents into semantic chunks.

This module provides functionality to split text into chunks at sentence
boundaries while respecting size limits and overlap requirements.
"""

import re
from typing import List


class TextChunker:
    """
    Chunks text into overlapping segments at sentence boundaries.
    
    Uses semantic chunking to avoid breaking sentences, ensuring each chunk
    contains complete thoughts for better embedding quality.
    """
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize the text chunker.
        
        Args:
            chunk_size: Target size for each chunk in characters (default: 1000)
            overlap: Number of characters to overlap between chunks (default: 200)
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap cannot be negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")
        
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    @staticmethod
    def _split_into_sentences(text: str) -> List[str]:
        """
        Split text into sentences using regex patterns.
        
        Handles common sentence boundaries while avoiding false positives
        like abbreviations and decimal numbers.
        
        Args:
            text: Text to split into sentences
            
        Returns:
            List of sentences
        """
        # Pattern matches sentence-ending punctuation followed by whitespace and capital letter
        # or end of string
        pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$'
        
        sentences = re.split(pattern, text)
        
        # Clean up and filter empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """
        Chunk text into overlapping segments at sentence boundaries.
        
        Splits text into sentences and groups them into chunks that respect
        the size limit while maintaining semantic coherence. Chunks overlap
        to preserve context across boundaries.
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters (uses instance default if None)
            overlap: Overlap size in characters (uses instance default if None)
            
        Returns:
            List of text chunks
        """
        # Use instance defaults if not specified
        chunk_size = chunk_size if chunk_size is not None else self.chunk_size
        overlap = overlap if overlap is not None else self.overlap
        
        # Handle empty text
        if not text or not text.strip():
            return []
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            # If single sentence exceeds chunk_size, add it as its own chunk
            if sentence_len > chunk_size:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Add the long sentence as its own chunk
                chunks.append(sentence)
                continue
            
            # Check if adding this sentence would exceed chunk_size
            # Account for space between sentences
            space_needed = 1 if current_chunk else 0
            if current_size + space_needed + sentence_len > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                # Find sentences from current chunk that fit in overlap
                overlap_chunk = []
                overlap_size = 0
                
                for prev_sentence in reversed(current_chunk):
                    prev_len = len(prev_sentence)
                    space = 1 if overlap_chunk else 0
                    
                    if overlap_size + space + prev_len <= overlap:
                        overlap_chunk.insert(0, prev_sentence)
                        overlap_size += space + prev_len
                    else:
                        break
                
                current_chunk = overlap_chunk
                current_size = overlap_size
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += (1 if len(current_chunk) > 1 else 0) + sentence_len
        
        # Add final chunk if it exists
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Convenience function to chunk text with default parameters.
    
    Args:
        text: Text to chunk
        chunk_size: Target chunk size in characters (default: 1000)
        overlap: Overlap size in characters (default: 200)
        
    Returns:
        List of text chunks
    """
    chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk_text(text)
