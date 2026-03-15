"""Unit tests and property tests for Feasibility Agent."""

import pytest
from datetime import datetime, time, timedelta
from hypothesis import given, strategies as st, settings

from src.agents.feasibility import (
    calculate_total_distance,
    calculate_total_time,
    check_opening_hours_conflicts,
    calculate_feasibility_score,
    suggest_improvements,
    feasibility_agent
)
from src.agents.models import (
    PlannerState,
    Place,
    UserPreferences,
    OpeningHours,
    TravelTime
)


class TestCalculateTotalDistance:
    """Tests for calculate_total_distance function."""
    
    def test_single_segment(self):
        """Test calculating distance for a single segment."""
        route = ["Colosseum", "Roman Forum"]
        travel_times = {
            ("Colosseum", "Roman Forum"): TravelTime(
                duration_minutes=10.0,
                distance_km=0.8,
                mode="pedestrian"
            )
        }
        
        distance = calculate_total_distance(route, travel_times)
        
        assert distance == 0.8
    
    def test_multiple_segments(self):
        """Test calculating distance for multiple segments."""
        route = ["Colosseum", "Roman Forum", "Trevi Fountain"]
        travel_times = {
            ("Colosseum", "Roman Forum"): TravelTime(
                duration_minutes=10.0,
                distance_km=0.8,
                mode="pedestrian"
            ),
            ("Roman Forum", "Trevi Fountain"): TravelTime(
                duration_minutes=15.0,
                distance_km=1.2,
                mode="pedestrian"
            )
        }
        
        distance = calculate_total_distance(route, travel_times)
        
        assert distance == 2.0
    
    def test_lunch_break_ignored(self):
        """Test that LUNCH_BREAK is ignored in distance calculation."""
        route = ["Colosseum", "LUNCH_BREAK", "Vatican Museums"]
        travel_times = {
            ("Colosseum", "Vatican Museums"): TravelTime(
                duration_minutes=30.0,
                distance_km=5.0,
                mode="metro"
            )
        }
        
        distance = calculate_total_distance(route, travel_times)
        
        assert distance == 0.0  # No segment crosses LUNCH_BREAK
    
    def test_missing_travel_time(self):
        """Test handling missing travel time data."""
        route = ["Colosseum", "Roman Forum"]
        travel_times = {}
        
        distance = calculate_total_distance(route, travel_times)
        
        assert distance == 0.0
    
    def test_empty_route(self):
        """Test empty route returns zero distance."""
        route = []
        travel_times = {}
        
        distance = calculate_total_distance(route, travel_times)
        
        assert distance == 0.0



class TestCalculateTotalTime:
    """Tests for calculate_total_time function."""
    
    def test_single_place(self):
        """Test calculating time for a single place."""
        route = ["Colosseum"]
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            )
        ]
        travel_times = {}
        
        total_time = calculate_total_time(route, places, travel_times)
        
        assert total_time == 120
    
    def test_multiple_places_with_travel(self):
        """Test calculating time for multiple places with travel."""
        route = ["Colosseum", "Roman Forum"]
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            ),
            Place(
                name="Roman Forum",
                place_type="monument",
                coordinates=(41.8925, 12.4853),
                visit_duration=90
            )
        ]
        travel_times = {
            ("Colosseum", "Roman Forum"): TravelTime(
                duration_minutes=10.0,
                distance_km=0.8,
                mode="pedestrian"
            )
        }
        
        total_time = calculate_total_time(route, places, travel_times)
        
        # 120 (Colosseum) + 10 (travel) + 90 (Roman Forum) = 220
        assert total_time == 220
    
    def test_lunch_break_adds_time(self):
        """Test that LUNCH_BREAK adds 60 minutes."""
        route = ["Colosseum", "LUNCH_BREAK", "Vatican Museums"]
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
        travel_times = {}
        
        total_time = calculate_total_time(route, places, travel_times)
        
        # 120 (Colosseum) + 60 (lunch) + 180 (Vatican) = 360
        assert total_time == 360
    
    def test_missing_place_data(self):
        """Test handling missing place data."""
        route = ["Colosseum", "Unknown Place"]
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            )
        ]
        travel_times = {}
        
        total_time = calculate_total_time(route, places, travel_times)
        
        # Only Colosseum time counted
        assert total_time == 120


class TestCheckOpeningHoursConflicts:
    """Tests for check_opening_hours_conflicts function."""
    
    def test_no_conflicts(self):
        """Test itinerary with no opening hours conflicts."""
        route = ["Colosseum"]
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            )
        ]
        opening_hours = {
            "Colosseum": OpeningHours(
                place_name="Colosseum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            )
        }
        travel_times = {}
        start_time = datetime.now().replace(hour=10, minute=0)
        
        conflicts = check_opening_hours_conflicts(
            route, places, opening_hours, travel_times, start_time
        )
        
        assert len(conflicts) == 0
    
    def test_closed_today(self):
        """Test detecting place closed today."""
        route = ["Colosseum"]
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            )
        ]
        opening_hours = {
            "Colosseum": OpeningHours(
                place_name="Colosseum",
                is_open_today=False,
                opening_time=None,
                closing_time=None,
                last_entry_time=None,
                closed_days=["Monday"]
            )
        }
        travel_times = {}
        start_time = datetime.now()
        
        conflicts = check_opening_hours_conflicts(
            route, places, opening_hours, travel_times, start_time
        )
        
        assert len(conflicts) == 1
        assert "closed today" in conflicts[0]
    
    def test_arrive_before_opening(self):
        """Test detecting arrival before opening time."""
        route = ["Colosseum"]
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            )
        ]
        opening_hours = {
            "Colosseum": OpeningHours(
                place_name="Colosseum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            )
        }
        travel_times = {}
        start_time = datetime.now().replace(hour=7, minute=0)
        
        conflicts = check_opening_hours_conflicts(
            route, places, opening_hours, travel_times, start_time
        )
        
        assert len(conflicts) == 1
        assert "before opening" in conflicts[0]
    
    def test_arrive_after_last_entry(self):
        """Test detecting arrival after last entry time."""
        route = ["Colosseum"]
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            )
        ]
        opening_hours = {
            "Colosseum": OpeningHours(
                place_name="Colosseum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            )
        }
        travel_times = {}
        start_time = datetime.now().replace(hour=18, minute=30)
        
        conflicts = check_opening_hours_conflicts(
            route, places, opening_hours, travel_times, start_time
        )
        
        assert len(conflicts) == 1
        assert "after last entry" in conflicts[0]


class TestCalculateFeasibilityScore:
    """Tests for calculate_feasibility_score function."""
    
    def test_perfect_score(self):
        """Test perfect feasibility score."""
        score = calculate_feasibility_score(
            total_distance=5.0,
            total_time=240,  # 4 hours
            total_cost=50.0,
            conflicts=[],
            max_walking_km=10.0,
            available_hours=8.0,
            max_budget=100.0
        )
        
        assert score == 100.0
    
    def test_distance_penalty(self):
        """Test penalty for exceeding walking distance."""
        score = calculate_feasibility_score(
            total_distance=15.0,  # 50% over limit
            total_time=240,
            total_cost=50.0,
            conflicts=[],
            max_walking_km=10.0,
            available_hours=8.0,
            max_budget=100.0
        )
        
        # Should have distance penalty
        assert score < 100.0
        assert score >= 70.0  # Penalty capped at 30
    
    def test_time_penalty(self):
        """Test penalty for exceeding available time."""
        score = calculate_feasibility_score(
            total_distance=5.0,
            total_time=600,  # 10 hours (25% over 8 hours)
            total_cost=50.0,
            conflicts=[],
            max_walking_km=10.0,
            available_hours=8.0,
            max_budget=100.0
        )
        
        # Should have time penalty
        assert score < 100.0
        assert score >= 60.0  # Penalty capped at 40
    
    def test_budget_penalty(self):
        """Test penalty for exceeding budget."""
        score = calculate_feasibility_score(
            total_distance=5.0,
            total_time=240,
            total_cost=150.0,  # 50% over budget
            conflicts=[],
            max_walking_km=10.0,
            available_hours=8.0,
            max_budget=100.0
        )
        
        # Should have budget penalty
        assert score < 100.0
        assert score >= 80.0  # Penalty capped at 20
    
    def test_conflict_penalty(self):
        """Test penalty for conflicts."""
        score = calculate_feasibility_score(
            total_distance=5.0,
            total_time=240,
            total_cost=50.0,
            conflicts=["Conflict 1", "Conflict 2"],
            max_walking_km=10.0,
            available_hours=8.0,
            max_budget=100.0
        )
        
        # Should have conflict penalty (10 points per conflict)
        assert score == 80.0
    
    def test_multiple_penalties(self):
        """Test multiple penalties combined."""
        score = calculate_feasibility_score(
            total_distance=15.0,  # Over limit
            total_time=600,  # Over time
            total_cost=150.0,  # Over budget
            conflicts=["Conflict 1"],
            max_walking_km=10.0,
            available_hours=8.0,
            max_budget=100.0
        )
        
        # Should have multiple penalties
        assert score < 70.0
    
    def test_score_never_negative(self):
        """Test that score never goes below 0."""
        score = calculate_feasibility_score(
            total_distance=50.0,  # Way over
            total_time=2000,  # Way over
            total_cost=500.0,  # Way over
            conflicts=["C1", "C2", "C3", "C4", "C5"],
            max_walking_km=5.0,
            available_hours=4.0,
            max_budget=50.0
        )
        
        assert score >= 0.0



class TestSuggestImprovements:
    """Tests for suggest_improvements function."""
    
    def test_distance_suggestions(self):
        """Test suggestions for distance issues."""
        issues = ["Walking distance (15.0km) exceeds limit"]
        route = ["P1", "P2", "P3", "P4", "P5"]
        places = []
        
        suggestions = suggest_improvements(issues, route, places)
        
        assert len(suggestions) > 0
        assert any("reducing stops" in s.lower() for s in suggestions)
    
    def test_time_suggestions(self):
        """Test suggestions for time issues."""
        issues = ["Total time (10.0h) exceeds available time"]
        route = ["P1", "P2", "P3"]
        places = []
        
        suggestions = suggest_improvements(issues, route, places)
        
        assert len(suggestions) > 0
        assert any("multi-day" in s.lower() for s in suggestions)
    
    def test_budget_suggestions(self):
        """Test suggestions for budget issues."""
        issues = ["Cost (€150) exceeds budget"]
        route = ["P1", "P2"]
        places = []
        
        suggestions = suggest_improvements(issues, route, places)
        
        assert len(suggestions) > 0
        assert any("free" in s.lower() or "budget" in s.lower() for s in suggestions)



class TestFeasibilityAgent:
    """Tests for feasibility_agent function."""
    
    def test_agent_calculates_feasibility(self):
        """Test agent calculates feasibility and updates state."""
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            ),
            Place(
                name="Roman Forum",
                place_type="monument",
                coordinates=(41.8925, 12.4853),
                visit_duration=90
            )
        ]
        
        state = PlannerState(
            user_query="Visit Rome",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=8.0,
                max_budget=100.0,
                max_walking_km=10.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={
                "Colosseum": OpeningHours(
                    place_name="Colosseum",
                    is_open_today=True,
                    opening_time=time(9, 0),
                    closing_time=time(19, 0),
                    last_entry_time=time(18, 0),
                    closed_days=[]
                )
            },
            ticket_info={},
            travel_times={
                ("Colosseum", "Roman Forum"): TravelTime(
                    duration_minutes=10.0,
                    distance_km=0.8,
                    mode="pedestrian"
                )
            },
            optimized_route=["Colosseum", "Roman Forum"],
            crowd_predictions={},
            total_cost=50.0,
            feasibility_score=None,
            feasibility_issues=[],
            iteration_count=0,
            max_iterations=3,
            is_feasible=False,
            itinerary=None,
            explanation=""
        )
        
        updated_state = feasibility_agent(state)
        
        # Verify feasibility was calculated
        assert updated_state.feasibility_score is not None
        assert updated_state.feasibility_score >= 0.0
        assert updated_state.feasibility_score <= 100.0
        assert updated_state.is_feasible is not None
    
    def test_agent_flags_infeasible_itinerary(self):
        """Test agent flags infeasible itinerary."""
        places = [
            Place(
                name=f"Place_{i}",
                place_type="monument",
                coordinates=(41.89 + i * 0.1, 12.49 + i * 0.1),
                visit_duration=180
            )
            for i in range(10)
        ]
        
        # Create travel times for all pairs
        travel_times = {}
        for i in range(9):
            travel_times[(f"Place_{i}", f"Place_{i+1}")] = TravelTime(
                duration_minutes=30.0,
                distance_km=3.0,
                mode="pedestrian"
            )
        
        state = PlannerState(
            user_query="Visit many places",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=4.0,  # Only 4 hours
                max_budget=50.0,  # Low budget
                max_walking_km=5.0,  # Low walking limit
                crowd_tolerance="neutral"
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times=travel_times,
            optimized_route=[f"Place_{i}" for i in range(10)],
            crowd_predictions={},
            total_cost=200.0,  # High cost
            feasibility_score=None,
            feasibility_issues=[],
            iteration_count=0,
            max_iterations=3,
            is_feasible=False,
            itinerary=None,
            explanation=""
        )
        
        updated_state = feasibility_agent(state)
        
        # Should be infeasible
        assert updated_state.is_feasible is False
        assert updated_state.feasibility_score < 70.0
        assert len(updated_state.feasibility_issues) > 0
    
    def test_agent_handles_no_route(self):
        """Test agent handles missing optimized route."""
        state = PlannerState(
            user_query="Visit Rome",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=8.0,
                max_budget=100.0,
                max_walking_km=10.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=[],
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={},
            optimized_route=None,  # No route
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
        
        updated_state = feasibility_agent(state)
        
        # Should handle gracefully
        assert updated_state.is_feasible is False
        assert updated_state.feasibility_score == 0.0



# ============================================================================
# Property-Based Tests using Hypothesis
# ============================================================================

class TestFeasibilityProperties:
    """Property-based tests for Feasibility Agent."""
    
    @given(
        total_distance=st.floats(min_value=0.0, max_value=50.0),
        total_time=st.integers(min_value=0, max_value=1440),
        total_cost=st.floats(min_value=0.0, max_value=500.0),
        num_conflicts=st.integers(min_value=0, max_value=10),
        max_walking_km=st.floats(min_value=1.0, max_value=20.0),
        available_hours=st.floats(min_value=1.0, max_value=12.0),
        max_budget=st.floats(min_value=10.0, max_value=500.0)
    )
    @settings(max_examples=100)
    def test_property_score_in_range(
        self, total_distance, total_time, total_cost, num_conflicts,
        max_walking_km, available_hours, max_budget
    ):
        """
        Property Test: Feasibility score is always in [0, 100].
        
        **Validates: Requirements 9.7**
        
        For any itinerary parameters, the feasibility score must be
        between 0 and 100 inclusive.
        """
        conflicts = [f"Conflict_{i}" for i in range(num_conflicts)]
        
        score = calculate_feasibility_score(
            total_distance=total_distance,
            total_time=total_time,
            total_cost=total_cost,
            conflicts=conflicts,
            max_walking_km=max_walking_km,
            available_hours=available_hours,
            max_budget=max_budget
        )
        
        assert 0.0 <= score <= 100.0, (
            f"Feasibility score {score} is out of range [0, 100]"
        )
    
    @given(
        num_places=st.integers(min_value=1, max_value=10),
        distance_per_segment=st.floats(min_value=0.1, max_value=5.0)
    )
    @settings(max_examples=50)
    def test_property_distance_non_negative(self, num_places, distance_per_segment):
        """
        Property Test: Total distance is always non-negative.
        
        **Validates: Requirements 9.1**
        
        For any route, the total walking distance must be >= 0.
        """
        route = [f"Place_{i}" for i in range(num_places)]
        
        travel_times = {}
        for i in range(num_places - 1):
            travel_times[(route[i], route[i+1])] = TravelTime(
                duration_minutes=10.0,
                distance_km=distance_per_segment,
                mode="pedestrian"
            )
        
        distance = calculate_total_distance(route, travel_times)
        
        assert distance >= 0.0, f"Total distance {distance} is negative"
    
    @given(
        num_places=st.integers(min_value=1, max_value=10),
        visit_duration=st.integers(min_value=10, max_value=300)
    )
    @settings(max_examples=50)
    def test_property_time_non_negative(self, num_places, visit_duration):
        """
        Property Test: Total time is always non-negative.
        
        **Validates: Requirements 9.2**
        
        For any route, the total time must be >= 0.
        """
        route = [f"Place_{i}" for i in range(num_places)]
        places = [
            Place(
                name=f"Place_{i}",
                place_type="monument",
                coordinates=(41.89, 12.49),
                visit_duration=visit_duration
            )
            for i in range(num_places)
        ]
        travel_times = {}
        
        total_time = calculate_total_time(route, places, travel_times)
        
        assert total_time >= 0, f"Total time {total_time} is negative"
    
    @given(
        num_places=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_property_feasibility_deterministic(self, num_places):
        """
        Property Test: Feasibility calculation is deterministic.
        
        **Validates: Implementation correctness**
        
        Calculating feasibility for the same itinerary multiple times
        should return identical results.
        """
        route = [f"Place_{i}" for i in range(num_places)]
        places = [
            Place(
                name=f"Place_{i}",
                place_type="monument",
                coordinates=(41.89, 12.49),
                visit_duration=60
            )
            for i in range(num_places)
        ]
        
        travel_times = {}
        for i in range(num_places - 1):
            travel_times[(route[i], route[i+1])] = TravelTime(
                duration_minutes=10.0,
                distance_km=1.0,
                mode="pedestrian"
            )
        
        # Calculate twice
        distance1 = calculate_total_distance(route, travel_times)
        distance2 = calculate_total_distance(route, travel_times)
        
        time1 = calculate_total_time(route, places, travel_times)
        time2 = calculate_total_time(route, places, travel_times)
        
        score1 = calculate_feasibility_score(
            distance1, time1, 50.0, [], 10.0, 8.0, 100.0
        )
        score2 = calculate_feasibility_score(
            distance2, time2, 50.0, [], 10.0, 8.0, 100.0
        )
        
        # Should be identical
        assert distance1 == distance2
        assert time1 == time2
        assert score1 == score2
    
    @given(
        distance_ratio=st.floats(min_value=0.0, max_value=2.0),
        time_ratio=st.floats(min_value=0.0, max_value=2.0),
        cost_ratio=st.floats(min_value=0.0, max_value=2.0)
    )
    @settings(max_examples=100)
    def test_property_score_decreases_with_violations(
        self, distance_ratio, time_ratio, cost_ratio
    ):
        """
        Property Test: Score decreases as constraints are violated.
        
        **Validates: Requirements 9.1, 9.2, 9.4**
        
        As distance, time, or cost exceed their limits, the feasibility
        score should decrease.
        """
        max_walking = 10.0
        available_hours = 8.0
        max_budget = 100.0
        
        # Calculate score with ratios applied
        score = calculate_feasibility_score(
            total_distance=max_walking * distance_ratio,
            total_time=int(available_hours * 60 * time_ratio),
            total_cost=max_budget * cost_ratio,
            conflicts=[],
            max_walking_km=max_walking,
            available_hours=available_hours,
            max_budget=max_budget
        )
        
        # If all ratios <= 1.0, score should be 100
        if distance_ratio <= 1.0 and time_ratio <= 1.0 and cost_ratio <= 1.0:
            assert score == 100.0
        
        # If any ratio > 1.0, score should be < 100
        if distance_ratio > 1.0 or time_ratio > 1.0 or cost_ratio > 1.0:
            assert score < 100.0
    
    @given(
        num_conflicts=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=50)
    def test_property_conflicts_decrease_score(self, num_conflicts):
        """
        Property Test: More conflicts decrease the score.
        
        **Validates: Requirements 9.3**
        
        As the number of conflicts increases, the feasibility score
        should decrease.
        """
        conflicts = [f"Conflict_{i}" for i in range(num_conflicts)]
        
        score = calculate_feasibility_score(
            total_distance=5.0,
            total_time=240,
            total_cost=50.0,
            conflicts=conflicts,
            max_walking_km=10.0,
            available_hours=8.0,
            max_budget=100.0
        )
        
        # Score should decrease by 10 per conflict (but not below 0)
        expected_score = max(0.0, 100.0 - (num_conflicts * 10))
        assert score == expected_score
