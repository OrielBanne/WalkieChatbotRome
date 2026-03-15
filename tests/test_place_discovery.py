"""Unit tests for the Place Discovery Agent.

This module tests the place discovery functionality with mock RAG and geocoder.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.agents.place_discovery import PlaceDiscoveryAgent, place_discovery_agent
from src.agents.models import PlannerState, UserPreferences, Place
from src.models import PlaceMention, Coordinates


@pytest.fixture
def mock_rag_chain():
    """Create a mock RAG chain."""
    mock = Mock()
    mock.invoke.return_value = (
        "The Colosseum is an ancient amphitheater in Rome. "
        "The Trevi Fountain is a famous baroque fountain. "
        "The Pantheon is a former Roman temple."
    )
    return mock


@pytest.fixture
def mock_geocoder():
    """Create a mock geocoder."""
    mock = Mock()
    mock.geocode_place.return_value = Coordinates(
        latitude=41.9028,
        longitude=12.4964,
        accuracy="exact",
        source="mock"
    )
    return mock


@pytest.fixture
def agent(mock_rag_chain, mock_geocoder):
    """Create a PlaceDiscoveryAgent instance."""
    return PlaceDiscoveryAgent(mock_rag_chain, mock_geocoder)


@pytest.fixture
def basic_state():
    """Create a basic planner state."""
    return PlannerState(
        user_query="Show me ancient monuments in Rome",
        user_preferences=UserPreferences(
            interests=["history", "architecture"],
            available_hours=6.0
        )
    )



class TestPlaceDiscoveryAgent:
    """Tests for PlaceDiscoveryAgent class."""
    
    def test_initialization(self, mock_rag_chain, mock_geocoder):
        """Test agent initialization."""
        agent = PlaceDiscoveryAgent(mock_rag_chain, mock_geocoder)
        
        assert agent.rag_chain == mock_rag_chain
        assert agent.geocoder == mock_geocoder
        assert agent.place_extractor is not None
    
    def test_discover_places_success(self, agent, basic_state):
        """Test successful place discovery."""
        result_state = agent.discover_places(basic_state)
        
        # Should have discovered places
        assert len(result_state.candidate_places) > 0
        
        # Each place should have required attributes
        for place in result_state.candidate_places:
            assert isinstance(place, Place)
            assert place.name
            assert place.place_type
            assert place.coordinates
            assert place.visit_duration > 0
    
    def test_discover_places_with_no_results(self, mock_rag_chain, mock_geocoder):
        """Test place discovery when RAG returns no places."""
        # Mock RAG to return text with no known places
        mock_rag_chain.invoke.return_value = "Rome is a beautiful city with many attractions."
        
        agent = PlaceDiscoveryAgent(mock_rag_chain, mock_geocoder)
        state = PlannerState(user_query="Tell me about Rome")
        
        result_state = agent.discover_places(state)
        
        # Should handle gracefully
        assert len(result_state.candidate_places) == 0
        assert "No specific places found" in result_state.explanation
    
    def test_discover_places_limits_to_10(self, mock_rag_chain, mock_geocoder):
        """Test that discovery limits results to top 10 places."""
        # Mock RAG to return many places
        places_text = " ".join([
            "Colosseum", "Trevi Fountain", "Pantheon", "Vatican", 
            "Spanish Steps", "Roman Forum", "Piazza Navona",
            "Castel Sant'Angelo", "Villa Borghese", "Trastevere",
            "Campo de' Fiori", "Piazza del Popolo", "Circus Maximus"
        ])
        mock_rag_chain.invoke.return_value = places_text
        
        agent = PlaceDiscoveryAgent(mock_rag_chain, mock_geocoder)
        state = PlannerState(user_query="Show me all Rome attractions")
        
        result_state = agent.discover_places(state)
        
        # Should limit to 10
        assert len(result_state.candidate_places) <= 10
    
    def test_enrich_place(self, agent):
        """Test place enrichment with metadata."""
        mention = PlaceMention(
            name="Colosseum",
            entity_type="GPE",
            confidence=1.0,
            span=(0, 9),
            context="The Colosseum is ancient"
        )
        rag_response = "The Colosseum is an ancient amphitheater in Rome."
        
        place = agent._enrich_place(mention, rag_response)
        
        assert place.name == "Colosseum"
        assert place.place_type == "monument"
        assert place.visit_duration == 120  # Known duration for Colosseum
        assert place.coordinates != (0.0, 0.0)
        assert place.description is not None
    
    def test_get_coordinates_success(self, agent, mock_geocoder):
        """Test successful coordinate retrieval."""
        coords = agent._get_coordinates("Colosseum")
        
        assert coords[0] == 41.9028
        assert coords[1] == 12.4964
        assert mock_geocoder.geocode_place.called
    
    def test_get_coordinates_fallback(self, agent, mock_geocoder):
        """Test coordinate fallback when geocoding fails."""
        mock_geocoder.geocode_place.return_value = None
        
        coords = agent._get_coordinates("Unknown Place")
        
        # Should return Rome center as fallback
        assert coords == (41.9028, 12.4964)
    
    def test_extract_description(self, agent):
        """Test description extraction from RAG response."""
        rag_response = (
            "The Colosseum is an ancient amphitheater. "
            "It was built in 70-80 AD. "
            "The Colosseum could hold 50,000 spectators."
        )
        
        description = agent._extract_description("Colosseum", rag_response)
        
        assert description is not None
        assert "Colosseum" in description
        assert description.endswith('.')
    
    def test_extract_description_no_match(self, agent):
        """Test description extraction when place not mentioned."""
        rag_response = "Rome is a beautiful city with many attractions."
        
        description = agent._extract_description("Colosseum", rag_response)
        
        assert description is None
    
    def test_rank_by_preferences_with_interests(self, agent):
        """Test ranking places by user interests."""
        places = [
            Place(name="Trattoria", place_type="restaurant", coordinates=(41.9, 12.5), visit_duration=90),
            Place(name="Colosseum", place_type="monument", coordinates=(41.89, 12.49), visit_duration=120),
            Place(name="Vatican Museums", place_type="museum", coordinates=(41.90, 12.45), visit_duration=180),
        ]
        
        preferences = UserPreferences(interests=["history", "art"])
        
        ranked = agent._rank_by_preferences(places, preferences)
        
        # Museum and monument should rank higher than restaurant for history/art interests
        assert ranked[0].place_type in ["museum", "monument"]
        assert ranked[-1].place_type == "restaurant"
    
    def test_rank_by_preferences_no_interests(self, agent):
        """Test ranking when user has no specific interests."""
        places = [
            Place(name="Place A", place_type="monument", coordinates=(41.9, 12.5), visit_duration=60),
            Place(name="Place B", place_type="restaurant", coordinates=(41.89, 12.49), visit_duration=90),
        ]
        
        preferences = UserPreferences(interests=[])
        
        ranked = agent._rank_by_preferences(places, preferences)
        
        # Should return in original order
        assert len(ranked) == 2
    
    def test_calculate_relevance_score_art_interest(self, agent):
        """Test relevance scoring for art interest."""
        museum = Place(name="Museum", place_type="museum", coordinates=(41.9, 12.5), visit_duration=120)
        restaurant = Place(name="Restaurant", place_type="restaurant", coordinates=(41.89, 12.49), visit_duration=90)
        
        preferences = UserPreferences(interests=["art"])
        
        museum_score = agent._calculate_relevance_score(museum, preferences)
        restaurant_score = agent._calculate_relevance_score(restaurant, preferences)
        
        # Museum should score higher for art interest
        assert museum_score > restaurant_score
    
    def test_calculate_relevance_score_with_rating(self, agent):
        """Test that ratings boost relevance score."""
        place_with_rating = Place(
            name="Rated Place", 
            place_type="monument", 
            coordinates=(41.9, 12.5), 
            visit_duration=60,
            rating=4.5
        )
        place_without_rating = Place(
            name="Unrated Place", 
            place_type="monument", 
            coordinates=(41.89, 12.49), 
            visit_duration=60
        )
        
        preferences = UserPreferences(interests=[])
        
        score_with = agent._calculate_relevance_score(place_with_rating, preferences)
        score_without = agent._calculate_relevance_score(place_without_rating, preferences)
        
        # Place with rating should score higher
        assert score_with > score_without
    
    def test_calculate_relevance_score_time_penalty(self, agent):
        """Test that long visits are penalized for limited time."""
        long_visit = Place(name="Long Visit", place_type="museum", coordinates=(41.9, 12.5), visit_duration=180)
        short_visit = Place(name="Short Visit", place_type="monument", coordinates=(41.89, 12.49), visit_duration=30)
        
        # Limited time preference
        preferences = UserPreferences(available_hours=3.0, interests=[])
        
        long_score = agent._calculate_relevance_score(long_visit, preferences)
        short_score = agent._calculate_relevance_score(short_visit, preferences)
        
        # Long visit should be penalized
        assert long_score < short_score
    
    def test_rag_chain_error_handling(self, mock_rag_chain, mock_geocoder):
        """Test error handling when RAG chain fails."""
        mock_rag_chain.invoke.side_effect = Exception("RAG error")
        
        agent = PlaceDiscoveryAgent(mock_rag_chain, mock_geocoder)
        state = PlannerState(user_query="Show me Rome")
        
        result_state = agent.discover_places(state)
        
        # Should handle error gracefully
        assert len(result_state.errors) > 0
        assert "Place discovery error" in result_state.errors[0]
        assert "trouble discovering places" in result_state.explanation


class TestFunctionalWrapper:
    """Tests for the functional wrapper."""
    
    def test_place_discovery_agent_wrapper(self, mock_rag_chain, mock_geocoder, basic_state):
        """Test the functional wrapper for LangGraph integration."""
        result_state = place_discovery_agent(basic_state, mock_rag_chain, mock_geocoder)
        
        assert isinstance(result_state, PlannerState)
        assert len(result_state.candidate_places) > 0
