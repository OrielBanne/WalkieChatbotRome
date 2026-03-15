"""Tests for the itinerary display component."""

import pytest
from datetime import datetime, time
from src.agents.models import (
    Itinerary,
    ItineraryStop,
    Place,
    TicketInfo,
    CrowdLevel,
    UserPreferences
)
from src.components.itinerary_display import (
    generate_text_itinerary,
)


@pytest.fixture
def sample_place():
    """Create a sample place for testing."""
    return Place(
        name="Colosseum",
        place_type="monument",
        coordinates=(41.8902, 12.4922),
        visit_duration=90,
        description="Ancient Roman amphitheater",
        rating=4.8
    )


@pytest.fixture
def sample_ticket_info():
    """Create sample ticket info for testing."""
    return TicketInfo(
        place_name="Colosseum",
        ticket_required=True,
        reservation_required=True,
        price=16.0,
        skip_the_line_available=True,
        booking_url="https://example.com/book"
    )


@pytest.fixture
def sample_itinerary_stop(sample_place, sample_ticket_info):
    """Create a sample itinerary stop for testing."""
    return ItineraryStop(
        time=datetime(2024, 6, 15, 9, 0),
        place=sample_place,
        duration_minutes=90,
        notes=["Arrive early to avoid crowds", "Bring water"],
        ticket_info=sample_ticket_info,
        crowd_level=CrowdLevel.MEDIUM
    )


@pytest.fixture
def sample_itinerary(sample_itinerary_stop):
    """Create a sample itinerary for testing."""
    return Itinerary(
        stops=[sample_itinerary_stop],
        total_duration_minutes=240,
        total_distance_km=5.2,
        total_cost=45.50,
        feasibility_score=85.0,
        explanation="Optimized route for ancient Rome"
    )


class TestGenerateTextItinerary:
    """Tests for generate_text_itinerary function."""
    
    def test_generates_text_with_all_sections(self, sample_itinerary):
        """Test that text itinerary includes all required sections."""
        text = generate_text_itinerary(sample_itinerary)
        
        # Check for main sections
        assert "YOUR ROME ITINERARY" in text
        assert "SUMMARY" in text
        assert "STOPS" in text
        assert "PLANNING NOTES" in text
        
    def test_includes_summary_metrics(self, sample_itinerary):
        """Test that summary includes all metrics."""
        text = generate_text_itinerary(sample_itinerary)
        
        assert "Total Duration: 4h 0m" in text
        assert "Walking Distance: 5.2 km" in text
        assert "Total Cost: €45.50" in text
        assert "Feasibility Score: 85/100" in text
        
    def test_includes_stop_details(self, sample_itinerary):
        """Test that stop details are included."""
        text = generate_text_itinerary(sample_itinerary)
        
        assert "Colosseum" in text
        assert "09:00" in text
        assert "90 minutes" in text
        assert "Ticket: €16.00" in text
        assert "Advance booking required" in text
        
    def test_includes_notes(self, sample_itinerary):
        """Test that notes are included."""
        text = generate_text_itinerary(sample_itinerary)
        
        assert "Arrive early to avoid crowds" in text
        assert "Bring water" in text
        
    def test_includes_explanation(self, sample_itinerary):
        """Test that explanation is included."""
        text = generate_text_itinerary(sample_itinerary)
        
        assert "Optimized route for ancient Rome" in text
        
    def test_handles_multiple_stops(self):
        """Test that multiple stops are formatted correctly."""
        stop1 = ItineraryStop(
            time=datetime(2024, 6, 15, 9, 0),
            place=Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=90
            ),
            duration_minutes=90,
            notes=["Note 1"]
        )
        
        stop2 = ItineraryStop(
            time=datetime(2024, 6, 15, 11, 0),
            place=Place(
                name="Roman Forum",
                place_type="monument",
                coordinates=(41.8925, 12.4853),
                visit_duration=60
            ),
            duration_minutes=60,
            notes=["Note 2"]
        )
        
        itinerary = Itinerary(
            stops=[stop1, stop2],
            total_duration_minutes=180,
            total_distance_km=3.5,
            total_cost=30.0,
            feasibility_score=90.0,
            explanation="Test itinerary"
        )
        
        text = generate_text_itinerary(itinerary)
        
        assert "1. Colosseum" in text
        assert "2. Roman Forum" in text
        assert "09:00" in text
        assert "11:00" in text
        
    def test_handles_free_entry(self):
        """Test that free entry places are handled correctly."""
        stop = ItineraryStop(
            time=datetime(2024, 6, 15, 9, 0),
            place=Place(
                name="Trevi Fountain",
                place_type="monument",
                coordinates=(41.9009, 12.4833),
                visit_duration=30
            ),
            duration_minutes=30,
            notes=[],
            ticket_info=TicketInfo(
                place_name="Trevi Fountain",
                ticket_required=False,
                reservation_required=False,
                price=0.0
            )
        )
        
        itinerary = Itinerary(
            stops=[stop],
            total_duration_minutes=30,
            total_distance_km=1.0,
            total_cost=0.0,
            feasibility_score=100.0,
            explanation=""
        )
        
        text = generate_text_itinerary(itinerary)
        
        # Should not include ticket price for free entry
        assert "Ticket: €0.00" not in text
        assert "Trevi Fountain" in text


class TestItineraryDataIntegrity:
    """Tests for data integrity in itinerary display."""
    
    def test_time_ordering_preserved(self):
        """Test that stops maintain chronological order."""
        stops = [
            ItineraryStop(
                time=datetime(2024, 6, 15, 9, 0),
                place=Place(name="Place A", coordinates=(0, 0), visit_duration=60),
                duration_minutes=60,
                notes=[]
            ),
            ItineraryStop(
                time=datetime(2024, 6, 15, 11, 0),
                place=Place(name="Place B", coordinates=(0, 0), visit_duration=60),
                duration_minutes=60,
                notes=[]
            ),
            ItineraryStop(
                time=datetime(2024, 6, 15, 13, 0),
                place=Place(name="Place C", coordinates=(0, 0), visit_duration=60),
                duration_minutes=60,
                notes=[]
            )
        ]
        
        itinerary = Itinerary(
            stops=stops,
            total_duration_minutes=180,
            total_distance_km=5.0,
            total_cost=50.0,
            feasibility_score=80.0,
            explanation=""
        )
        
        text = generate_text_itinerary(itinerary)
        
        # Check that places appear in order
        place_a_pos = text.find("Place A")
        place_b_pos = text.find("Place B")
        place_c_pos = text.find("Place C")
        
        assert place_a_pos < place_b_pos < place_c_pos
        
    def test_crowd_level_display(self):
        """Test that all crowd levels are handled."""
        for crowd_level in [CrowdLevel.LOW, CrowdLevel.MEDIUM, CrowdLevel.HIGH, CrowdLevel.VERY_HIGH]:
            stop = ItineraryStop(
                time=datetime(2024, 6, 15, 9, 0),
                place=Place(name="Test Place", coordinates=(0, 0), visit_duration=60),
                duration_minutes=60,
                notes=[],
                crowd_level=crowd_level
            )
            
            itinerary = Itinerary(
                stops=[stop],
                total_duration_minutes=60,
                total_distance_km=1.0,
                total_cost=10.0,
                feasibility_score=90.0,
                explanation=""
            )
            
            # Should not raise any errors
            text = generate_text_itinerary(itinerary)
            assert "Test Place" in text
            
    def test_handles_empty_notes(self):
        """Test that empty notes list is handled correctly."""
        stop = ItineraryStop(
            time=datetime(2024, 6, 15, 9, 0),
            place=Place(name="Test Place", coordinates=(0, 0), visit_duration=60),
            duration_minutes=60,
            notes=[]
        )
        
        itinerary = Itinerary(
            stops=[stop],
            total_duration_minutes=60,
            total_distance_km=1.0,
            total_cost=10.0,
            feasibility_score=90.0,
            explanation=""
        )
        
        text = generate_text_itinerary(itinerary)
        
        # Should not have "Notes:" section if no notes
        assert "Test Place" in text
        # The word "Notes:" should not appear for this stop
        lines = text.split('\n')
        stop_section = []
        in_stop = False
        for line in lines:
            if "Test Place" in line:
                in_stop = True
            elif in_stop and line.strip() and not line.startswith(' '):
                break
            if in_stop:
                stop_section.append(line)
        
        stop_text = '\n'.join(stop_section)
        assert "Notes:" not in stop_text


class TestUserPreferencesForm:
    """Tests for user preferences form data."""
    
    def test_default_preferences_valid(self):
        """Test that default preferences are valid."""
        prefs = UserPreferences()
        
        assert prefs.available_hours > 0
        assert prefs.max_budget >= 0
        assert prefs.max_walking_km > 0
        assert prefs.crowd_tolerance in ["avoid", "neutral", "dont_care"]
        
    def test_custom_preferences_valid(self):
        """Test that custom preferences can be created."""
        prefs = UserPreferences(
            interests=["art", "food"],
            available_hours=6.0,
            max_budget=150.0,
            max_walking_km=8.0,
            crowd_tolerance="avoid",
            start_time=time(9, 0)
        )
        
        assert prefs.interests == ["art", "food"]
        assert prefs.available_hours == 6.0
        assert prefs.max_budget == 150.0
        assert prefs.max_walking_km == 8.0
        assert prefs.crowd_tolerance == "avoid"
        assert prefs.start_time == time(9, 0)
