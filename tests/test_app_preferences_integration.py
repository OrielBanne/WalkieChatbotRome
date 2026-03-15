"""Tests for user preferences integration in the main app."""

import pytest
from datetime import time
from src.agents.models import UserPreferences


class TestUserPreferencesIntegration:
    """Tests for user preferences integration in the app."""
    
    def test_user_preferences_can_be_created_with_all_fields(self):
        """Test that UserPreferences can be created with all fields from the form."""
        # Simulate form inputs
        interests = ["art", "food", "history"]
        available_hours = 8.0
        max_budget = 100.0
        max_walking_km = 10.0
        crowd_tolerance = "neutral"
        start_time = time(hour=9, minute=0)
        
        # Create preferences object
        prefs = UserPreferences(
            interests=interests,
            available_hours=available_hours,
            max_budget=max_budget,
            max_walking_km=max_walking_km,
            crowd_tolerance=crowd_tolerance,
            start_time=start_time
        )
        
        # Verify all fields are set correctly
        assert prefs.interests == interests
        assert prefs.available_hours == available_hours
        assert prefs.max_budget == max_budget
        assert prefs.max_walking_km == max_walking_km
        assert prefs.crowd_tolerance == crowd_tolerance
        assert prefs.start_time == start_time
    
    def test_user_preferences_with_minimal_interests(self):
        """Test that preferences work with no interests selected."""
        prefs = UserPreferences(
            interests=[],
            available_hours=4.0,
            max_budget=50.0,
            max_walking_km=5.0,
            crowd_tolerance="avoid",
            start_time=time(hour=10, minute=0)
        )
        
        assert prefs.interests == []
        assert prefs.available_hours == 4.0
    
    def test_user_preferences_with_all_interests(self):
        """Test that preferences work with all interests selected."""
        all_interests = ["art", "food", "history", "photography"]
        
        prefs = UserPreferences(
            interests=all_interests,
            available_hours=12.0,
            max_budget=200.0,
            max_walking_km=15.0,
            crowd_tolerance="dont_care",
            start_time=time(hour=8, minute=0)
        )
        
        assert prefs.interests == all_interests
        assert len(prefs.interests) == 4
    
    def test_user_preferences_boundary_values(self):
        """Test that preferences work with boundary values."""
        # Minimum values
        prefs_min = UserPreferences(
            interests=[],
            available_hours=2.0,
            max_budget=0.0,
            max_walking_km=2.0,
            crowd_tolerance="avoid",
            start_time=time(hour=6, minute=0)
        )
        
        assert prefs_min.available_hours == 2.0
        assert prefs_min.max_budget == 0.0
        assert prefs_min.max_walking_km == 2.0
        
        # Maximum values
        prefs_max = UserPreferences(
            interests=["art", "food", "history", "photography"],
            available_hours=12.0,
            max_budget=500.0,
            max_walking_km=20.0,
            crowd_tolerance="dont_care",
            start_time=time(hour=14, minute=0)
        )
        
        assert prefs_max.available_hours == 12.0
        assert prefs_max.max_budget == 500.0
        assert prefs_max.max_walking_km == 20.0
    
    def test_user_preferences_crowd_tolerance_options(self):
        """Test all crowd tolerance options."""
        for tolerance in ["avoid", "neutral", "dont_care"]:
            prefs = UserPreferences(
                interests=["art"],
                available_hours=8.0,
                max_budget=100.0,
                max_walking_km=10.0,
                crowd_tolerance=tolerance,
                start_time=time(hour=9, minute=0)
            )
            
            assert prefs.crowd_tolerance == tolerance
    
    def test_user_preferences_invalid_crowd_tolerance(self):
        """Test that invalid crowd tolerance raises error."""
        with pytest.raises(ValueError, match="crowd_tolerance must be one of"):
            UserPreferences(
                interests=["art"],
                available_hours=8.0,
                max_budget=100.0,
                max_walking_km=10.0,
                crowd_tolerance="invalid_option",
                start_time=time(hour=9, minute=0)
            )
    
    def test_user_preferences_start_time_range(self):
        """Test various start times."""
        for hour in [6, 7, 8, 9, 10, 11, 12, 13, 14]:
            prefs = UserPreferences(
                interests=["art"],
                available_hours=8.0,
                max_budget=100.0,
                max_walking_km=10.0,
                crowd_tolerance="neutral",
                start_time=time(hour=hour, minute=0)
            )
            
            assert prefs.start_time.hour == hour
            assert prefs.start_time.minute == 0
    
    def test_user_preferences_serialization(self):
        """Test that preferences can be serialized and deserialized."""
        original_prefs = UserPreferences(
            interests=["art", "food"],
            available_hours=6.0,
            max_budget=120.0,
            max_walking_km=8.0,
            crowd_tolerance="avoid",
            start_time=time(hour=9, minute=30)
        )
        
        # Serialize to dict
        prefs_dict = original_prefs.model_dump()
        
        # Deserialize back
        restored_prefs = UserPreferences(**prefs_dict)
        
        # Verify all fields match
        assert restored_prefs.interests == original_prefs.interests
        assert restored_prefs.available_hours == original_prefs.available_hours
        assert restored_prefs.max_budget == original_prefs.max_budget
        assert restored_prefs.max_walking_km == original_prefs.max_walking_km
        assert restored_prefs.crowd_tolerance == original_prefs.crowd_tolerance
        assert restored_prefs.start_time == original_prefs.start_time
