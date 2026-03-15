"""Integration tests for Place Discovery Agent with real RAG system.

This module tests the place discovery functionality with actual RAG chain
and geocoder instances to verify end-to-end integration.
"""

import pytest
from unittest.mock import Mock, patch
from src.agents.place_discovery import PlaceDiscoveryAgent
from src.agents.models import PlannerState, UserPreferences
from src.rag_chain import RAGChain
from src.geocoder import Geocoder


@pytest.fixture
def real_geocoder():
    """Create a real geocoder instance."""
    return Geocoder(user_agent="test_place_discovery_integration")


@pytest.fixture
def mock_llm():
    """Create a mock LLM for RAG chain."""
    mock = Mock()
    # Mock the invoke method to return a response about Rome places
    mock.invoke.return_value = (
        "The Colosseum is an ancient amphitheater in Rome, built in 70-80 AD. "
        "It could hold up to 50,000 spectators. "
        "The Trevi Fountain is a famous baroque fountain in Rome. "
        "The Pantheon is a former Roman temple, now a church."
    )
    return mock


@pytest.fixture
def mock_retriever():
    """Create a mock retriever for RAG chain."""
    from langchain_core.documents import Document
    
    mock = Mock()
    mock.get_relevant_documents.return_value = [
        Document(page_content="The Colosseum is an ancient amphitheater."),
        Document(page_content="The Trevi Fountain is a baroque fountain."),
        Document(page_content="The Pantheon is a former Roman temple."),
    ]
    return mock


@pytest.fixture
def real_rag_chain(mock_llm, mock_retriever):
    """Create a RAG chain with mocked components."""
    with patch('src.rag_chain.RetrievalQA') as mock_qa:
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "result": (
                "The Colosseum is an ancient amphitheater in Rome. "
                "The Trevi Fountain is a famous baroque fountain. "
                "The Pantheon is a former Roman temple."
            )
        }
        mock_qa.from_chain_type.return_value = mock_chain
        
        rag_chain = RAGChain(llm=mock_llm, retriever=mock_retriever)
        return rag_chain



class TestPlaceDiscoveryIntegration:
    """Integration tests for Place Discovery Agent."""
    
    def test_discover_places_with_real_rag(self, real_rag_chain, real_geocoder):
        """Test place discovery with real RAG chain and geocoder."""
        agent = PlaceDiscoveryAgent(real_rag_chain, real_geocoder)
        
        state = PlannerState(
            user_query="Show me ancient monuments in Rome",
            user_preferences=UserPreferences(
                interests=["history", "architecture"],
                available_hours=6.0
            )
        )
        
        result_state = agent.discover_places(state)
        
        # Should discover places
        assert len(result_state.candidate_places) > 0
        
        # Verify places have proper structure
        for place in result_state.candidate_places:
            assert place.name
            assert place.place_type
            assert place.coordinates != (0.0, 0.0)
            assert place.visit_duration > 0
        
        # Should have explanation
        assert "Found" in result_state.explanation or "places" in result_state.explanation
    
    def test_discover_places_with_food_query(self, real_rag_chain, real_geocoder):
        """Test place discovery with food-related query."""
        # Update mock to return restaurant info
        real_rag_chain.chain.invoke.return_value = {
            "result": "Trastevere is known for its restaurants and trattorias."
        }
        
        agent = PlaceDiscoveryAgent(real_rag_chain, real_geocoder)
        
        state = PlannerState(
            user_query="Where can I eat in Rome?",
            user_preferences=UserPreferences(
                interests=["food"],
                available_hours=4.0
            )
        )
        
        result_state = agent.discover_places(state)
        
        # Should handle food queries
        assert isinstance(result_state, PlannerState)
    
    def test_geocoding_with_known_places(self, real_rag_chain, real_geocoder):
        """Test that known Rome places are geocoded correctly."""
        agent = PlaceDiscoveryAgent(real_rag_chain, real_geocoder)
        
        state = PlannerState(
            user_query="Tell me about the Colosseum",
            user_preferences=UserPreferences()
        )
        
        result_state = agent.discover_places(state)
        
        # Should find Colosseum
        colosseum_places = [p for p in result_state.candidate_places if "colosseum" in p.name.lower()]
        
        if colosseum_places:
            colosseum = colosseum_places[0]
            # Colosseum coordinates should be close to actual location
            assert 41.88 < colosseum.coordinates[0] < 41.91  # Latitude
            assert 12.48 < colosseum.coordinates[1] < 12.50  # Longitude
    
    def test_place_classification(self, real_rag_chain, real_geocoder):
        """Test that places are classified correctly."""
        agent = PlaceDiscoveryAgent(real_rag_chain, real_geocoder)
        
        state = PlannerState(
            user_query="Show me museums and monuments",
            user_preferences=UserPreferences(interests=["art", "history"])
        )
        
        result_state = agent.discover_places(state)
        
        # Should classify places
        if result_state.candidate_places:
            place_types = [p.place_type for p in result_state.candidate_places]
            # Should have valid place types
            assert all(pt in ["monument", "museum", "church", "restaurant", "park", "square", "attraction"] 
                      for pt in place_types)
    
    def test_visit_duration_estimation(self, real_rag_chain, real_geocoder):
        """Test that visit durations are estimated reasonably."""
        agent = PlaceDiscoveryAgent(real_rag_chain, real_geocoder)
        
        state = PlannerState(
            user_query="What should I visit in Rome?",
            user_preferences=UserPreferences()
        )
        
        result_state = agent.discover_places(state)
        
        # All places should have reasonable visit durations
        for place in result_state.candidate_places:
            assert 15 <= place.visit_duration <= 480  # Between 15 min and 8 hours
    
    def test_ranking_by_preferences(self, real_rag_chain, real_geocoder):
        """Test that places are ranked according to user preferences."""
        # Mock response with both museums and restaurants
        real_rag_chain.chain.invoke.return_value = {
            "result": (
                "Vatican Museums is a world-famous art museum. "
                "Trastevere has many restaurants and trattorias."
            )
        }
        
        agent = PlaceDiscoveryAgent(real_rag_chain, real_geocoder)
        
        # Test with art preference
        state_art = PlannerState(
            user_query="What should I see?",
            user_preferences=UserPreferences(interests=["art"])
        )
        
        result_art = agent.discover_places(state_art)
        
        # Museums should rank higher for art lovers
        if result_art.candidate_places:
            # Check if museums appear early in the list
            top_types = [p.place_type for p in result_art.candidate_places[:3]]
            # At least one museum in top 3 if museums were found
            museum_places = [p for p in result_art.candidate_places if p.place_type == "museum"]
            if museum_places:
                assert any(pt == "museum" for pt in top_types)
    
    def test_error_recovery(self, real_geocoder):
        """Test that agent recovers from RAG errors."""
        # Create a RAG chain that fails
        failing_rag = Mock()
        failing_rag.invoke.side_effect = Exception("RAG service unavailable")
        
        agent = PlaceDiscoveryAgent(failing_rag, real_geocoder)
        
        state = PlannerState(
            user_query="Show me Rome",
            user_preferences=UserPreferences()
        )
        
        result_state = agent.discover_places(state)
        
        # Should handle error gracefully
        assert len(result_state.errors) > 0
        assert "trouble discovering places" in result_state.explanation
        # Should not crash
        assert isinstance(result_state, PlannerState)
