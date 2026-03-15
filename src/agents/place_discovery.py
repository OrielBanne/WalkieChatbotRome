"""Place Discovery Agent for the Agentic Travel Planner.

This agent discovers relevant places based on user queries and preferences
using the existing RAG system. It extracts, classifies, enriches, and ranks
places to provide personalized recommendations.
"""

from typing import List, Dict, Optional
import logging
from src.agents.models import PlannerState, Place, UserPreferences
from src.agents.tools import classify_place_type, estimate_visit_duration
from src.rag_chain import RAGChain
from src.place_extractor import PlaceExtractor
from src.geocoder import Geocoder

logger = logging.getLogger(__name__)


class PlaceDiscoveryAgent:
    """Agent responsible for discovering and ranking places based on user preferences."""
    
    def __init__(self, rag_chain: RAGChain, geocoder: Geocoder):
        """Initialize the Place Discovery Agent.
        
        Args:
            rag_chain: RAG chain for querying place information
            geocoder: Geocoder for getting place coordinates
        """
        self.rag_chain = rag_chain
        self.place_extractor = PlaceExtractor()
        self.geocoder = geocoder
    
    def discover_places(self, state: PlannerState) -> PlannerState:
        """Discover places using RAG and classify them.
        
        This is the main entry point for the agent. It:
        1. Uses the RAG system to find relevant places
        2. Extracts place names from the response
        3. Enriches each place with metadata
        4. Ranks places by user preferences
        5. Returns top candidates
        
        Args:
            state: Current planner state with user query and preferences
            
        Returns:
            Updated state with candidate_places populated
        """
        try:
            logger.info(f"Discovering places for query: {state.user_query}")
            
            # Use RAG system to get relevant information
            rag_response = self.rag_chain.invoke(state.user_query)
            
            # Extract place mentions from response
            place_mentions = self.place_extractor.extract_places(rag_response)
            
            if not place_mentions:
                logger.warning("No places extracted from RAG response")
                state.explanation += "\n⚠️ No specific places found for your query"
                return state
            
            # Enrich places with metadata
            places = []
            for mention in place_mentions:
                try:
                    place = self._enrich_place(mention, rag_response)
                    places.append(place)
                except Exception as e:
                    logger.warning(f"Failed to enrich place {mention.name}: {e}")
                    continue
            
            # Rank by user preferences
            ranked_places = self._rank_by_preferences(places, state.user_preferences)
            
            # Take top 10 candidates
            state.candidate_places = ranked_places[:10]
            
            logger.info(f"Discovered {len(state.candidate_places)} candidate places")
            state.explanation += f"\n✓ Found {len(state.candidate_places)} places matching your interests"
            
        except Exception as e:
            logger.error(f"Place discovery failed: {e}")
            state.errors.append(f"Place discovery error: {str(e)}")
            state.explanation += "\n⚠️ Had trouble discovering places, using defaults"
        
        return state
    
    def _enrich_place(self, mention, rag_response: str) -> Place:
        """Enrich a place mention with metadata.
        
        Args:
            mention: PlaceMention object from extractor
            rag_response: Full RAG response for context
            
        Returns:
            Enriched Place object with all metadata
        """
        # Classify place type
        place_type = classify_place_type(mention.name)
        
        # Estimate visit duration
        visit_duration = estimate_visit_duration(mention.name, place_type)
        
        # Get coordinates
        coordinates = self._get_coordinates(mention.name)
        
        # Extract description from RAG response
        description = self._extract_description(mention.name, rag_response)
        
        return Place(
            name=mention.name,
            place_type=place_type,
            coordinates=coordinates,
            visit_duration=visit_duration,
            description=description,
            rating=None  # Could be enhanced with ratings API
        )
    
    def _get_coordinates(self, place_name: str) -> tuple:
        """Get coordinates for a place.
        
        Args:
            place_name: Name of the place
            
        Returns:
            Tuple of (latitude, longitude)
        """
        try:
            coords = self.geocoder.geocode_place(place_name)
            if coords:
                return (coords.latitude, coords.longitude)
        except Exception as e:
            logger.warning(f"Geocoding failed for {place_name}: {e}")
        
        # Default to Rome center if geocoding fails
        return (41.9028, 12.4964)
    
    def _extract_description(self, place_name: str, rag_response: str) -> Optional[str]:
        """Extract description for a place from RAG response.
        
        Args:
            place_name: Name of the place
            rag_response: Full RAG response text
            
        Returns:
            Description string or None
        """
        # Simple extraction: find sentences mentioning the place
        sentences = rag_response.split('.')
        relevant_sentences = []
        
        for sentence in sentences:
            if place_name.lower() in sentence.lower():
                relevant_sentences.append(sentence.strip())
        
        if relevant_sentences:
            # Take first 2 sentences
            description = '. '.join(relevant_sentences[:2])
            if description and not description.endswith('.'):
                description += '.'
            return description
        
        return None
    
    def _rank_by_preferences(self, places: List[Place], preferences: UserPreferences) -> List[Place]:
        """Rank places by relevance to user preferences.
        
        Args:
            places: List of places to rank
            preferences: User preferences for ranking
            
        Returns:
            Sorted list of places (most relevant first)
        """
        if not preferences.interests:
            # No specific interests, return as-is
            return places
        
        # Score each place based on preferences
        scored_places = []
        for place in places:
            score = self._calculate_relevance_score(place, preferences)
            scored_places.append((score, place))
        
        # Sort by score (descending)
        scored_places.sort(key=lambda x: x[0], reverse=True)
        
        return [place for score, place in scored_places]
    
    def _calculate_relevance_score(self, place: Place, preferences: UserPreferences) -> float:
        """Calculate relevance score for a place based on preferences.
        
        Args:
            place: Place to score
            preferences: User preferences
            
        Returns:
            Relevance score (higher is better)
        """
        score = 0.0
        
        # Interest-based scoring
        interest_keywords = {
            'art': ['museum', 'gallery', 'church', 'basilica'],
            'history': ['monument', 'forum', 'ancient', 'church', 'basilica'],
            'food': ['restaurant', 'trattoria', 'pizzeria', 'cafe'],
            'photography': ['monument', 'fountain', 'square', 'park'],
            'architecture': ['church', 'basilica', 'monument', 'palace']
        }
        
        for interest in preferences.interests:
            interest_lower = interest.lower()
            if interest_lower in interest_keywords:
                keywords = interest_keywords[interest_lower]
                if any(keyword in place.place_type.lower() for keyword in keywords):
                    score += 10.0
                if place.description and any(keyword in place.description.lower() for keyword in keywords):
                    score += 5.0
        
        # Boost highly rated places
        if place.rating:
            score += place.rating * 2.0
        
        # Penalize very long visits if time is limited
        if preferences.available_hours < 4 and place.visit_duration > 120:
            score -= 5.0
        
        return score


def place_discovery_agent(state: PlannerState) -> PlannerState:
    """Functional wrapper for the Place Discovery Agent.
    
    This function provides a simple interface for use in LangGraph workflows.
    It initializes the required dependencies (RAGChain and Geocoder) internally.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated planner state
    """
    # Skip discovery if places are already selected (e.g., from itinerary modification)
    if state.selected_places:
        logger.info(f"Skipping place discovery - using {len(state.selected_places)} pre-selected places")
        state.candidate_places = state.selected_places
        state.explanation += f"\n✓ Using {len(state.selected_places)} selected places"
        return state
    
    # Initialize dependencies
    # Note: In production, these should be passed in or cached
    try:
        from src.rag_chain import RAGChain
        from src.geocoder import Geocoder
        
        rag_chain = RAGChain()
        geocoder = Geocoder()
        
        agent = PlaceDiscoveryAgent(rag_chain, geocoder)
        return agent.discover_places(state)
    except Exception as e:
        logger.error(f"Failed to initialize place discovery dependencies: {e}")
        state.errors.append(f"Place discovery initialization error: {str(e)}")
        state.explanation += "\n⚠️ Could not initialize place discovery system"
        return state
