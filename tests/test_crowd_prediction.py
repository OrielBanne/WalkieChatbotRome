"""Unit tests and property tests for Crowd Prediction Agent."""

import pytest
from datetime import datetime, time
from hypothesis import given, strategies as st, settings

from src.agents.crowd_prediction import (
    load_crowd_patterns,
    get_season,
    is_cruise_ship_day,
    predict_crowd_level,
    get_best_visiting_time,
    crowd_prediction_agent
)
from src.agents.models import CrowdLevel, PlannerState, Place, UserPreferences


class TestLoadCrowdPatterns:
    """Tests for load_crowd_patterns function."""
    
    def test_load_valid_data(self):
        """Test loading valid crowd pattern data."""
        data = load_crowd_patterns()
        
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Colosseum" in data
        assert "Vatican Museums" in data
    
    def test_data_structure(self):
        """Test that loaded data has correct structure."""
        data = load_crowd_patterns()
        
        # Check a known place
        colosseum = data.get("Colosseum")
        assert colosseum is not None
        assert "base_level" in colosseum
        assert "peak_hours" in colosseum
        assert "low_hours" in colosseum
        assert "peak_days" in colosseum
        assert "cruise_ship_impact" in colosseum
        assert "seasonal_multiplier" in colosseum
    
    def test_seasonal_multiplier_has_all_seasons(self):
        """Test that seasonal multipliers include all four seasons."""
        data = load_crowd_patterns()
        
        for place_name, pattern in data.items():
            seasonal = pattern.get("seasonal_multiplier", {})
            assert "winter" in seasonal, f"{place_name} missing winter multiplier"
            assert "spring" in seasonal, f"{place_name} missing spring multiplier"
            assert "summer" in seasonal, f"{place_name} missing summer multiplier"
            assert "fall" in seasonal, f"{place_name} missing fall multiplier"


class TestGetSeason:
    """Tests for get_season function."""
    
    def test_winter_months(self):
        """Test winter season detection."""
        assert get_season(datetime(2024, 12, 15)) == "winter"
        assert get_season(datetime(2024, 1, 15)) == "winter"
        assert get_season(datetime(2024, 2, 15)) == "winter"
    
    def test_spring_months(self):
        """Test spring season detection."""
        assert get_season(datetime(2024, 3, 15)) == "spring"
        assert get_season(datetime(2024, 4, 15)) == "spring"
        assert get_season(datetime(2024, 5, 15)) == "spring"
    
    def test_summer_months(self):
        """Test summer season detection."""
        assert get_season(datetime(2024, 6, 15)) == "summer"
        assert get_season(datetime(2024, 7, 15)) == "summer"
        assert get_season(datetime(2024, 8, 15)) == "summer"
    
    def test_fall_months(self):
        """Test fall season detection."""
        assert get_season(datetime(2024, 9, 15)) == "fall"
        assert get_season(datetime(2024, 10, 15)) == "fall"
        assert get_season(datetime(2024, 11, 15)) == "fall"


class TestIsCruiseShipDay:
    """Tests for is_cruise_ship_day function."""
    
    def test_cruise_season_tuesday(self):
        """Test Tuesday in cruise season is a cruise ship day."""
        # April Tuesday
        tuesday_april = datetime(2024, 4, 2)  # Tuesday
        assert is_cruise_ship_day(tuesday_april) is True
    
    def test_cruise_season_thursday(self):
        """Test Thursday in cruise season is a cruise ship day."""
        # May Thursday
        thursday_may = datetime(2024, 5, 2)  # Thursday
        assert is_cruise_ship_day(thursday_may) is True
    
    def test_cruise_season_other_days(self):
        """Test other days in cruise season are not cruise ship days."""
        # Monday in cruise season
        monday_june = datetime(2024, 6, 3)  # Monday
        assert is_cruise_ship_day(monday_june) is False
        
        # Friday in cruise season
        friday_july = datetime(2024, 7, 5)  # Friday
        assert is_cruise_ship_day(friday_july) is False
    
    def test_off_season_tuesday(self):
        """Test Tuesday outside cruise season is not a cruise ship day."""
        # January Tuesday
        tuesday_jan = datetime(2024, 1, 2)  # Tuesday
        assert is_cruise_ship_day(tuesday_jan) is False
        
        # November Tuesday
        tuesday_nov = datetime(2024, 11, 5)  # Tuesday
        assert is_cruise_ship_day(tuesday_nov) is False
    
    def test_off_season_thursday(self):
        """Test Thursday outside cruise season is not a cruise ship day."""
        # February Thursday
        thursday_feb = datetime(2024, 2, 1)  # Thursday
        assert is_cruise_ship_day(thursday_feb) is False
        
        # December Thursday
        thursday_dec = datetime(2024, 12, 5)  # Thursday
        assert is_cruise_ship_day(thursday_dec) is False


class TestPredictCrowdLevel:
    """Tests for predict_crowd_level function."""
    
    def test_colosseum_peak_hour(self):
        """Test Colosseum crowd level during peak hours."""
        # Peak hour: 12:00 on a Saturday in summer
        visit_time = datetime(2024, 7, 13, 12, 0)  # Saturday
        
        crowd_level = predict_crowd_level("Colosseum", visit_time)
        
        # Should be high or very high
        assert crowd_level in [CrowdLevel.HIGH, CrowdLevel.VERY_HIGH]
    
    def test_colosseum_low_hour(self):
        """Test Colosseum crowd level during low hours."""
        # Low hour: 8:00 on a Tuesday in winter
        visit_time = datetime(2024, 1, 9, 8, 0)  # Tuesday
        
        crowd_level = predict_crowd_level("Colosseum", visit_time)
        
        # Should be low or medium
        assert crowd_level in [CrowdLevel.LOW, CrowdLevel.MEDIUM]
    
    def test_vatican_museums_cruise_ship_day(self):
        """Test Vatican Museums on cruise ship day."""
        # Tuesday in cruise season (April-October)
        visit_time = datetime(2024, 5, 7, 11, 0)  # Tuesday, May
        
        crowd_level = predict_crowd_level("Vatican Museums", visit_time, is_cruise_day=True)
        
        # Should be very high due to cruise ship impact
        assert crowd_level == CrowdLevel.VERY_HIGH
    
    def test_trevi_fountain_evening(self):
        """Test Trevi Fountain in the evening."""
        # Evening peak hour: 19:00
        visit_time = datetime(2024, 6, 15, 19, 0)
        
        crowd_level = predict_crowd_level("Trevi Fountain", visit_time)
        
        # Should be high or very high
        assert crowd_level in [CrowdLevel.HIGH, CrowdLevel.VERY_HIGH]
    
    def test_trevi_fountain_early_morning(self):
        """Test Trevi Fountain early morning."""
        # Early morning low hour: 7:00 in winter (lower season multiplier)
        visit_time = datetime(2024, 1, 15, 7, 0)  # Winter
        
        crowd_level = predict_crowd_level("Trevi Fountain", visit_time)
        
        # Should be low or medium in winter early morning
        assert crowd_level in [CrowdLevel.LOW, CrowdLevel.MEDIUM]
    
    def test_unknown_place_defaults_to_medium(self):
        """Test unknown place defaults to medium crowd level."""
        visit_time = datetime(2024, 6, 15, 12, 0)
        
        crowd_level = predict_crowd_level("Unknown Place", visit_time)
        
        assert crowd_level == CrowdLevel.MEDIUM
    
    def test_seasonal_variation_summer_vs_winter(self):
        """Test seasonal variation affects crowd levels."""
        # Same place, same time, different seasons
        summer_time = datetime(2024, 7, 15, 12, 0)  # Summer
        winter_time = datetime(2024, 1, 15, 12, 0)  # Winter
        
        summer_crowd = predict_crowd_level("Colosseum", summer_time)
        winter_crowd = predict_crowd_level("Colosseum", winter_time)
        
        # Summer should be busier than winter
        crowd_order = [CrowdLevel.LOW, CrowdLevel.MEDIUM, CrowdLevel.HIGH, CrowdLevel.VERY_HIGH]
        summer_idx = crowd_order.index(summer_crowd)
        winter_idx = crowd_order.index(winter_crowd)
        
        assert summer_idx >= winter_idx
    
    def test_peak_day_increases_crowds(self):
        """Test that peak days increase crowd levels."""
        # Vatican Museums: Wednesday is peak day
        wednesday = datetime(2024, 6, 12, 11, 0)  # Wednesday
        monday = datetime(2024, 6, 10, 11, 0)  # Monday (not peak)
        
        wednesday_crowd = predict_crowd_level("Vatican Museums", wednesday)
        monday_crowd = predict_crowd_level("Vatican Museums", monday)
        
        # Wednesday should be busier or equal
        crowd_order = [CrowdLevel.LOW, CrowdLevel.MEDIUM, CrowdLevel.HIGH, CrowdLevel.VERY_HIGH]
        wednesday_idx = crowd_order.index(wednesday_crowd)
        monday_idx = crowd_order.index(monday_crowd)
        
        assert wednesday_idx >= monday_idx


class TestGetBestVisitingTime:
    """Tests for get_best_visiting_time function."""
    
    def test_colosseum_best_time(self):
        """Test getting best visiting time for Colosseum."""
        date = datetime(2024, 6, 15)
        
        best_hour = get_best_visiting_time("Colosseum", date)
        
        assert best_hour is not None
        assert best_hour in [8, 9, 17, 18]  # Low hours for Colosseum
    
    def test_vatican_museums_best_time(self):
        """Test getting best visiting time for Vatican Museums."""
        date = datetime(2024, 6, 15)
        
        best_hour = get_best_visiting_time("Vatican Museums", date)
        
        assert best_hour is not None
        assert best_hour in [8, 9, 16, 17]  # Low hours for Vatican
    
    def test_unknown_place_returns_none(self):
        """Test unknown place returns None."""
        date = datetime(2024, 6, 15)
        
        best_hour = get_best_visiting_time("Unknown Place", date)
        
        assert best_hour is None


class TestCrowdPredictionAgent:
    """Tests for crowd_prediction_agent function."""
    
    def test_agent_processes_optimized_route(self):
        """Test agent processes all places in optimized route."""
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
                crowd_tolerance="neutral",
                start_time=time(9, 0)
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={},
            optimized_route=["Colosseum", "Vatican Museums"],
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
        updated_state = crowd_prediction_agent(state)
        
        # Verify crowd predictions were added
        assert len(updated_state.crowd_predictions) == 2
        assert "Colosseum" in updated_state.crowd_predictions
        assert "Vatican Museums" in updated_state.crowd_predictions
    
    def test_agent_warns_about_very_high_crowds(self):
        """Test agent adds warnings for very high crowd levels."""
        places = [
            Place(
                name="Vatican Museums",
                place_type="museum",
                coordinates=(41.9065, 12.4536),
                visit_duration=180
            )
        ]
        
        state = PlannerState(
            user_query="Visit Vatican Museums",
            user_preferences=UserPreferences(
                interests=["art"],
                available_hours=4.0,
                max_budget=50.0,
                max_walking_km=5.0,
                crowd_tolerance="avoid",
                start_time=time(11, 0)  # Peak hour
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={},
            optimized_route=["Vatican Museums"],
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
        
        updated_state = crowd_prediction_agent(state)
        
        # Check if warning was added
        assert "Vatican Museums" in updated_state.crowd_predictions
        # Explanation should contain warning if crowd level is very high
        if updated_state.crowd_predictions["Vatican Museums"] == CrowdLevel.VERY_HIGH:
            assert "Vatican Museums" in updated_state.explanation
            assert "crowded" in updated_state.explanation.lower()
    
    def test_agent_detects_cruise_ship_day(self):
        """Test agent detects and warns about cruise ship days."""
        places = [
            Place(
                name="Trevi Fountain",
                place_type="monument",
                coordinates=(41.9009, 12.4833),
                visit_duration=30
            )
        ]
        
        # Create a Tuesday in cruise season
        from unittest.mock import patch
        with patch('src.agents.crowd_prediction.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 5, 7, 9, 0)  # Tuesday, May
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            state = PlannerState(
                user_query="Visit Trevi Fountain",
                user_preferences=UserPreferences(
                    interests=["sightseeing"],
                    available_hours=2.0,
                    max_budget=20.0,
                    max_walking_km=3.0,
                    crowd_tolerance="neutral",
                    start_time=time(10, 0)
                ),
                candidate_places=places,
                selected_places=[],
                opening_hours={},
                ticket_info={},
                travel_times={},
                optimized_route=["Trevi Fountain"],
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
            
            updated_state = crowd_prediction_agent(state)
            
            # Should warn about cruise ship day
            assert "cruise" in updated_state.explanation.lower()
    
    def test_agent_handles_empty_route(self):
        """Test agent handles empty optimized route."""
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
        
        updated_state = crowd_prediction_agent(state)
        
        # Should handle gracefully
        assert len(updated_state.crowd_predictions) == 0
    
    def test_agent_skips_lunch_breaks(self):
        """Test agent skips LUNCH_BREAK entries in route."""
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            )
        ]
        
        state = PlannerState(
            user_query="Visit Colosseum with lunch",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=6.0,
                max_budget=80.0,
                max_walking_km=5.0,
                crowd_tolerance="neutral",
                start_time=time(9, 0)
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={},
            optimized_route=["Colosseum", "LUNCH_BREAK"],
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
        
        updated_state = crowd_prediction_agent(state)
        
        # Should only have prediction for Colosseum, not LUNCH_BREAK
        assert len(updated_state.crowd_predictions) == 1
        assert "Colosseum" in updated_state.crowd_predictions
        assert "LUNCH_BREAK" not in updated_state.crowd_predictions


# ============================================================================
# Property-Based Tests using Hypothesis
# ============================================================================

class TestCrowdPredictionProperties:
    """Property-based tests for Crowd Prediction Agent."""
    
    @given(
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28)
    )
    @settings(max_examples=50)
    def test_property_season_is_valid(self, month, day):
        """
        Property Test: get_season always returns a valid season.
        
        **Validates: Requirements 7.2**
        
        For any valid date, get_season must return one of the four seasons.
        """
        date = datetime(2024, month, day)
        season = get_season(date)
        
        assert season in ["winter", "spring", "summer", "fall"]
    
    @given(
        place_name=st.sampled_from([
            "Colosseum", "Vatican Museums", "Trevi Fountain", "Pantheon",
            "Spanish Steps", "Roman Forum", "Borghese Gallery"
        ]),
        hour=st.integers(min_value=0, max_value=23),
        month=st.integers(min_value=1, max_value=12)
    )
    @settings(max_examples=100)
    def test_property_crowd_level_is_valid(self, place_name, hour, month):
        """
        Property Test: predict_crowd_level always returns a valid CrowdLevel.
        
        **Validates: Requirements 7.1**
        
        For any place and time, the predicted crowd level must be one of
        the four valid CrowdLevel enum values.
        """
        visit_time = datetime(2024, month, 15, hour, 0)
        
        crowd_level = predict_crowd_level(place_name, visit_time)
        
        assert isinstance(crowd_level, CrowdLevel)
        assert crowd_level in [
            CrowdLevel.LOW,
            CrowdLevel.MEDIUM,
            CrowdLevel.HIGH,
            CrowdLevel.VERY_HIGH
        ]
    
    @given(
        place_name=st.sampled_from([
            "Colosseum", "Vatican Museums", "Trevi Fountain"
        ]),
        hour=st.integers(min_value=0, max_value=23)
    )
    @settings(max_examples=50)
    def test_property_prediction_is_deterministic(self, place_name, hour):
        """
        Property Test: Predictions are deterministic for same inputs.
        
        **Validates: Implementation correctness**
        
        Predicting crowd level for the same place and time multiple times
        should return the same result.
        """
        visit_time = datetime(2024, 6, 15, hour, 0)
        
        result1 = predict_crowd_level(place_name, visit_time)
        result2 = predict_crowd_level(place_name, visit_time)
        
        assert result1 == result2
    
    @given(
        place_name=st.sampled_from([
            "Colosseum", "Vatican Museums", "Trevi Fountain", "Pantheon"
        ])
    )
    @settings(max_examples=30)
    def test_property_cruise_day_increases_crowds(self, place_name):
        """
        Property Test: Cruise ship days increase or maintain crowd levels.
        
        **Validates: Requirements 7.3**
        
        For any place, the crowd level on a cruise ship day should be
        greater than or equal to a non-cruise day at the same time.
        """
        # Peak hour to maximize effect
        visit_time = datetime(2024, 6, 15, 12, 0)
        
        normal_crowd = predict_crowd_level(place_name, visit_time, is_cruise_day=False)
        cruise_crowd = predict_crowd_level(place_name, visit_time, is_cruise_day=True)
        
        crowd_order = [CrowdLevel.LOW, CrowdLevel.MEDIUM, CrowdLevel.HIGH, CrowdLevel.VERY_HIGH]
        normal_idx = crowd_order.index(normal_crowd)
        cruise_idx = crowd_order.index(cruise_crowd)
        
        assert cruise_idx >= normal_idx, (
            f"{place_name}: cruise day crowd ({cruise_crowd}) should be >= "
            f"normal day crowd ({normal_crowd})"
        )
    
    @given(
        place_name=st.sampled_from([
            "Colosseum", "Vatican Museums", "Pantheon"
        ])
    )
    @settings(max_examples=30)
    def test_property_summer_busier_than_winter(self, place_name):
        """
        Property Test: Summer is busier than winter for tourist attractions.
        
        **Validates: Requirements 7.2**
        
        For major tourist attractions, summer crowd levels should be
        greater than or equal to winter crowd levels at the same time.
        """
        # Same time, different seasons
        summer_time = datetime(2024, 7, 15, 12, 0)
        winter_time = datetime(2024, 1, 15, 12, 0)
        
        summer_crowd = predict_crowd_level(place_name, summer_time)
        winter_crowd = predict_crowd_level(place_name, winter_time)
        
        crowd_order = [CrowdLevel.LOW, CrowdLevel.MEDIUM, CrowdLevel.HIGH, CrowdLevel.VERY_HIGH]
        summer_idx = crowd_order.index(summer_crowd)
        winter_idx = crowd_order.index(winter_crowd)
        
        assert summer_idx >= winter_idx, (
            f"{place_name}: summer crowd ({summer_crowd}) should be >= "
            f"winter crowd ({winter_crowd})"
        )
