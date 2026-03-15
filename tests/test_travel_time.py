"""Unit and integration tests for Travel Time Agent."""

import pytest
from unittest.mock import Mock, patch
from src.agents.travel_time import (
    calculate_travel_time,
    calculate_route_distance,
    calculate_haversine_distance,
    suggest_transport_mode,
    travel_time_agent
)
from src.agents.models import TravelTime, PlannerState, Place


class TestCalculateHaversineDistance:
    """Test haversine distance calculation."""
    
    def test_same_location(self):
        """Distance between same coordinates should be 0."""
        coord = (41.9028, 12.4964)  # Rome center
        distance = calculate_haversine_distance(coord, coord)
        assert distance == 0.0
    
    def test_known_distance(self):
        """Test with known distance between Rome landmarks."""
        # Colosseum to Trevi Fountain (approximately 1.5 km)
        colosseum = (41.8902, 12.4922)
        trevi = (41.9009, 12.4833)
        distance = calculate_haversine_distance(colosseum, trevi)
        
        # Should be approximately 1.5 km (allow 10% margin)
        assert 1.3 <= distance <= 1.7
    
    def test_symmetric(self):
        """Distance should be same in both directions."""
        coord1 = (41.9028, 12.4964)
        coord2 = (41.8902, 12.4922)
        
        dist1 = calculate_haversine_distance(coord1, coord2)
        dist2 = calculate_haversine_distance(coord2, coord1)
        
        assert dist1 == dist2


class TestCalculateRouteDistance:
    """Test route distance calculation from coordinates."""
    
    def test_empty_route(self):
        """Empty route should have 0 distance."""
        assert calculate_route_distance([]) == 0.0
    
    def test_single_point(self):
        """Single point route should have 0 distance."""
        assert calculate_route_distance([(41.9028, 12.4964)]) == 0.0
    
    def test_two_points(self):
        """Two point route should calculate distance."""
        route = [(41.9028, 12.4964), (41.8902, 12.4922)]
        distance = calculate_route_distance(route)
        assert distance > 0
    
    def test_multi_point_route(self):
        """Multi-point route should sum all segments."""
        route = [
            (41.9028, 12.4964),  # Point A
            (41.8902, 12.4922),  # Point B
            (41.9009, 12.4833)   # Point C
        ]
        distance = calculate_route_distance(route)
        
        # Should be sum of A->B and B->C
        dist_ab = calculate_haversine_distance(route[0], route[1])
        dist_bc = calculate_haversine_distance(route[1], route[2])
        expected = dist_ab + dist_bc
        
        assert abs(distance - expected) < 0.001


class TestSuggestTransportMode:
    """Test transport mode suggestion based on distance."""
    
    def test_short_distance_pedestrian(self):
        """Short distances should suggest pedestrian."""
        assert suggest_transport_mode(0.5) == "pedestrian"
        assert suggest_transport_mode(1.5) == "pedestrian"
    
    def test_medium_distance_public_transport(self):
        """Medium distances should suggest public transport."""
        assert suggest_transport_mode(2.5) == "public_transport"
        assert suggest_transport_mode(4.0) == "public_transport"
    
    def test_long_distance_car(self):
        """Long distances should suggest car."""
        assert suggest_transport_mode(6.0) == "car"
        assert suggest_transport_mode(10.0) == "car"
    
    def test_boundary_cases(self):
        """Test boundary values."""
        assert suggest_transport_mode(2.0) == "public_transport"
        assert suggest_transport_mode(5.0) == "car"


class TestCalculateTravelTime:
    """Test travel time calculation with Router integration."""
    
    @patch('src.agents.travel_time.Router')
    def test_successful_routing(self, mock_router_class):
        """Test successful route calculation."""
        # Setup mock
        mock_router = Mock()
        mock_router_class.return_value = mock_router
        
        # Mock route result: 1 km route taking 12 minutes (720 seconds)
        route_coords = [
            (41.9028, 12.4964),
            (41.9000, 12.4950),
            (41.8902, 12.4922)
        ]
        mock_router.get_route.return_value = (route_coords, 720)
        
        # Calculate travel time
        start = (41.9028, 12.4964)
        end = (41.8902, 12.4922)
        result = calculate_travel_time(start, end, mode="pedestrian")
        
        # Verify result
        assert isinstance(result, TravelTime)
        assert result.duration_minutes == 12.0
        assert result.distance_km > 0
        assert result.mode == "pedestrian"
        
        # Verify Router was called correctly
        mock_router.get_route.assert_called_once_with(start, end, mode="pedestrian")
    
    @patch('src.agents.travel_time.Router')
    def test_routing_failure_fallback(self, mock_router_class):
        """Test fallback to haversine when routing fails."""
        # Setup mock to return None (routing failure)
        mock_router = Mock()
        mock_router_class.return_value = mock_router
        mock_router.get_route.return_value = None
        
        # Calculate travel time
        start = (41.9028, 12.4964)
        end = (41.8902, 12.4922)
        result = calculate_travel_time(start, end, mode="pedestrian")
        
        # Should still return a result using fallback
        assert isinstance(result, TravelTime)
        assert result.duration_minutes > 0
        assert result.distance_km > 0
        assert result.mode == "pedestrian"
    
    @patch('src.agents.travel_time.Router')
    def test_different_transport_modes(self, mock_router_class):
        """Test calculation with different transport modes."""
        mock_router = Mock()
        mock_router_class.return_value = mock_router
        
        route_coords = [(41.9028, 12.4964), (41.8902, 12.4922)]
        mock_router.get_route.return_value = (route_coords, 600)
        
        # Test pedestrian mode
        result = calculate_travel_time(
            (41.9028, 12.4964),
            (41.8902, 12.4922),
            mode="pedestrian"
        )
        assert result.mode == "pedestrian"


class TestTravelTimeAgent:
    """Test the Travel Time Agent function."""
    
    @patch('src.agents.travel_time.Router')
    def test_agent_calculates_pairwise_times(self, mock_router_class):
        """Test agent calculates travel times between all place pairs."""
        # Setup mock router
        mock_router = Mock()
        mock_router_class.return_value = mock_router
        
        # Mock route to return consistent results
        route_coords = [(0, 0), (1, 1)]
        mock_router.get_route.return_value = (route_coords, 600)
        
        # Create test state with 3 places
        places = [
            Place(name="Place A", coordinates=(41.9028, 12.4964)),
            Place(name="Place B", coordinates=(41.8902, 12.4922)),
            Place(name="Place C", coordinates=(41.9009, 12.4833))
        ]
        state = PlannerState(candidate_places=places)
        
        # Run agent
        result_state = travel_time_agent(state)
        
        # Should have calculated 6 travel times (3 pairs * 2 directions)
        assert len(result_state.travel_times) == 6
        
        # Check that all pairs exist
        assert ("Place A", "Place B") in result_state.travel_times
        assert ("Place B", "Place A") in result_state.travel_times
        assert ("Place A", "Place C") in result_state.travel_times
        assert ("Place C", "Place A") in result_state.travel_times
        assert ("Place B", "Place C") in result_state.travel_times
        assert ("Place C", "Place B") in result_state.travel_times
        
        # Check symmetry
        assert (result_state.travel_times[("Place A", "Place B")].duration_minutes ==
                result_state.travel_times[("Place B", "Place A")].duration_minutes)
    
    @patch('src.agents.travel_time.Router')
    def test_agent_handles_routing_failures(self, mock_router_class):
        """Test agent handles routing failures gracefully."""
        # Setup mock to fail routing
        mock_router = Mock()
        mock_router_class.return_value = mock_router
        mock_router.get_route.return_value = None
        
        # Create test state
        places = [
            Place(name="Place A", coordinates=(41.9028, 12.4964)),
            Place(name="Place B", coordinates=(41.8902, 12.4922))
        ]
        state = PlannerState(candidate_places=places)
        
        # Run agent - should not crash
        result_state = travel_time_agent(state)
        
        # Should still have travel times (using fallback)
        assert len(result_state.travel_times) == 2
        assert ("Place A", "Place B") in result_state.travel_times
        assert ("Place B", "Place A") in result_state.travel_times
    
    def test_agent_with_empty_places(self):
        """Test agent with no places."""
        state = PlannerState(candidate_places=[])
        result_state = travel_time_agent(state)
        
        # Should have no travel times
        assert len(result_state.travel_times) == 0
    
    def test_agent_with_single_place(self):
        """Test agent with single place."""
        places = [Place(name="Place A", coordinates=(41.9028, 12.4964))]
        state = PlannerState(candidate_places=places)
        
        result_state = travel_time_agent(state)
        
        # Should have no travel times (no pairs)
        assert len(result_state.travel_times) == 0


class TestTravelTimeIntegration:
    """Integration tests with real Router (requires network)."""
    
    @pytest.mark.integration
    def test_real_router_integration(self):
        """Test with real Router API (requires network)."""
        # Real Rome coordinates
        colosseum = (41.8902, 12.4922)
        trevi = (41.9009, 12.4833)
        
        # Calculate travel time
        result = calculate_travel_time(colosseum, trevi, mode="pedestrian")
        
        # Verify result is reasonable
        assert isinstance(result, TravelTime)
        assert result.duration_minutes > 0
        assert result.duration_minutes < 60  # Should be less than 1 hour
        assert result.distance_km > 0
        assert result.distance_km < 5  # Should be less than 5 km
        assert result.mode == "pedestrian"
    
    @pytest.mark.integration
    def test_agent_with_real_router(self):
        """Test agent with real Router API (requires network)."""
        # Create state with real Rome places
        places = [
            Place(name="Colosseum", coordinates=(41.8902, 12.4922)),
            Place(name="Trevi Fountain", coordinates=(41.9009, 12.4833))
        ]
        state = PlannerState(candidate_places=places)
        
        # Run agent
        result_state = travel_time_agent(state)
        
        # Verify results
        assert len(result_state.travel_times) == 2
        
        travel_time = result_state.travel_times[("Colosseum", "Trevi Fountain")]
        assert travel_time.duration_minutes > 0
        assert travel_time.distance_km > 0
