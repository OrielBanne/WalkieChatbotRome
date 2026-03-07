"""
Unit tests for the data ingestion script.

Tests ingestion of YouTube videos, web pages, and PDFs, as well as
FAISS index persistence.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from langchain_core.documents import Document

# Import functions from the ingestion script
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ingest_data import (
    load_sources_from_file,
    ingest_youtube_videos,
    ingest_webpages,
    ingest_pdfs
)
from src.chunker import TextChunker
from src.vector_store import VectorStore


class TestLoadSourcesFromFile:
    """Tests for loading sources from a file."""
    
    def test_load_sources_from_file(self, tmp_path):
        """Test loading sources from a properly formatted file."""
        sources_file = tmp_path / "sources.txt"
        sources_file.write_text(
            "youtube: https://www.youtube.com/watch?v=test1\n"
            "web: https://example.com/page1\n"
            "pdf: /path/to/file.pdf\n"
            "# This is a comment\n"
            "youtube: https://www.youtube.com/watch?v=test2\n"
        )
        
        sources = load_sources_from_file(str(sources_file))
        
        assert len(sources['youtube']) == 2
        assert len(sources['web']) == 1
        assert len(sources['pdf']) == 1
        assert 'https://www.youtube.com/watch?v=test1' in sources['youtube']
        assert 'https://example.com/page1' in sources['web']
        assert '/path/to/file.pdf' in sources['pdf']
    
    def test_load_sources_empty_file(self, tmp_path):
        """Test loading from an empty file."""
        sources_file = tmp_path / "empty.txt"
        sources_file.write_text("")
        
        sources = load_sources_from_file(str(sources_file))
        
        assert sources['youtube'] == []
        assert sources['web'] == []
        assert sources['pdf'] == []
    
    def test_load_sources_comments_only(self, tmp_path):
        """Test loading from a file with only comments."""
        sources_file = tmp_path / "comments.txt"
        sources_file.write_text(
            "# Comment 1\n"
            "# Comment 2\n"
        )
        
        sources = load_sources_from_file(str(sources_file))
        
        assert sources['youtube'] == []
        assert sources['web'] == []
        assert sources['pdf'] == []


class TestIngestYouTubeVideos:
    """Tests for YouTube video ingestion."""
    
    @patch('scripts.ingest_data.YouTubeLoader')
    def test_ingest_youtube_video_success(self, mock_loader_class):
        """Test successful ingestion of a YouTube video."""
        # Mock the loader
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        
        # Mock transcript document
        mock_doc = Document(
            page_content="This is a test transcript. " * 100,  # Long enough to chunk
            metadata={
                'source': 'youtube',
                'url': 'https://www.youtube.com/watch?v=test',
                'video_id': 'test'
            }
        )
        mock_loader.load_transcript.return_value = mock_doc
        
        # Create chunker
        chunker = TextChunker(chunk_size=100, overlap=20)
        
        # Ingest
        urls = ['https://www.youtube.com/watch?v=test']
        chunks = ingest_youtube_videos(urls, chunker)
        
        # Verify
        assert len(chunks) > 0
        assert all(isinstance(doc, Document) for doc in chunks)
        assert all('chunk_id' in doc.metadata for doc in chunks)
        assert all('total_chunks' in doc.metadata for doc in chunks)
        mock_loader.load_transcript.assert_called_once_with(urls[0])
    
    @patch('scripts.ingest_data.YouTubeLoader')
    def test_ingest_youtube_video_failure(self, mock_loader_class):
        """Test handling of YouTube video ingestion failure."""
        # Mock the loader to raise an exception
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_transcript.side_effect = ValueError("Video not found")
        
        chunker = TextChunker()
        urls = ['https://www.youtube.com/watch?v=invalid']
        
        # Should not raise, but return empty list
        chunks = ingest_youtube_videos(urls, chunker)
        
        assert chunks == []
    
    @patch('scripts.ingest_data.YouTubeLoader')
    def test_ingest_multiple_youtube_videos(self, mock_loader_class):
        """Test ingestion of multiple YouTube videos."""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        
        # Mock two different transcripts
        def mock_load_transcript(url):
            if 'test1' in url:
                return Document(
                    page_content="Transcript 1. " * 50,
                    metadata={'source': 'youtube', 'url': url, 'video_id': 'test1'}
                )
            else:
                return Document(
                    page_content="Transcript 2. " * 50,
                    metadata={'source': 'youtube', 'url': url, 'video_id': 'test2'}
                )
        
        mock_loader.load_transcript.side_effect = mock_load_transcript
        
        chunker = TextChunker(chunk_size=100, overlap=20)
        urls = [
            'https://www.youtube.com/watch?v=test1',
            'https://www.youtube.com/watch?v=test2'
        ]
        
        chunks = ingest_youtube_videos(urls, chunker)
        
        assert len(chunks) > 0
        assert mock_loader.load_transcript.call_count == 2


class TestIngestWebpages:
    """Tests for webpage ingestion."""
    
    @patch('scripts.ingest_data.WebLoader')
    def test_ingest_webpage_success(self, mock_loader_class):
        """Test successful ingestion of a webpage."""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        
        mock_doc = Document(
            page_content="This is webpage content. " * 100,
            metadata={
                'source': 'web',
                'url': 'https://example.com/page',
                'title': 'Test Page'
            }
        )
        mock_loader.load_webpage.return_value = mock_doc
        
        chunker = TextChunker(chunk_size=100, overlap=20)
        urls = ['https://example.com/page']
        
        chunks = ingest_webpages(urls, chunker)
        
        assert len(chunks) > 0
        assert all(isinstance(doc, Document) for doc in chunks)
        assert all('chunk_id' in doc.metadata for doc in chunks)
        mock_loader.load_webpage.assert_called_once_with(urls[0])
    
    @patch('scripts.ingest_data.WebLoader')
    def test_ingest_webpage_failure(self, mock_loader_class):
        """Test handling of webpage ingestion failure."""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_webpage.side_effect = ValueError("Page not found")
        
        chunker = TextChunker()
        urls = ['https://example.com/invalid']
        
        chunks = ingest_webpages(urls, chunker)
        
        assert chunks == []


class TestIngestPDFs:
    """Tests for PDF ingestion."""
    
    @patch('scripts.ingest_data.PDFLoader')
    def test_ingest_pdf_success(self, mock_loader_class):
        """Test successful ingestion of a PDF file."""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        
        # Mock PDF with multiple pages
        mock_docs = [
            Document(
                page_content="Page 1 content. " * 50,
                metadata={'source': 'pdf', 'file_path': '/path/to/test.pdf', 'page': 1}
            ),
            Document(
                page_content="Page 2 content. " * 50,
                metadata={'source': 'pdf', 'file_path': '/path/to/test.pdf', 'page': 2}
            )
        ]
        mock_loader.load_pdf.return_value = mock_docs
        
        chunker = TextChunker(chunk_size=100, overlap=20)
        paths = ['/path/to/test.pdf']
        
        chunks = ingest_pdfs(paths, chunker)
        
        assert len(chunks) > 0
        assert all(isinstance(doc, Document) for doc in chunks)
        assert all('chunk_id' in doc.metadata for doc in chunks)
        mock_loader.load_pdf.assert_called_once_with(paths[0])
    
    @patch('scripts.ingest_data.PDFLoader')
    def test_ingest_pdf_failure(self, mock_loader_class):
        """Test handling of PDF ingestion failure."""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load_pdf.side_effect = ValueError("PDF not found")
        
        chunker = TextChunker()
        paths = ['/path/to/invalid.pdf']
        
        chunks = ingest_pdfs(paths, chunker)
        
        assert chunks == []


class TestFAISSIndexPersistence:
    """Tests for FAISS index persistence."""
    
    @patch('src.vector_store.OpenAIEmbeddings')
    def test_vector_store_save_and_load(self, mock_embeddings_class, tmp_path):
        """Test saving and loading FAISS index."""
        # Mock the embeddings model
        mock_embeddings = Mock()
        mock_embeddings_class.return_value = mock_embeddings
        
        # Mock embedding responses (1536 dimensions)
        import numpy as np
        mock_embeddings.embed_documents.return_value = [
            np.random.rand(1536).tolist(),
            np.random.rand(1536).tolist()
        ]
        mock_embeddings.embed_query.return_value = np.random.rand(1536).tolist()
        
        # Create a vector store with some documents
        vector_store = VectorStore()
        
        # Add sample documents
        docs = [
            Document(
                page_content="The Colosseum is an ancient amphitheater in Rome.",
                metadata={'source': 'test', 'id': 'doc1'}
            ),
            Document(
                page_content="The Trevi Fountain is a famous baroque fountain.",
                metadata={'source': 'test', 'id': 'doc2'}
            )
        ]
        
        vector_store.add_documents(docs)
        
        # Save to disk
        output_dir = tmp_path / "vector_store"
        vector_store.save(str(output_dir))
        
        # Verify files were created
        assert (output_dir / "faiss.index").exists()
        assert (output_dir / "documents.pkl").exists()
        
        # Load into a new vector store
        new_vector_store = VectorStore()
        new_vector_store.load(str(output_dir))
        
        # Verify documents were loaded
        assert len(new_vector_store) == 2
        assert len(new_vector_store.documents) == 2
        
        # Verify document content was preserved
        doc_contents = [doc.page_content for doc in new_vector_store.documents]
        assert "The Colosseum is an ancient amphitheater in Rome." in doc_contents
        assert "The Trevi Fountain is a famous baroque fountain." in doc_contents
    
    @patch('src.vector_store.OpenAIEmbeddings')
    def test_vector_store_append_mode(self, mock_embeddings_class, tmp_path):
        """Test appending to an existing vector store."""
        # Mock the embeddings model
        mock_embeddings = Mock()
        mock_embeddings_class.return_value = mock_embeddings
        
        # Mock embedding responses
        import numpy as np
        mock_embeddings.embed_documents.return_value = [np.random.rand(1536).tolist()]
        
        output_dir = tmp_path / "vector_store"
        
        # Create initial vector store
        vector_store1 = VectorStore()
        docs1 = [
            Document(
                page_content="Document 1",
                metadata={'source': 'test', 'id': 'doc1'}
            )
        ]
        vector_store1.add_documents(docs1)
        vector_store1.save(str(output_dir))
        
        # Load and append more documents
        vector_store2 = VectorStore()
        vector_store2.load(str(output_dir))
        
        docs2 = [
            Document(
                page_content="Document 2",
                metadata={'source': 'test', 'id': 'doc2'}
            )
        ]
        vector_store2.add_documents(docs2)
        vector_store2.save(str(output_dir))
        
        # Load again and verify both documents exist
        vector_store3 = VectorStore()
        vector_store3.load(str(output_dir))
        
        assert len(vector_store3) == 2
    
    def test_vector_store_empty_save(self, tmp_path):
        """Test saving an empty vector store."""
        vector_store = VectorStore()
        output_dir = tmp_path / "empty_store"
        
        # Should not raise an error
        vector_store.save(str(output_dir))
        
        # Verify directory was created
        assert output_dir.exists()
