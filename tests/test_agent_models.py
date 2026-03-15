"""
Unit tests for agent data models.

This module contains unit tests for the Pydantic models used in the
multi-agent travel planner system.
"""

import pytest
from datetime import datetime, time
from pydantic import ValidationError
from src.agents.models import (
    UserPreferences,
    Place,
    OpeningHours,
    TicketInfo,
    TravelTime,
    CrowdLevel,
    ItineraryStop,
    Itinerary,
    PlannerState
)


class TestUserPreferences:
    """Tests for UserPreferences model."""
    
    def test_valid_user_preferences(self):
        """Test creating valid UserPreferences."""
        prefs = UserPreferences(
            interests=["art", "history"],
            available_hours=6.0,
            max_budget=150.0,
            max_walking_km=8.0,
            crowd_tolerance="avoid"
        )
        assert prefs.interests == ["art", "history"]
        assert prefs.available_hours == 6.0
        assert prefs.max_budget == 150.0
        assert prefs.crowd_tolerance == "avoid"
    
    def test_default_values(self):
        """Test default values are set correctly."""
        prefs = UserPreferences()
        assert prefs.interests == []
        assert prefs.available_hours == 8.0
        assert prefs.max_budget == 100.0
        assert prefs.max_walking_km == 10.0
        assert prefs.crowd_tolerance == "neutral"
    
    def test_invalid_crowd_tolerance(self):
        """Test that invalid crowd_tolerance raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserPreferences(crowd_tolerance="invalid")
        assert "crowd_tolerance must be one of" in str(exc_info.value)
    
    def test_negative_available_hours(self):
        """Test that negative available_hours raises ValidationError."""
        with pytest.raises(ValidationError):
            UserPreferences(available_hours=-1.0)
    
    def test_available_hours_exceeds_24(self):
        """Test that available_hours > 24 raises ValidationError."""
        with pytest.raises(ValidationError):
            UserPreferences(available_hours=25.0)
    
    def test_negative_budget(self):
        """Test that negative budget raises ValidationError."""
        with pytest.raises(ValidationError):
            UserPreferences(max_budget=-10.0)
    
    def test_zero_walking_distance(self):
        """Test that zero walking distance raises ValidationError."""
        with pytest.raises(ValidationError):
            UserPreferences(max_walking_km=0.0)


class TestPlace:
    """Tests for Place model."""
    
    def test_valid_place(self):
        """Test creating valid Place."""
        place = Place(
            name="Colosseum",
            place_type="monument",
            coordinates=(41.8902, 12.4922),
            visit_duration=120,
            description="Ancient amphitheater",
            rating=4.8
        )
        assert place.name == "Colosseum"
        assert place.coordinates == (41.8902, 12.4922)
        assert place.visit_duration == 120
    
    def test_empty_name(self):
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError):
            Place(name="")
    
    def test_invalid_latitude(self):
        """Test that invalid latitude raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Place(name="Test", coordinates=(91.0, 12.0))
        assert "Latitude must be between -90 and 90" in str(exc_info.value)
    
    def test_invalid_longitude(self):
        """Test that invalid longitude raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Place(name="Test", coordinates=(41.0, 181.0))
        assert "Longitude must be between -180 and 180" in str(exc_info.value)
    
    def test_negative_visit_duration(self):
        """Test that negative visit_duration raises ValidationError."""
        with pytest.raises(ValidationError):
            Place(name="Test", visit_duration=-10)
    
    def test_excessive_visit_duration(self):
        """Test that visit_duration > 480 raises ValidationError."""
        with pytest.raises(ValidationError):
            Place(name="Test", visit_duration=500)
    
    def test_invalid_rating(self):
        """Test that rating > 5 raises ValidationError."""
        with pytest.raises(ValidationError):
            Place(name="Test", rating=6.0)


class TestOpeningHours:
    """Tests for OpeningHours model."""
    
    def test_valid_opening_hours(self):
        """Test creating valid OpeningHours."""
        hours = OpeningHours(
            place_name="Vatican Museums",
            is_open_today=True,
            opening_time=time(9, 0),
            closing_time=time(18, 0),
            last_entry_time=time(16, 0),
            closed_days=["Sunday"]
        )
        assert hours.place_name == "Vatican Museums"
        assert hours.opening_time == time(9, 0)
        assert hours.closing_time == time(18, 0)
    
    def test_opening_after_closing(self):
        """Test that opening_time >= closing_time raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OpeningHours(
                place_name="Test",
                is_open_today=True,
                opening_time=time(18, 0),
                closing_time=time(9, 0)
            )
        assert "opening_time must be before closing_time" in str(exc_info.value)
    
    def test_last_entry_after_closing(self):
        """Test that last_entry_time > closing_time raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OpeningHours(
                place_name="Test",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(18, 0),
                last_entry_time=time(19, 0)
            )
        assert "last_entry_time must be before or equal to closing_time" in str(exc_info.value)
    
    def test_empty_place_name(self):
        """Test that empty place_name raises ValidationError."""
        with pytest.raises(ValidationError):
            OpeningHours(place_name="")


class TestTicketInfo:
    """Tests for TicketInfo model."""
    
    def test_valid_ticket_info(self):
        """Test creating valid TicketInfo."""
        ticket = TicketInfo(
            place_name="Colosseum",
            ticket_required=True,
            reservation_required=True,
            price=16.0,
            skip_the_line_available=True,
            booking_url="https://example.com"
        )
        assert ticket.place_name == "Colosseum"
        assert ticket.ticket_required is True
        assert ticket.price == 16.0
    
    def test_reservation_without_ticket(self):
        """Test that reservation_required=True with ticket_required=False raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TicketInfo(
                place_name="Test",
                ticket_required=False,
                reservation_required=True,
                price=0.0
            )
        assert "reservation_required cannot be True if ticket_required is False" in str(exc_info.value)
    
    def test_negative_price(self):
        """Test that negative price raises ValidationError."""
        with pytest.raises(ValidationError):
            TicketInfo(place_name="Test", price=-5.0)
    
    def test_empty_place_name(self):
        """Test that empty place_name raises ValidationError."""
        with pytest.raises(ValidationError):
            TicketInfo(place_name="")


class TestTravelTime:
    """Tests for TravelTime model."""
    
    def test_valid_travel_time(self):
        """Test creating valid TravelTime."""
        travel = TravelTime(
            duration_minutes=15.5,
            distance_km=1.2,
            mode="pedestrian"
        )
        assert travel.duration_minutes == 15.5
        assert travel.distance_km == 1.2
        assert travel.mode == "pedestrian"
    
    def test_invalid_mode(self):
        """Test that invalid mode raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TravelTime(
                duration_minutes=10.0,
                distance_km=1.0,
                mode="airplane"
            )
        assert "mode must be one of" in str(exc_info.value)
    
    def test_zero_duration(self):
        """Test that zero duration raises ValidationError."""
        with pytest.raises(ValidationError):
            TravelTime(duration_minutes=0.0, distance_km=1.0)
    
    def test_negative_distance(self):
        """Test that negative distance raises ValidationError."""
        with pytest.raises(ValidationError):
            TravelTime(duration_minutes=10.0, distance_km=-1.0)


class TestCrowdLevel:
    """Tests for CrowdLevel enum."""
    
    def test_crowd_level_values(self):
        """Test that CrowdLevel enum has correct values."""
        assert CrowdLevel.LOW.value == "low"
        assert CrowdLevel.MEDIUM.value == "medium"
        assert CrowdLevel.HIGH.value == "high"
        assert CrowdLevel.VERY_HIGH.value == "very_high"


class TestItineraryStop:
    """Tests for ItineraryStop model."""
    
    def test_valid_itinerary_stop(self):
        """Test creating valid ItineraryStop."""
        place = Place(name="Colosseum", coordinates=(41.8902, 12.4922))
        stop = ItineraryStop(
            time=datetime(2024, 6, 15, 9, 0),
            place=place,
            duration_minutes=120,
            notes=["Bring water", "Arrive early"],
            crowd_level=CrowdLevel.HIGH
        )
        assert stop.place.name == "Colosseum"
        assert stop.duration_minutes == 120
        assert len(stop.notes) == 2
    
    def test_zero_duration(self):
        """Test that zero duration raises ValidationError."""
        place = Place(name="Test", coordinates=(41.0, 12.0))
        with pytest.raises(ValidationError):
            ItineraryStop(
                time=datetime(2024, 6, 15, 9, 0),
                place=place,
                duration_minutes=0
            )


class TestItinerary:
    """Tests for Itinerary model."""
    
    def test_valid_itinerary(self):
        """Test creating valid Itinerary."""
        place = Place(name="Colosseum", coordinates=(41.8902, 12.4922))
        stop = ItineraryStop(
            time=datetime(2024, 6, 15, 9, 0),
            place=place,
            duration_minutes=120
        )
        itinerary = Itinerary(
            stops=[stop],
            total_duration_minutes=180,
            total_distance_km=5.5,
            total_cost=50.0,
            feasibility_score=85.0,
            explanation="Great itinerary"
        )
        assert len(itinerary.stops) == 1
        assert itinerary.total_cost == 50.0
        assert itinerary.feasibility_score == 85.0
    
    def test_negative_total_duration(self):
        """Test that negative total_duration raises ValidationError."""
        with pytest.raises(ValidationError):
            Itinerary(
                stops=[],
                total_duration_minutes=-10,
                total_distance_km=0.0,
                total_cost=0.0,
                feasibility_score=50.0,
                explanation=""
            )
    
    def test_negative_total_distance(self):
        """Test that negative total_distance_km raises ValidationError."""
        with pytest.raises(ValidationError):
            Itinerary(
                stops=[],
                total_duration_minutes=0,
                total_distance_km=-5.0,
                total_cost=0.0,
                feasibility_score=50.0,
                explanation=""
            )
    
    def test_negative_total_cost(self):
        """Test that negative total_cost raises ValidationError."""
        with pytest.raises(ValidationError):
            Itinerary(
                stops=[],
                total_duration_minutes=0,
                total_distance_km=0.0,
                total_cost=-10.0,
                feasibility_score=50.0,
                explanation=""
            )
    
    def test_feasibility_score_exceeds_100(self):
        """Test that feasibility_score > 100 raises ValidationError."""
        with pytest.raises(ValidationError):
            Itinerary(
                stops=[],
                total_duration_minutes=0,
                total_distance_km=0.0,
                total_cost=0.0,
                feasibility_score=101.0,
                explanation=""
            )
    
    def test_negative_feasibility_score(self):
        """Test that negative feasibility_score raises ValidationError."""
        with pytest.raises(ValidationError):
            Itinerary(
                stops=[],
                total_duration_minutes=0,
                total_distance_km=0.0,
                total_cost=0.0,
                feasibility_score=-5.0,
                explanation=""
            )


class TestPlannerState:
    """Tests for PlannerState model."""
    
    def test_valid_planner_state(self):
        """Test creating valid PlannerState."""
        state = PlannerState(
            user_query="Show me art museums",
            iteration_count=1,
            max_iterations=3
        )
        assert state.user_query == "Show me art museums"
        assert state.iteration_count == 1
        assert state.is_feasible is False
    
    def test_iteration_count_exceeds_max(self):
        """Test that iteration_count > max_iterations raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PlannerState(
                iteration_count=5,
                max_iterations=3
            )
        assert "iteration_count cannot exceed max_iterations" in str(exc_info.value)
    
    def test_negative_iteration_count(self):
        """Test that negative iteration_count raises ValidationError."""
        with pytest.raises(ValidationError):
            PlannerState(iteration_count=-1)
    
    def test_zero_max_iterations(self):
        """Test that zero max_iterations raises ValidationError."""
        with pytest.raises(ValidationError):
            PlannerState(max_iterations=0)
    
    def test_negative_total_cost(self):
        """Test that negative total_cost raises ValidationError."""
        with pytest.raises(ValidationError):
            PlannerState(total_cost=-50.0)
    
    def test_negative_feasibility_score(self):
        """Test that negative feasibility_score raises ValidationError."""
        with pytest.raises(ValidationError):
            PlannerState(feasibility_score=-10.0)
    
    def test_feasibility_score_exceeds_100(self):
        """Test that feasibility_score > 100 raises ValidationError."""
        with pytest.raises(ValidationError):
            PlannerState(feasibility_score=150.0)
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        state = PlannerState()
        assert state.user_query == ""
        assert state.iteration_count == 0
        assert state.max_iterations == 3
        assert state.is_feasible is False
        assert state.candidate_places == []
        assert state.selected_places == []
