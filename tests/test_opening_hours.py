"""Unit tests and property tests for Opening Hours Agent."""

import json
import pytest
from datetime import datetime, time
from pathlib import Path
from unittest.mock import patch, mock_open
from hypothesis import given, strategies as st, settings

from src.agents.opening_hours import (
    load_opening_hours_data,
    get_opening_hours,
    check_is_open,
    get_last_entry_time,
    opening_hours_agent
)
from src.agents.models import OpeningHours, PlannerState, Place, UserPreferences


class TestLoadOpeningHoursData:
    """Tests for load_opening_hours_data function."""
    
    def test_load_valid_data(self):
        """Test loading valid opening hours data."""
        data = load_opening_hours_data()
        
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Colosseum" in data
        assert "Vatican Museums" in data
    
    def test_data_structure(self):
        """Test that loaded data has correct structure."""
        data = load_opening_hours_data()
        
        # Check a known place
        colosseum = data.get("Colosseum")
        assert colosseum is not None
        assert "place_name" in colosseum
        assert "opening_time" in colosseum
        assert "closing_time" in colosseum
        assert "closed_days" in colosseum
    
    def test_data_keyed_by_place_name(self):
        """Test that data is keyed by place_name."""
        data = load_opening_hours_data()
        
        for place_name, place_data in data.items():
            assert place_data["place_name"] == place_name


class TestGetOpeningHours:
    """Tests for get_opening_hours function."""
    
    def test_get_colosseum_hours(self):
        """Test getting opening hours for Colosseum."""
        hours = get_opening_hours("Colosseum")
        
        assert hours is not None
        assert hours.place_name == "Colosseum"
        assert hours.opening_time == time(9, 0)
        assert hours.closing_time == time(19, 0)
        assert hours.last_entry_time == time(18, 0)
    
    def test_get_vatican_museums_hours(self):
        """Test getting opening hours for Vatican Museums."""
        hours = get_opening_hours("Vatican Museums")
        
        assert hours is not None
        assert hours.place_name == "Vatican Museums"
        assert hours.opening_time == time(9, 0)
        assert hours.closing_time == time(18, 0)
        assert hours.last_entry_time == time(16, 0)
        assert "Sunday" in hours.closed_days
    
    def test_get_trevi_fountain_hours(self):
        """Test getting opening hours for Trevi Fountain (24/7)."""
        hours = get_opening_hours("Trevi Fountain")
        
        assert hours is not None
        assert hours.place_name == "Trevi Fountain"
        assert hours.opening_time == time(0, 0)
        assert hours.closing_time == time(23, 59)
        assert hours.last_entry_time is None
        assert len(hours.closed_days) == 0
    
    def test_get_unknown_place(self):
        """Test getting opening hours for unknown place."""
        hours = get_opening_hours("Unknown Place")
        
        assert hours is None
    
    def test_closed_on_monday(self):
        """Test places closed on Monday."""
        # Borghese Gallery is closed on Monday
        hours = get_opening_hours("Borghese Gallery")
        
        assert hours is not None
        assert "Monday" in hours.closed_days
        
        # Test with a Monday date
        monday = datetime(2024, 1, 1)  # January 1, 2024 is a Monday
        hours_monday = get_opening_hours("Borghese Gallery", monday)
        
        # Note: is_open_today checks day name, not specific holidays
        assert "Monday" in hours_monday.closed_days
    
    def test_closed_on_sunday(self):
        """Test places closed on Sunday."""
        # Vatican Museums closed on Sunday
        hours = get_opening_hours("Vatican Museums")
        
        assert hours is not None
        assert "Sunday" in hours.closed_days
    
    def test_with_specific_date(self):
        """Test getting opening hours for a specific date."""
        # Test with a specific date
        test_date = datetime(2024, 6, 15)  # A Saturday
        hours = get_opening_hours("Colosseum", test_date)
        
        assert hours is not None
        assert hours.place_name == "Colosseum"


class TestCheckIsOpen:
    """Tests for check_is_open function."""
    
    def test_colosseum_open_during_hours(self):
        """Test Colosseum is open during operating hours."""
        # Colosseum opens 09:00-19:00
        check_time = datetime(2024, 6, 15, 12, 0)  # Noon on a Saturday
        
        assert check_is_open("Colosseum", check_time) is True
    
    def test_colosseum_closed_before_opening(self):
        """Test Colosseum is closed before opening time."""
        check_time = datetime(2024, 6, 15, 8, 0)  # 8 AM
        
        assert check_is_open("Colosseum", check_time) is False
    
    def test_colosseum_closed_after_closing(self):
        """Test Colosseum is closed after closing time."""
        check_time = datetime(2024, 6, 15, 20, 0)  # 8 PM
        
        assert check_is_open("Colosseum", check_time) is False
    
    def test_trevi_fountain_always_open(self):
        """Test Trevi Fountain is always open (24/7)."""
        # Test various times
        times = [
            datetime(2024, 6, 15, 0, 0),   # Midnight
            datetime(2024, 6, 15, 6, 0),   # 6 AM
            datetime(2024, 6, 15, 12, 0),  # Noon
            datetime(2024, 6, 15, 18, 0),  # 6 PM
            datetime(2024, 6, 15, 23, 0),  # 11 PM
        ]
        
        for check_time in times:
            assert check_is_open("Trevi Fountain", check_time) is True
    
    def test_campo_de_fiori_closed_on_sunday(self):
        """Test Campo de' Fiori is closed on Sunday."""
        # Campo de' Fiori market is closed on Sunday
        sunday = datetime(2024, 6, 16, 10, 0)  # 10 AM on Sunday
        
        assert check_is_open("Campo de' Fiori", sunday) is False
    
    def test_borghese_gallery_closed_on_monday(self):
        """Test Borghese Gallery is closed on Monday."""
        monday = datetime(2024, 6, 17, 10, 0)  # 10 AM on Monday
        
        assert check_is_open("Borghese Gallery", monday) is False
    
    def test_unknown_place_defaults_to_open(self):
        """Test unknown place defaults to open."""
        check_time = datetime(2024, 6, 15, 12, 0)
        
        assert check_is_open("Unknown Place", check_time) is True
    
    def test_at_opening_time(self):
        """Test place is open exactly at opening time."""
        # Colosseum opens at 09:00
        check_time = datetime(2024, 6, 15, 9, 0)
        
        assert check_is_open("Colosseum", check_time) is True
    
    def test_at_closing_time(self):
        """Test place is open exactly at closing time."""
        # Colosseum closes at 19:00
        check_time = datetime(2024, 6, 15, 19, 0)
        
        assert check_is_open("Colosseum", check_time) is True


class TestGetLastEntryTime:
    """Tests for get_last_entry_time function."""
    
    def test_colosseum_last_entry(self):
        """Test getting last entry time for Colosseum."""
        last_entry = get_last_entry_time("Colosseum")
        
        assert last_entry == time(18, 0)
    
    def test_vatican_museums_last_entry(self):
        """Test getting last entry time for Vatican Museums."""
        last_entry = get_last_entry_time("Vatican Museums")
        
        assert last_entry == time(16, 0)
    
    def test_trevi_fountain_no_last_entry(self):
        """Test Trevi Fountain has no last entry time."""
        last_entry = get_last_entry_time("Trevi Fountain")
        
        assert last_entry is None
    
    def test_unknown_place_no_last_entry(self):
        """Test unknown place returns None."""
        last_entry = get_last_entry_time("Unknown Place")
        
        assert last_entry is None


class TestOpeningHoursAgent:
    """Tests for opening_hours_agent function."""
    
    def test_agent_processes_candidate_places(self):
        """Test agent processes all candidate places."""
        # Create test state
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            ),
            Place(
                name="Vatican Museums",
                place_type="museum",
                coordinates=(41.9065, 12.4536),
                visit_duration=180
            )
        ]
        
        state = PlannerState(
            user_query="Show me Rome attractions",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=8.0,
                max_budget=100.0,
                max_walking_km=10.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={},
            optimized_route=None,
            crowd_predictions={},
            total_cost=None,
            feasibility_score=None,
            feasibility_issues=[],
            iteration_count=0,
            max_iterations=3,
            is_feasible=False,
            itinerary=None,
            explanation=""
        )
        
        # Run agent
        updated_state = opening_hours_agent(state)
        
        # Verify opening hours were added
        assert len(updated_state.opening_hours) == 2
        assert "Colosseum" in updated_state.opening_hours
        assert "Vatican Museums" in updated_state.opening_hours
    
    def test_agent_includes_closed_days_info(self):
        """Test agent includes closed days information."""
        # Create a place that has closed days
        places = [
            Place(
                name="Borghese Gallery",
                place_type="museum",
                coordinates=(41.9142, 12.4922),
                visit_duration=120
            )
        ]
        
        state = PlannerState(
            user_query="Visit Borghese Gallery",
            user_preferences=UserPreferences(
                interests=["art"],
                available_hours=4.0,
                max_budget=50.0,
                max_walking_km=5.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={},
            optimized_route=None,
            crowd_predictions={},
            total_cost=None,
            feasibility_score=None,
            feasibility_issues=[],
            iteration_count=0,
            max_iterations=3,
            is_feasible=False,
            itinerary=None,
            explanation=""
        )
        
        updated_state = opening_hours_agent(state)
        
        # Check if opening hours were added
        assert "Borghese Gallery" in updated_state.opening_hours
        hours = updated_state.opening_hours["Borghese Gallery"]
        
        # Verify closed days information is present
        assert "Monday" in hours.closed_days
        assert hours.opening_time == time(9, 0)
        assert hours.closing_time == time(19, 0)
    
    def test_agent_handles_unknown_places(self):
        """Test agent handles places without opening hours data."""
        places = [
            Place(
                name="Unknown Place",
                place_type="attraction",
                coordinates=(41.9, 12.5),
                visit_duration=60
            )
        ]
        
        state = PlannerState(
            user_query="Visit unknown place",
            user_preferences=UserPreferences(
                interests=["general"],
                available_hours=4.0,
                max_budget=50.0,
                max_walking_km=5.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={},
            optimized_route=None,
            crowd_predictions={},
            total_cost=None,
            feasibility_score=None,
            feasibility_issues=[],
            iteration_count=0,
            max_iterations=3,
            is_feasible=False,
            itinerary=None,
            explanation=""
        )
        
        updated_state = opening_hours_agent(state)
        
        # Should create default hours
        assert "Unknown Place" in updated_state.opening_hours
        hours = updated_state.opening_hours["Unknown Place"]
        assert hours.is_open_today is True
        assert hours.opening_time is None
        assert hours.closing_time is None
    
    def test_agent_with_empty_candidate_places(self):
        """Test agent handles empty candidate places list."""
        state = PlannerState(
            user_query="Show me Rome",
            user_preferences=UserPreferences(
                interests=["general"],
                available_hours=4.0,
                max_budget=50.0,
                max_walking_km=5.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=[],
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={},
            optimized_route=None,
            crowd_predictions={},
            total_cost=None,
            feasibility_score=None,
            feasibility_issues=[],
            iteration_count=0,
            max_iterations=3,
            is_feasible=False,
            itinerary=None,
            explanation=""
        )
        
        updated_state = opening_hours_agent(state)
        
        # Should handle gracefully
        assert len(updated_state.opening_hours) == 0


# ============================================================================
# Property-Based Tests using Hypothesis
# ============================================================================

class TestOpeningHoursProperties:
    """Property-based tests for Opening Hours Agent."""
    
    @given(
        place_name=st.sampled_from([
            "Colosseum", "Vatican Museums", "Pantheon", "Borghese Gallery",
            "St. Peter's Basilica", "Castel Sant'Angelo", "Capitoline Museums",
            "Ara Pacis Museum", "Catacombs of San Callisto"
        ])
    )
    @settings(max_examples=50)
    def test_property_opening_before_closing(self, place_name):
        """
        Property Test: Opening time must be before closing time.
        
        **Validates: Requirements 3.1, 3.2**
        
        For any place with defined opening and closing times,
        the opening time must be strictly before the closing time.
        """
        hours = get_opening_hours(place_name)
        
        # If place has both opening and closing times
        if hours and hours.opening_time and hours.closing_time:
            # Opening time must be before closing time
            assert hours.opening_time < hours.closing_time, (
                f"{place_name}: opening time {hours.opening_time} "
                f"must be before closing time {hours.closing_time}"
            )
    
    @given(
        place_name=st.sampled_from([
            "Colosseum", "Vatican Museums", "Pantheon", "Borghese Gallery",
            "St. Peter's Basilica", "Castel Sant'Angelo"
        ])
    )
    @settings(max_examples=50)
    def test_property_last_entry_before_closing(self, place_name):
        """
        Property Test: Last entry time must be before or equal to closing time.
        
        **Validates: Requirements 3.2**
        
        For any place with defined last entry and closing times,
        the last entry time must be before or equal to the closing time.
        """
        hours = get_opening_hours(place_name)
        
        # If place has both last entry and closing times
        if hours and hours.last_entry_time and hours.closing_time:
            # Last entry must be before or at closing time
            assert hours.last_entry_time <= hours.closing_time, (
                f"{place_name}: last entry time {hours.last_entry_time} "
                f"must be before or equal to closing time {hours.closing_time}"
            )
    
    @given(
        place_name=st.sampled_from([
            "Colosseum", "Vatican Museums", "Pantheon", "Trevi Fountain",
            "Spanish Steps", "Piazza Navona"
        ])
    )
    @settings(max_examples=30)
    def test_property_consistent_retrieval(self, place_name):
        """
        Property Test: Multiple retrievals return consistent data.
        
        **Validates: Implementation correctness**
        
        Retrieving opening hours for the same place multiple times
        should return identical data.
        """
        hours1 = get_opening_hours(place_name)
        hours2 = get_opening_hours(place_name)
        
        if hours1 and hours2:
            assert hours1.place_name == hours2.place_name
            assert hours1.opening_time == hours2.opening_time
            assert hours1.closing_time == hours2.closing_time
            assert hours1.last_entry_time == hours2.last_entry_time
            assert hours1.closed_days == hours2.closed_days
    
    @given(
        place_name=st.sampled_from([
            "Colosseum", "Vatican Museums", "Borghese Gallery"
        ]),
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=100)
    def test_property_check_is_open_deterministic(self, place_name, hour, minute):
        """
        Property Test: check_is_open is deterministic.
        
        **Validates: Requirements 3.1, 3.4**
        
        Checking if a place is open at the same time multiple times
        should return the same result.
        """
        check_time = datetime(2024, 6, 15, hour, minute)  # Saturday
        
        result1 = check_is_open(place_name, check_time)
        result2 = check_is_open(place_name, check_time)
        
        assert result1 == result2, (
            f"check_is_open for {place_name} at {check_time} "
            f"returned inconsistent results"
        )
