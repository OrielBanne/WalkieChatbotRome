"""Unit tests for Planner Agent."""

import pytest
from datetime import datetime, time, timedelta
from src.agents.models import (
    PlannerState,
    UserPreferences,
    Place,
    OpeningHours,
    TicketInfo,
    TravelTime,
    CrowdLevel,
    Itinerary
)
from src.agents.planner import (
    should_iterate,
    reduce_stops,
    remove_expensive_places,
    remove_longest_visits,
    handle_feasibility_issues,
    build_itinerary,
    planner_agent
)


@pytest.fixture
def sample_places():
    """Create sample places for testing."""
    return [
        Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90),
        Place(name="Roman Forum", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60),
        Place(name="Pantheon", place_type="monument", coordinates=(41.8986, 12.4768), visit_duration=30),
        Place(name="Trevi Fountain", place_type="monument", coordinates=(41.9009, 12.4833), visit_duration=20),
        Place(name="Vatican Museums", place_type="museum", coordinates=(41.9065, 12.4536), visit_duration=180),
    ]


@pytest.fixture
def sample_state(sample_places):
    """Create sample planner state."""
    return PlannerState(
        user_query="Show me ancient Rome",
        user_preferences=UserPreferences(
            interests=["history", "art"],
            available_hours=8.0,
            max_budget=100.0,
            max_walking_km=10.0,
            crowd_tolerance="neutral"
        ),
        candidate_places=sample_places,
        optimized_route=["Colosseum", "Roman Forum", "Pantheon", "Trevi Fountain"],
        opening_hours={
            "Colosseum": OpeningHours(
                place_name="Colosseum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            ),
            "Roman Forum": OpeningHours(
                place_name="Roman Forum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                closed_days=[]
            ),
        },
        ticket_info={
            "Colosseum": TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=True,
                price=18.0
            ),
            "Vatican Museums": TicketInfo(
                place_name="Vatican Museums",
                ticket_required=True,
                reservation_required=True,
                price=20.0
            ),
        },
        travel_times={
            ("Colosseum", "Roman Forum"): TravelTime(duration_minutes=5, distance_km=0.3, mode="pedestrian"),
            ("Roman Forum", "Pantheon"): TravelTime(duration_minutes=15, distance_km=1.0, mode="pedestrian"),
            ("Pantheon", "Trevi Fountain"): TravelTime(duration_minutes=10, distance_km=0.6, mode="pedestrian"),
        },
        crowd_predictions={
            "Colosseum": CrowdLevel.HIGH,
            "Vatican Museums": CrowdLevel.VERY_HIGH,
        },
        total_cost=50.0,
        feasibility_score=85.0,
        is_feasible=True
    )


class TestShouldIterate:
    """Tests for should_iterate function."""
    
    def test_should_iterate_when_not_feasible(self):
        """Should iterate when itinerary is not feasible."""
        state = PlannerState(
            user_query="test",
            is_feasible=False,
            iteration_count=0,
            max_iterations=3,
            feasibility_issues=["Distance too long"]
        )
        assert should_iterate(state) is True
    
    def test_should_not_iterate_when_feasible(self):
        """Should not iterate when itinerary is feasible."""
        state = PlannerState(
            user_query="test",
            is_feasible=True,
            iteration_count=0,
            max_iterations=3
        )
        assert should_iterate(state) is False
    
    def test_should_not_iterate_when_max_reached(self):
        """Should not iterate when max iterations reached."""
        state = PlannerState(
            user_query="test",
            is_feasible=False,
            iteration_count=3,
            max_iterations=3,
            feasibility_issues=["Distance too long"]
        )
        assert should_iterate(state) is False
    
    def test_should_not_iterate_when_no_issues(self):
        """Should not iterate when no issues to fix."""
        state = PlannerState(
            user_query="test",
            is_feasible=False,
            iteration_count=0,
            max_iterations=3,
            feasibility_issues=[]
        )
        assert should_iterate(state) is False


class TestReduceStops:
    """Tests for reduce_stops function."""
    
    def test_reduces_number_of_places(self, sample_places):
        """Should reduce number of places."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places
        )
        
        result = reduce_stops(state)
        
        assert len(result.selected_places) < len(sample_places)
        assert len(result.selected_places) >= 2  # Minimum 2 places
    
    def test_adds_explanation(self, sample_places):
        """Should add explanation to state."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places
        )
        
        result = reduce_stops(state)
        
        assert "Reduced stops" in result.explanation
        assert str(len(sample_places)) in result.explanation
    
    def test_respects_minimum_places(self):
        """Should not reduce below 2 places."""
        places = [
            Place(name="Place 1", coordinates=(41.9, 12.5), visit_duration=60),
            Place(name="Place 2", coordinates=(41.9, 12.5), visit_duration=60),
        ]
        state = PlannerState(
            user_query="test",
            candidate_places=places
        )
        
        result = reduce_stops(state)
        
        assert len(result.selected_places) == 2


class TestRemoveExpensivePlaces:
    """Tests for remove_expensive_places function."""
    
    def test_removes_expensive_places(self, sample_places):
        """Should remove expensive places."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places,
            ticket_info={
                "Colosseum": TicketInfo(place_name="Colosseum", ticket_required=True, reservation_required=False, price=18.0),
                "Vatican Museums": TicketInfo(place_name="Vatican Museums", ticket_required=True, reservation_required=False, price=20.0),
                "Pantheon": TicketInfo(place_name="Pantheon", ticket_required=False, reservation_required=False, price=0.0),
            }
        )
        
        result = remove_expensive_places(state)
        
        # Should keep cheaper places
        assert len(result.selected_places) < len(sample_places)
        # Pantheon (free) should be kept
        assert any(p.name == "Pantheon" for p in result.selected_places)
    
    def test_adds_explanation(self, sample_places):
        """Should add explanation about budget."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places,
            ticket_info={}
        )
        
        result = remove_expensive_places(state)
        
        assert "budget" in result.explanation.lower()


class TestRemoveLongestVisits:
    """Tests for remove_longest_visits function."""
    
    def test_removes_longest_visits(self):
        """Should remove places with longest visit durations."""
        places = [
            Place(name="Quick Visit", coordinates=(41.9, 12.5), visit_duration=20),
            Place(name="Medium Visit", coordinates=(41.9, 12.5), visit_duration=60),
            Place(name="Long Visit", coordinates=(41.9, 12.5), visit_duration=180),
        ]
        state = PlannerState(
            user_query="test",
            candidate_places=places
        )
        
        result = remove_longest_visits(state)
        
        # Should keep shorter visits
        assert len(result.selected_places) < len(places)
        assert all(p.visit_duration <= 60 for p in result.selected_places)
    
    def test_adds_explanation(self, sample_places):
        """Should add explanation about time."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places
        )
        
        result = remove_longest_visits(state)
        
        assert "time" in result.explanation.lower()


class TestHandleFeasibilityIssues:
    """Tests for handle_feasibility_issues function."""
    
    def test_handles_distance_issues(self, sample_places):
        """Should handle distance feasibility issues."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places,
            feasibility_issues=["Walking distance (15.0km) exceeds limit"],
            iteration_count=0
        )
        
        result = handle_feasibility_issues(state)
        
        assert result.iteration_count == 1
        assert len(result.selected_places) < len(sample_places)
        assert len(result.feasibility_issues) == 0  # Cleared for re-evaluation
    
    def test_handles_time_issues(self, sample_places):
        """Should handle time feasibility issues."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places,
            feasibility_issues=["Total time exceeds available time"],
            iteration_count=0
        )
        
        result = handle_feasibility_issues(state)
        
        assert result.iteration_count == 1
        assert len(result.selected_places) < len(sample_places)
    
    def test_handles_budget_issues(self, sample_places):
        """Should handle budget feasibility issues."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places,
            ticket_info={
                "Colosseum": TicketInfo(place_name="Colosseum", ticket_required=True, reservation_required=False, price=50.0),
                "Pantheon": TicketInfo(place_name="Pantheon", ticket_required=False, reservation_required=False, price=0.0),
            },
            feasibility_issues=["Cost exceeds budget"],
            iteration_count=0
        )
        
        result = handle_feasibility_issues(state)
        
        assert result.iteration_count == 1
        # Should prefer cheaper places
        assert "Colosseum" not in [p.name for p in result.selected_places]
    
    def test_handles_opening_hours_issues(self, sample_places):
        """Should handle opening hours issues."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places,
            opening_hours={
                "Colosseum": OpeningHours(
                    place_name="Colosseum",
                    is_open_today=False,
                    closed_days=["Monday"]
                ),
                "Pantheon": OpeningHours(
                    place_name="Pantheon",
                    is_open_today=True,
                    opening_time=time(9, 0),
                    closing_time=time(19, 0),
                    closed_days=[]
                ),
            },
            feasibility_issues=["Colosseum is closed today"],
            iteration_count=0
        )
        
        result = handle_feasibility_issues(state)
        
        assert result.iteration_count == 1
        # Should remove closed places
        assert "Colosseum" not in [p.name for p in result.selected_places]
    
    def test_increments_iteration_count(self, sample_places):
        """Should increment iteration count."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places,
            feasibility_issues=["Some issue"],
            iteration_count=0
        )
        
        result = handle_feasibility_issues(state)
        
        assert result.iteration_count == 1
    
    def test_clears_feasibility_issues(self, sample_places):
        """Should clear feasibility issues for re-evaluation."""
        state = PlannerState(
            user_query="test",
            candidate_places=sample_places,
            feasibility_issues=["Issue 1", "Issue 2"],
            iteration_count=0
        )
        
        result = handle_feasibility_issues(state)
        
        assert len(result.feasibility_issues) == 0


class TestBuildItinerary:
    """Tests for build_itinerary function."""
    
    def test_builds_itinerary_with_stops(self, sample_state):
        """Should build itinerary with all stops."""
        itinerary = build_itinerary(sample_state)
        
        assert isinstance(itinerary, Itinerary)
        assert len(itinerary.stops) == len(sample_state.optimized_route)
    
    def test_includes_opening_hours_in_notes(self, sample_state):
        """Should include opening hours in stop notes."""
        itinerary = build_itinerary(sample_state)
        
        # Find Colosseum stop
        colosseum_stop = next(s for s in itinerary.stops if s.place.name == "Colosseum")
        
        # Should have opening hours note
        assert any("Open:" in note for note in colosseum_stop.notes)
    
    def test_includes_crowd_warnings(self, sample_state):
        """Should include crowd warnings in notes."""
        itinerary = build_itinerary(sample_state)
        
        # Find Colosseum stop (has HIGH crowd level)
        colosseum_stop = next(s for s in itinerary.stops if s.place.name == "Colosseum")
        
        # Should have crowd warning
        assert any("crowd" in note.lower() for note in colosseum_stop.notes)
    
    def test_includes_ticket_warnings(self, sample_state):
        """Should include ticket warnings for places requiring booking."""
        itinerary = build_itinerary(sample_state)
        
        # Find Colosseum stop (requires reservation)
        colosseum_stop = next(s for s in itinerary.stops if s.place.name == "Colosseum")
        
        # Should have booking warning
        assert any("booking" in note.lower() for note in colosseum_stop.notes)
    
    def test_includes_travel_times(self, sample_state):
        """Should include travel times to next stop."""
        itinerary = build_itinerary(sample_state)
        
        # First stop should have travel time to next
        first_stop = itinerary.stops[0]
        assert any("Next:" in note for note in first_stop.notes)
    
    def test_calculates_total_duration(self, sample_state):
        """Should calculate total duration correctly."""
        itinerary = build_itinerary(sample_state)
        
        assert itinerary.total_duration_minutes > 0
        # Should include visit times and travel times
        expected_min = sum(
            next(p for p in sample_state.candidate_places if p.name == name).visit_duration
            for name in sample_state.optimized_route
        )
        assert itinerary.total_duration_minutes >= expected_min
    
    def test_calculates_total_distance(self, sample_state):
        """Should calculate total distance correctly."""
        itinerary = build_itinerary(sample_state)
        
        assert itinerary.total_distance_km > 0
        # Should sum all travel distances
        expected_distance = sum(
            travel.distance_km for travel in sample_state.travel_times.values()
        )
        assert abs(itinerary.total_distance_km - expected_distance) < 0.1
    
    def test_handles_lunch_break(self, sample_state):
        """Should handle LUNCH_BREAK in route."""
        sample_state.optimized_route = ["Colosseum", "LUNCH_BREAK", "Pantheon"]
        
        itinerary = build_itinerary(sample_state)
        
        # Should have lunch break stop
        assert any(stop.place.name == "Lunch Break" for stop in itinerary.stops)
        lunch_stop = next(s for s in itinerary.stops if s.place.name == "Lunch Break")
        assert lunch_stop.duration_minutes == 60
    
    def test_uses_start_time_from_preferences(self, sample_state):
        """Should use start time from user preferences."""
        sample_state.user_preferences.start_time = time(10, 0)
        
        itinerary = build_itinerary(sample_state)
        
        # First stop should be at 10:00
        assert itinerary.stops[0].time.hour == 10
        assert itinerary.stops[0].time.minute == 0
    
    def test_chronological_order(self, sample_state):
        """Should create stops in chronological order."""
        itinerary = build_itinerary(sample_state)
        
        # Each stop should be after the previous one
        for i in range(len(itinerary.stops) - 1):
            assert itinerary.stops[i + 1].time > itinerary.stops[i].time


class TestPlannerAgent:
    """Tests for planner_agent function."""
    
    def test_generates_itinerary_when_feasible(self, sample_state):
        """Should generate final itinerary when feasible."""
        result = planner_agent(sample_state)
        
        assert result.itinerary is not None
        assert isinstance(result.itinerary, Itinerary)
    
    def test_iterates_when_not_feasible(self, sample_state):
        """Should iterate when not feasible."""
        sample_state.is_feasible = False
        sample_state.feasibility_issues = ["Distance too long"]
        sample_state.iteration_count = 0
        
        result = planner_agent(sample_state)
        
        # Should have attempted to fix issues
        assert result.iteration_count == 1
        assert result.itinerary is None  # Not generated yet
    
    def test_stops_at_max_iterations(self, sample_state):
        """Should stop iterating at max iterations."""
        sample_state.is_feasible = False
        sample_state.feasibility_issues = ["Distance too long"]
        sample_state.iteration_count = 3
        sample_state.max_iterations = 3
        
        result = planner_agent(sample_state)
        
        # Should generate itinerary even if not feasible
        assert result.itinerary is not None
    
    def test_adds_feasibility_summary(self, sample_state):
        """Should add feasibility summary to explanation."""
        result = planner_agent(sample_state)
        
        assert "feasible" in result.explanation.lower()
        assert str(int(sample_state.feasibility_score)) in result.explanation
    
    def test_handles_missing_route(self, sample_state):
        """Should handle missing optimized route."""
        sample_state.optimized_route = []
        
        result = planner_agent(sample_state)
        
        assert "Could not generate" in result.explanation
    
    def test_lists_remaining_issues_when_not_feasible(self, sample_state):
        """Should list remaining issues when not feasible."""
        sample_state.is_feasible = False
        sample_state.feasibility_issues = ["Issue 1", "Issue 2", "Issue 3"]
        sample_state.iteration_count = 3
        sample_state.max_iterations = 3
        
        result = planner_agent(sample_state)
        
        assert "Remaining issues" in result.explanation
        # Should list at least some issues
        assert any(issue in result.explanation for issue in sample_state.feasibility_issues)


class TestIntegration:
    """Integration tests for planner agent."""
    
    def test_full_iteration_cycle(self, sample_places):
        """Test full iteration cycle from infeasible to feasible."""
        state = PlannerState(
            user_query="test",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=2.0,  # Very limited time
                max_budget=50.0,
                max_walking_km=5.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=sample_places,
            optimized_route=[p.name for p in sample_places],  # All 5 places
            is_feasible=False,
            feasibility_issues=["Total time exceeds available time"],
            iteration_count=0,
            max_iterations=3,
            opening_hours={},
            ticket_info={},
            travel_times={},
            crowd_predictions={},
            total_cost=30.0,
            feasibility_score=40.0
        )
        
        # First iteration - should reduce stops
        result = planner_agent(state)
        assert result.iteration_count == 1
        assert len(result.selected_places) < len(sample_places)
        
        # Simulate re-optimization making it feasible
        result.is_feasible = True
        result.feasibility_score = 85.0
        result.optimized_route = [p.name for p in result.selected_places]
        
        # Second call - should generate itinerary
        final = planner_agent(result)
        assert final.itinerary is not None
    
    def test_handles_multiple_constraint_types(self, sample_places):
        """Test handling multiple types of constraints."""
        state = PlannerState(
            user_query="test",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=8.0,
                max_budget=20.0,  # Low budget
                max_walking_km=15.0,  # Long distance
                crowd_tolerance="avoid"
            ),
            candidate_places=sample_places,
            optimized_route=[p.name for p in sample_places],
            is_feasible=False,
            feasibility_issues=["Cost exceeds budget", "Walking distance too long"],
            iteration_count=0,
            max_iterations=3,
            opening_hours={},
            ticket_info={
                "Vatican Museums": TicketInfo(
                    place_name="Vatican Museums",
                    ticket_required=True,
                    reservation_required=True,
                    price=20.0
                ),
            },
            travel_times={},
            crowd_predictions={},
            total_cost=50.0,
            feasibility_score=30.0
        )
        
        # Should handle budget issue first
        result = planner_agent(state)
        assert result.iteration_count == 1
        # Should have removed expensive places
        assert "Vatican Museums" not in [p.name for p in result.selected_places]
