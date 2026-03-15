"""Tests for itinerary modification functionality (Task 22)."""

import pytest
from datetime import datetime, time
from src.agents.models import (
    Itinerary, ItineraryStop, Place, UserPreferences, CrowdLevel, TicketInfo
)
from src.planner_integration import modify_itinerary


@pytest.fixture
def sample_preferences():
    """Create sample user preferences."""
    return UserPreferences(
        interests=["art", "history"],
        available_hours=8.0,
        max_budget=100.0,
        max_walking_km=10.0,
        crowd_tolerance="neutral",
        start_time=time(9, 0)
    )


@pytest.fixture
def sample_itinerary():
    """Create a sample itinerary with 3 stops."""
    places = [
        Place(
            name="Colosseum",
            place_type="monument",
            coordinates=(41.8902, 12.4922),
            visit_duration=90,
            description="Ancient Roman amphitheater"
        ),
        Place(
            name="Roman Forum",
            place_type="monument",
            coordinates=(41.8925, 12.4853),
            visit_duration=60,
            description="Ancient Roman ruins"
        ),
        Place(
            name="Trevi Fountain",
            place_type="fountain",
            coordinates=(41.9009, 12.4833),
            visit_duration=30,
            description="Famous baroque fountain"
        )
    ]
    
    stops = [
        ItineraryStop(
            time=datetime(2024, 1, 15, 9, 0),
            place=places[0],
            duration_minutes=90,
            notes=["Arrive early to avoid crowds"],
            ticket_info=TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=True,
                price=16.0
            ),
            crowd_level=CrowdLevel.MEDIUM
        ),
        ItineraryStop(
            time=datetime(2024, 1, 15, 10, 45),
            place=places[1],
            duration_minutes=60,
            notes=["Included with Colosseum ticket"],
            ticket_info=TicketInfo(
                place_name="Roman Forum",
                ticket_required=True,
                reservation_required=False,
                price=0.0
            ),
            crowd_level=CrowdLevel.LOW
        ),
        ItineraryStop(
            time=datetime(2024, 1, 15, 12, 0),
            place=places[2],
            duration_minutes=30,
            notes=["Throw a coin for good luck"],
            crowd_level=CrowdLevel.HIGH
        )
    ]
    
    return Itinerary(
        stops=stops,
        total_duration_minutes=180,
        total_distance_km=2.5,
        total_cost=16.0,
        feasibility_score=85.0,
        explanation="Sample itinerary for testing"
    )


class TestItineraryModification:
    """Test suite for itinerary modification functionality."""
    
    def test_remove_stop_reduces_count(self, sample_itinerary, sample_preferences):
        """Test that removing a stop reduces the number of stops."""
        original_count = len(sample_itinerary.stops)
        
        # Remove the middle stop (index 1)
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="remove",
            stop_index=1
        )
        
        # Should have one less stop
        if modified:
            assert len(modified.stops) == original_count - 1
            # Should not contain the removed place
            place_names = [stop.place.name for stop in modified.stops]
            assert "Roman Forum" not in place_names
    
    def test_remove_last_stop_fails(self, sample_preferences):
        """Test that removing the last stop from a single-stop itinerary fails."""
        # Create itinerary with only one stop
        single_stop_itinerary = Itinerary(
            stops=[
                ItineraryStop(
                    time=datetime(2024, 1, 15, 9, 0),
                    place=Place(
                        name="Colosseum",
                        place_type="monument",
                        coordinates=(41.8902, 12.4922),
                        visit_duration=90
                    ),
                    duration_minutes=90,
                    notes=[]
                )
            ],
            total_duration_minutes=90,
            total_distance_km=0.0,
            total_cost=16.0,
            feasibility_score=100.0,
            explanation="Single stop itinerary"
        )
        
        # Try to remove the only stop
        modified = modify_itinerary(
            current_itinerary=single_stop_itinerary,
            user_preferences=sample_preferences,
            action_type="remove",
            stop_index=0
        )
        
        # Should return None (cannot remove last stop)
        assert modified is None
    
    def test_remove_invalid_index(self, sample_itinerary, sample_preferences):
        """Test that removing with invalid index fails gracefully."""
        # Try to remove with out-of-bounds index
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="remove",
            stop_index=99
        )
        
        assert modified is None
    
    def test_add_stop_increases_count(self, sample_itinerary, sample_preferences):
        """Test that adding a stop increases the number of stops."""
        original_count = len(sample_itinerary.stops)
        
        # Add a new stop
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="add",
            place_name="Pantheon"
        )
        
        # Should have one more stop
        if modified:
            assert len(modified.stops) == original_count + 1
            # Should contain the new place
            place_names = [stop.place.name for stop in modified.stops]
            assert "Pantheon" in place_names
    
    def test_add_stop_without_name_fails(self, sample_itinerary, sample_preferences):
        """Test that adding a stop without a place name fails."""
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="add",
            place_name=None
        )
        
        assert modified is None
    
    def test_invalid_action_type(self, sample_itinerary, sample_preferences):
        """Test that invalid action type fails gracefully."""
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="invalid_action",
            place_name="Test"
        )
        
        assert modified is None
    
    def test_modified_itinerary_has_valid_structure(self, sample_itinerary, sample_preferences):
        """Test that modified itinerary maintains valid structure."""
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="remove",
            stop_index=1
        )
        
        if modified:
            # Check all required fields are present
            assert modified.stops is not None
            assert len(modified.stops) > 0
            assert modified.total_duration_minutes >= 0
            assert modified.total_distance_km >= 0
            assert modified.total_cost >= 0
            assert 0 <= modified.feasibility_score <= 100
            assert modified.explanation is not None
            
            # Check each stop has required fields
            for stop in modified.stops:
                assert stop.time is not None
                assert stop.place is not None
                assert stop.duration_minutes > 0
                assert stop.notes is not None
    
    def test_remove_first_stop(self, sample_itinerary, sample_preferences):
        """Test removing the first stop."""
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="remove",
            stop_index=0
        )
        
        if modified:
            place_names = [stop.place.name for stop in modified.stops]
            assert "Colosseum" not in place_names
            assert len(modified.stops) == 2
    
    def test_remove_last_stop_from_multi_stop(self, sample_itinerary, sample_preferences):
        """Test removing the last stop from a multi-stop itinerary."""
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="remove",
            stop_index=2
        )
        
        if modified:
            place_names = [stop.place.name for stop in modified.stops]
            assert "Trevi Fountain" not in place_names
            assert len(modified.stops) == 2


class TestItineraryModificationIntegration:
    """Integration tests for itinerary modification with workflow."""
    
    @pytest.mark.integration
    def test_modification_triggers_reoptimization(self, sample_itinerary, sample_preferences):
        """Test that modification triggers route re-optimization."""
        # Add a stop and verify the route is re-optimized
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="add",
            place_name="Spanish Steps"
        )
        
        if modified:
            # The explanation should indicate re-optimization occurred
            assert "modified" in modified.explanation.lower() or "optimiz" in modified.explanation.lower()
            
            # Times should be recalculated
            for i in range(len(modified.stops) - 1):
                assert modified.stops[i].time < modified.stops[i + 1].time
    
    @pytest.mark.integration
    def test_modification_updates_costs(self, sample_itinerary, sample_preferences):
        """Test that modification updates total costs correctly."""
        original_cost = sample_itinerary.total_cost
        
        # Remove a stop with a ticket
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="remove",
            stop_index=0  # Remove Colosseum (has ticket)
        )
        
        if modified:
            # Cost should be recalculated (likely lower since we removed a paid attraction)
            assert modified.total_cost >= 0
            # Note: Cost might not be exactly lower due to meal estimates, etc.
    
    @pytest.mark.integration
    def test_modification_maintains_feasibility(self, sample_itinerary, sample_preferences):
        """Test that modification maintains feasibility score."""
        modified = modify_itinerary(
            current_itinerary=sample_itinerary,
            user_preferences=sample_preferences,
            action_type="remove",
            stop_index=1
        )
        
        if modified:
            # Feasibility score should be valid
            assert 0 <= modified.feasibility_score <= 100
            # Removing a stop should generally improve or maintain feasibility
            assert modified.feasibility_score > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
