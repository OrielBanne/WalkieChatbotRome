"""
Integration tests for the Streamlit application.

These tests verify the full query → response → map flow and session management
functionality of the Rome Places Chatbot Streamlit app.
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from langchain_core.documents import Document

from src.session_manager import SessionManager
from src.context_manager import ContextManager
from src.place_extractor import PlaceExtractor
from src.rag_chain import RAGChain
from src.geocoder import Geocoder
from src.map_builder import MapBuilder
from src.vector_store import VectorStore
from src.models import Message, PlaceMarker, Coordinates


@pytest.fixture
def temp_session_dir():
    """Create a temporary directory for session storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def session_manager(temp_session_dir):
    """Create a SessionManager with temporary storage."""
    return SessionManager(storage_dir=temp_session_dir)


@pytest.fixture
def context_manager(session_manager):
    """Create a ContextManager."""
    return ContextManager(session_manager)


@pytest.fixture
def place_extractor():
    """Create a PlaceExtractor."""
    return PlaceExtractor()


@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore."""
    vector_store = Mock(spec=VectorStore)
    
    # Mock similarity search to return sample documents
    sample_doc = Document(
        page_content="The Colosseum is an ancient amphitheater in Rome.",
        metadata={"source": "test", "place": "Colosseum"}
    )
    vector_store.similarity_search.return_value = [sample_doc]
    
    return vector_store


@pytest.fixture
def mock_llm():
    """Create a mock LLM - note: only works for direct calls, not LangChain chains."""
    llm = Mock()
    
    # Mock streaming response
    def mock_stream(prompt):
        response = "The Colosseum is a magnificent ancient amphitheater in Rome."
        for word in response.split():
            yield word + " "
    
    llm.stream = mock_stream
    
    # Mock invoke response
    llm.invoke.return_value = Mock(
        content="The Colosseum is a magnificent ancient amphitheater in Rome."
    )
    
    return llm


@pytest.fixture
def mock_retriever(mock_vector_store):
    """Create a mock retriever."""
    retriever = Mock()
    retriever.get_relevant_documents.return_value = mock_vector_store.similarity_search.return_value
    return retriever


@pytest.fixture
def geocoder():
    """Create a Geocoder."""
    return Geocoder()


@pytest.fixture
def map_builder():
    """Create a MapBuilder."""
    return MapBuilder()


class TestFullQueryResponseMapFlow:
    """Test the complete flow from query to response to map visualization."""
    
    @pytest.mark.skip(reason="Requires real OpenAI API key for RAG chain")
    def test_query_generates_response_and_extracts_places(
        self,
        session_manager,
        context_manager,
        place_extractor,
        geocoder,
        map_builder
    ):
        """
        Test full flow: user query → RAG response → place extraction → map generation.
        
        Requirements: All requirements
        
        Note: This test requires a real OpenAI API key and is skipped in CI.
        """
        # This test would require a real RAG chain with OpenAI API
        # Skipping to avoid API dependencies in tests
        pass
    
    def test_multiple_places_creates_route(
        self,
        place_extractor,
        geocoder,
        map_builder
    ):
        """
        Test that multiple places in response create a map with route.
        
        Requirements: Map visualization support
        """
        # Response with multiple places
        response = "Visit the Colosseum, then walk to the Roman Forum, and end at the Pantheon."
        
        # Extract places
        places = place_extractor.extract_places(response)
        rome_places = place_extractor.filter_rome_places(places)
        
        # Geocode places
        place_markers = []
        for place_mention in rome_places:
            coords = geocoder.geocode_place(place_mention.name)
            
            if coords:
                marker = PlaceMarker(
                    name=place_mention.name,
                    coordinates=(coords.latitude, coords.longitude),
                    place_type="landmark",
                    description=None,
                    icon="star"
                )
                place_markers.append(marker)
        
        # Should have multiple places
        assert len(place_markers) >= 2
        
        # Create map with route
        map_obj = map_builder.create_map_with_places(
            places=place_markers,
            add_route=True
        )
        
        # Verify map was created
        assert map_obj is not None
    
    def test_no_places_in_response_handles_gracefully(
        self,
        place_extractor,
        map_builder
    ):
        """
        Test that responses with no places are handled gracefully.
        
        Requirements: Map visualization support
        """
        # Response with no specific places (just general text)
        response = "Hello! I'm here to help you with your travel questions."
        
        # Extract places
        places = place_extractor.extract_places(response)
        
        # Filter to only specific Rome landmarks (not just "Rome" itself)
        specific_places = [p for p in places if p.name.lower() not in ["rome", "roma"]]
        
        # Should have no specific places
        assert len(specific_places) == 0
        
        # Create map with empty places list
        map_obj = map_builder.create_map_with_places(
            places=[],
            add_route=False
        )
        
        # Should still create a base map
        assert map_obj is not None


class TestSessionPersistenceAcrossReruns:
    """Test that session state persists correctly across app reruns."""
    
    def test_session_persists_after_save_and_load(
        self,
        session_manager,
        context_manager
    ):
        """
        Test that session data persists across app reruns.
        
        Requirements: 1.1, 1.2, 1.3, 1.4
        """
        # Create session and add messages
        user_id = "test_user"
        session = session_manager.get_or_create_session(user_id)
        
        # Add messages
        context_manager.add_to_history(session.session_id, "user", "Hello")
        context_manager.add_to_history(session.session_id, "assistant", "Hi there!")
        context_manager.add_to_history(session.session_id, "user", "Tell me about Rome")
        context_manager.add_to_history(session.session_id, "assistant", "Rome is beautiful!")
        
        # Simulate app rerun by creating new context manager
        new_context_manager = ContextManager(session_manager)
        
        # Load history
        history = session_manager.load_conversation_history(session.session_id)
        
        # Verify all messages persisted
        assert len(history) == 4
        assert history[0].content == "Hello"
        assert history[1].content == "Hi there!"
        assert history[2].content == "Tell me about Rome"
        assert history[3].content == "Rome is beautiful!"
    
    def test_multiple_sessions_persist_independently(
        self,
        session_manager,
        context_manager
    ):
        """
        Test that multiple sessions persist independently.
        
        Requirements: 1.4, 2.3
        """
        user_id = "test_user"
        
        # Create first session
        session1 = session_manager.get_or_create_session(user_id)
        context_manager.add_to_history(session1.session_id, "user", "Session 1 message")
        
        # Create second session
        session2 = session_manager.get_or_create_session(user_id)
        context_manager.add_to_history(session2.session_id, "user", "Session 2 message")
        
        # Load histories
        history1 = session_manager.load_conversation_history(session1.session_id)
        history2 = session_manager.load_conversation_history(session2.session_id)
        
        # Verify sessions are independent
        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0].content == "Session 1 message"
        assert history2[0].content == "Session 2 message"
        assert session1.session_id != session2.session_id


class TestClearHistoryFunctionality:
    """Test the clear history functionality."""
    
    def test_clear_history_removes_all_messages(
        self,
        session_manager,
        context_manager
    ):
        """
        Test that clearing history removes all messages.
        
        Requirements: 5.1
        """
        # Create session and add messages
        user_id = "test_user"
        session = session_manager.get_or_create_session(user_id)
        
        context_manager.add_to_history(session.session_id, "user", "Message 1")
        context_manager.add_to_history(session.session_id, "assistant", "Response 1")
        context_manager.add_to_history(session.session_id, "user", "Message 2")
        
        # Verify messages exist
        history = session_manager.load_conversation_history(session.session_id)
        assert len(history) == 3
        
        # Clear history
        session_manager.clear_history(session.session_id)
        
        # Verify history is empty
        history = session_manager.load_conversation_history(session.session_id)
        assert len(history) == 0
    
    def test_clear_history_preserves_session(
        self,
        session_manager,
        context_manager
    ):
        """
        Test that clearing history preserves the session itself.
        
        Requirements: 5.1
        """
        # Create session and add messages
        user_id = "test_user"
        session = session_manager.get_or_create_session(user_id)
        original_session_id = session.session_id
        
        context_manager.add_to_history(session.session_id, "user", "Message")
        
        # Clear history
        session_manager.clear_history(session.session_id)
        
        # Verify session still exists
        sessions = session_manager.list_sessions(user_id)
        assert len(sessions) == 1
        assert sessions[0].session_id == original_session_id


class TestExportHistoryFunctionality:
    """Test the export history functionality."""
    
    def test_export_history_creates_readable_format(
        self,
        session_manager,
        context_manager
    ):
        """
        Test that export creates a readable text format.
        
        Requirements: 5.4
        """
        # Create session and add messages
        user_id = "test_user"
        session = session_manager.get_or_create_session(user_id)
        
        context_manager.add_to_history(session.session_id, "user", "Hello")
        context_manager.add_to_history(session.session_id, "assistant", "Hi there!")
        
        # Export history
        exported = session_manager.export_history(session.session_id)
        
        # Verify format
        assert "Conversation History" in exported
        assert session.session_id in exported
        assert "User:" in exported
        assert "Assistant:" in exported
        assert "Hello" in exported
        assert "Hi there!" in exported
    
    def test_export_empty_history(
        self,
        session_manager
    ):
        """
        Test exporting an empty conversation history.
        
        Requirements: 5.4
        """
        # Create session without messages
        user_id = "test_user"
        session = session_manager.get_or_create_session(user_id)
        
        # Export history
        exported = session_manager.export_history(session.session_id)
        
        # Verify message
        assert "No conversation history found" in exported
    
    def test_export_preserves_message_order(
        self,
        session_manager,
        context_manager
    ):
        """
        Test that export preserves chronological message order.
        
        Requirements: 5.4, 1.5
        """
        # Create session and add messages
        user_id = "test_user"
        session = session_manager.get_or_create_session(user_id)
        
        messages = [
            ("user", "First message"),
            ("assistant", "First response"),
            ("user", "Second message"),
            ("assistant", "Second response"),
        ]
        
        for role, content in messages:
            context_manager.add_to_history(session.session_id, role, content)
        
        # Export history
        exported = session_manager.export_history(session.session_id)
        
        # Verify order by checking positions
        first_pos = exported.find("First message")
        first_resp_pos = exported.find("First response")
        second_pos = exported.find("Second message")
        second_resp_pos = exported.find("Second response")
        
        assert first_pos < first_resp_pos < second_pos < second_resp_pos


class TestErrorHandling:
    """Test error handling in the application."""
    
    @pytest.mark.skip(reason="Requires real LLM for RAG chain initialization")
    def test_rag_chain_error_displays_user_friendly_message(self):
        """
        Test that RAG chain errors show user-friendly messages.
        
        Requirements: 1.6, 4.1
        
        Note: This test requires a real LLM and is skipped in CI.
        """
        pass
    
    def test_geocoding_failure_handled_gracefully(
        self,
        geocoder
    ):
        """
        Test that geocoding failures are handled gracefully.
        
        Requirements: Map visualization support
        """
        # Try to geocode a non-existent place
        coords = geocoder.geocode_place("NonExistentPlace12345XYZ")
        
        # Should return None, not raise an error
        assert coords is None
    
    @pytest.mark.skip(reason="Requires real LLM for RAG chain initialization")
    def test_empty_vector_store_handled_gracefully(self):
        """
        Test that empty vector store is handled gracefully.
        
        Requirements: 3.1
        
        Note: This test requires a real LLM and is skipped in CI.
        """
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
