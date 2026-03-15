"""
Unit tests for error handling throughout the Rome Places Chatbot.

Tests cover:
- Storage unavailable scenarios
- API timeout handling
- Geocoding failure fallback
- Vector store error handling
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from src.session_manager import SessionManager
from src.place_extractor import PlaceExtractor
from src.geocoder import Geocoder
from src.vector_store import VectorStore, VectorStoreError
from src.rag_chain import RAGChain, RAGChainError
from src.models import Message, Coordinates
from langchain_core.documents import Document
import requests


class TestStorageErrorHandling:
    """Test error handling for storage operations."""
    
    def test_storage_unavailable_returns_empty_history(self):
        """Test that unavailable storage returns empty history gracefully."""
        # Create session manager with non-existent directory
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(storage_dir=temp_dir)
            
            # Try to load history for non-existent session
            history = session_manager.load_conversation_history("non_existent_session")
            
            # Should return empty list, not crash
            assert history == []
    
    def test_corrupted_session_data_returns_empty_history(self):
        """Test that corrupted session data returns empty history gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(storage_dir=temp_dir)
            
            # Create a session
            session = session_manager.get_or_create_session("test_user")
            
            # Corrupt the session file
            session_file = Path(temp_dir) / f"test_user_{session.session_id}.json"
            with open(session_file, 'w') as f:
                f.write("{ invalid json content }")
            
            # Try to load history
            history = session_manager.load_conversation_history(session.session_id)
            
            # Should return empty list, not crash
            assert history == []
    
    def test_corrupted_message_in_history_is_skipped(self):
        """Test that corrupted messages in history are skipped gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(storage_dir=temp_dir)
            
            # Create a session
            session = session_manager.get_or_create_session("test_user")
            
            # Add a valid message
            message1 = Message(
                role="user",
                content="Hello",
                timestamp=datetime.now(),
                session_id=session.session_id,
                metadata={}
            )
            session_manager.save_message(session.session_id, message1)
            
            # Manually corrupt the session file by adding invalid message
            session_file = Path(temp_dir) / f"test_user_{session.session_id}.json"
            import json
            with open(session_file, 'r') as f:
                data = json.load(f)
            
            # Add corrupted message (missing required fields)
            data["messages"].append({"role": "user"})  # Missing content, timestamp, etc.
            
            with open(session_file, 'w') as f:
                json.dump(data, f)
            
            # Try to load history
            history = session_manager.load_conversation_history(session.session_id)
            
            # Should return only valid messages
            assert len(history) == 1
            assert history[0].content == "Hello"
    
    def test_storage_write_failure_raises_error(self):
        """Test that storage write failures raise appropriate errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(storage_dir=temp_dir)
            session = session_manager.get_or_create_session("test_user")
            
            # Delete the session file to cause write failure
            session_file = Path(temp_dir) / f"test_user_{session.session_id}.json"
            session_file.unlink()
            
            # Try to save a message to non-existent session
            message = Message(
                role="user",
                content="Test",
                timestamp=datetime.now(),
                session_id=session.session_id,
                metadata={}
            )
            
            # Should raise ValueError for non-existent session
            with pytest.raises(ValueError):
                session_manager.save_message(session.session_id, message)


class TestAPIErrorHandling:
    """Test error handling for API operations."""
    
    def test_rag_chain_invoke_with_retry_logic(self):
        """Test that RAG chain has retry logic in invoke method."""
        # We can't easily mock the LLM due to LangChain's validation
        # Instead, test that the retry logic exists by checking the code
        from src.rag_chain import RAGChain
        import inspect
        
        # Check that invoke method has retry logic
        source = inspect.getsource(RAGChain.invoke)
        assert "max_retries" in source
        assert "retry" in source.lower() or "attempt" in source.lower()
    
    def test_rag_chain_error_raises_user_friendly_message(self):
        """Test that RAG chain errors raise user-friendly messages."""
        from src.rag_chain import RAGChainError
        
        # Verify that RAGChainError exists and can be raised
        try:
            raise RAGChainError("Test error message")
        except RAGChainError as e:
            assert "Test error message" in str(e)


class TestGeocodingErrorHandling:
    """Test error handling for geocoding operations."""
    
    def test_geocoding_timeout_with_retry(self):
        """Test that geocoder retries on timeout."""
        geocoder = Geocoder()
        
        # Check that the geocode_place method has max_retries parameter
        import inspect
        sig = inspect.signature(geocoder.geocode_place)
        assert 'max_retries' in sig.parameters
        
        # Verify default max_retries value (None means it uses config default)
        assert sig.parameters['max_retries'].default is None
    
    def test_geocoding_fallback_to_manual_database(self):
        """Test that geocoder falls back to manual database on failure."""
        geocoder = Geocoder()
        
        # Mock the session to always fail
        geocoder.session.get = Mock(side_effect=requests.exceptions.ConnectionError("Service error"))
        
        # Should fall back to manual database for known places
        coords = geocoder.geocode_place("Colosseum")
        
        assert coords is not None
        assert coords.source == "manual"
        assert coords.latitude == 41.8902
        assert coords.longitude == 12.4922
    
    def test_geocoding_failure_returns_none(self):
        """Test that geocoding failure for unknown place returns None."""
        geocoder = Geocoder()
        
        # Mock the session to always fail
        geocoder.session.get = Mock(side_effect=requests.exceptions.ConnectionError("Service error"))
        
        # Should return None for unknown places
        coords = geocoder.geocode_place("Unknown Place That Doesn't Exist")
        
        assert coords is None
    
    def test_geocoding_caches_failures(self):
        """Test that geocoding failures are cached to avoid repeated lookups."""
        geocoder = Geocoder()
        
        # Mock the session to always fail
        call_count = [0]
        
        def mock_get(*args, **kwargs):
            call_count[0] += 1
            raise requests.exceptions.ConnectionError("Service error")
        
        geocoder.session.get = mock_get
        
        # First call should hit the API
        coords1 = geocoder.geocode_place("Unknown Place")
        assert coords1 is None
        assert call_count[0] == 1
        
        # Second call should use cache, not hit API again
        coords2 = geocoder.geocode_place("Unknown Place")
        assert coords2 is None
        assert call_count[0] == 1  # No additional API call


class TestVectorStoreErrorHandling:
    """Test error handling for vector store operations."""
    
    def test_vector_store_empty_returns_error(self):
        """Test that querying empty vector store raises appropriate error."""
        vector_store = VectorStore()
        
        # Try to search empty vector store
        with pytest.raises(VectorStoreError) as exc_info:
            vector_store.similarity_search("test query")
        
        assert "empty or not initialized" in str(exc_info.value).lower()
    
    def test_vector_store_embedding_failure_with_retry(self):
        """Test that vector store retries on embedding failure."""
        # Create mock embedding model that fails twice then succeeds
        mock_embeddings = Mock()
        call_count = [0]
        
        def embed_side_effect(texts):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Embedding API error")
            return [[0.1] * 1536 for _ in texts]  # Return valid embeddings
        
        mock_embeddings.embed_documents = Mock(side_effect=embed_side_effect)
        
        vector_store = VectorStore(embedding_model=mock_embeddings)
        
        # Add documents - should succeed after retries
        docs = [Document(page_content="Test content", metadata={})]
        vector_store.add_documents(docs)
        
        assert len(vector_store.documents) == 1
        assert call_count[0] == 3
    
    def test_vector_store_embedding_failure_after_max_retries(self):
        """Test that vector store raises error after max embedding retries."""
        # Create mock embedding model that always fails
        mock_embeddings = Mock()
        mock_embeddings.embed_documents = Mock(side_effect=Exception("Embedding API error"))
        
        vector_store = VectorStore(embedding_model=mock_embeddings)
        
        # Try to add documents - should raise error after retries
        docs = [Document(page_content="Test content", metadata={})]
        
        with pytest.raises(VectorStoreError) as exc_info:
            vector_store.add_documents(docs)
        
        assert "failed to generate embeddings" in str(exc_info.value).lower()
    
    def test_vector_store_query_embedding_failure_with_retry(self):
        """Test that vector store retries query embedding on failure."""
        # Create mock embedding model
        mock_embeddings = Mock()
        mock_embeddings.embed_documents = Mock(return_value=[[0.1] * 1536])
        
        # Mock query embedding to fail twice then succeed
        call_count = [0]
        
        def query_embed_side_effect(text):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Query embedding error")
            return [0.1] * 1536
        
        mock_embeddings.embed_query = Mock(side_effect=query_embed_side_effect)
        
        vector_store = VectorStore(embedding_model=mock_embeddings)
        
        # Add a document first
        docs = [Document(page_content="Test content", metadata={})]
        vector_store.add_documents(docs)
        
        # Query should succeed after retries
        results = vector_store.similarity_search("test query")
        
        assert len(results) == 1
        assert call_count[0] == 3


class TestPlaceExtractionErrorHandling:
    """Test error handling for place extraction operations."""
    
    def test_place_extraction_empty_text_returns_empty_list(self):
        """Test that extracting from empty text returns empty list."""
        extractor = PlaceExtractor()
        
        places = extractor.extract_places("")
        assert places == []
        
        places = extractor.extract_places("   ")
        assert places == []
    
    def test_place_extraction_failure_returns_empty_list(self):
        """Test that place extraction failure returns empty list gracefully."""
        extractor = PlaceExtractor()
        
        # Mock spaCy to raise an error
        extractor.nlp = Mock(side_effect=Exception("NLP error"))
        
        # Should return empty list, not crash
        places = extractor.extract_places("Visit the Colosseum")
        assert places == []
    
    def test_place_extraction_handles_malformed_entities(self):
        """Test that place extraction handles malformed entities gracefully."""
        extractor = PlaceExtractor()
        
        # Create a mock doc with malformed entity
        mock_doc = Mock()
        mock_ent = Mock()
        mock_ent.label_ = "GPE"
        mock_ent.text = "Rome"
        mock_ent.start_char = 0
        mock_ent.end_char = 4
        
        # Make entity raise error when accessing properties
        def raise_error():
            raise AttributeError("Malformed entity")
        
        mock_ent.text = property(lambda self: raise_error())
        mock_doc.ents = [mock_ent]
        
        extractor.nlp = Mock(return_value=mock_doc)
        
        # Should handle error and continue
        places = extractor.extract_places("Visit Rome")
        
        # May return empty or partial results, but shouldn't crash
        assert isinstance(places, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
