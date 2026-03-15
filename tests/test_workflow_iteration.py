"""Tests for workflow iteration logic."""

import pytest
from datetime import time
from hypothesis import given, strategies as st, settings
from src.agents.models import PlannerState, UserPreferences, Place, TravelTime, TicketInfo
from src.agents.planner import should_iterate, handle_feasibility_issues, reduce_stops
from src.agents.workflow import create_planner_workflow


def test_should_iterate_when_not_feasible():
    """Test that iteration continues when itinerary is not feasible."""
    state = PlannerState(
        user_query="test",
        is_feasible=False,
        iteration_count=0,
        max_iterations=3,
        feasibility_issues=["Distance too long"]
    )
    
    assert should_iterate(state) is True


def test_should_not_iterate_when_feasible():
    """Test that iteration stops when itinerary is feasible."""
    state = PlannerState(
        user_query="test",
        is_feasible=True,
        iteration_count=0,
        max_iterations=3
    )
    
    assert should_iterate(state) is False


def test_should_not_iterate_when_max_reached():
    """Test that iteration stops when max iterations reached."""
    state = PlannerState(
        user_query="test",
        is_feasible=False,
        iteration_count=3,
        max_iterations=3,
        feasibility_issues=["Distance too long"]
    )
    
    assert should_iterate(state) is False


def test_should_not_iterate_when_no_issues():
    """Test that iteration stops when no issues to fix."""
    state = PlannerState(
        user_query="test",
        is_feasible=False,
        iteration_count=0,
        max_iterations=3,
        feasibility_issues=[]
    )
    
    assert should_iterate(state) is False


def test_reduce_stops():
    """Test that reduce_stops decreases number of places."""
    places = [
        Place(name=f"Place {i}", coordinates=(41.9, 12.5), visit_duration=60)
        for i in range(5)
    ]
    
    state = PlannerState(
        user_query="test",
        candidate_places=places
    )
    
    result = reduce_stops(state)
    
    assert len(result.selected_places) < len(places)
    assert len(result.selected_places) >= 2  # Minimum 2 places
    assert "Reduced stops" in result.explanation


def test_handle_distance_issues():
    """Test handling of distance feasibility issues."""
    places = [
        Place(name=f"Place {i}", coordinates=(41.9, 12.5), visit_duration=60)
        for i in range(5)
    ]
    
    state = PlannerState(
        user_query="test",
        candidate_places=places,
        feasibility_issues=["Walking distance (15.0km) exceeds limit (10.0km)"],
        iteration_count=0
    )
    
    result = handle_feasibility_issues(state)
    
    assert result.iteration_count == 1
    assert len(result.selected_places) < len(places)
    assert len(result.feasibility_issues) == 0  # Issues cleared for re-evaluation


def test_handle_time_issues():
    """Test handling of time feasibility issues."""
    places = [
        Place(name="Place 1", coordinates=(41.9, 12.5), visit_duration=120),
        Place(name="Place 2", coordinates=(41.9, 12.5), visit_duration=180),
        Place(name="Place 3", coordinates=(41.9, 12.5), visit_duration=60),
        Place(name="Place 4", coordinates=(41.9, 12.5), visit_duration=90),
    ]
    
    state = PlannerState(
        user_query="test",
        candidate_places=places,
        feasibility_issues=["Total time (8.0h) exceeds available time (6.0h)"],
        iteration_count=0
    )
    
    result = handle_feasibility_issues(state)
    
    assert result.iteration_count == 1
    assert len(result.selected_places) < len(places)
    # Should keep shorter visits
    assert all(p.visit_duration <= 120 for p in result.selected_places)


def test_handle_budget_issues():
    """Test handling of budget feasibility issues."""
    from src.agents.models import TicketInfo
    
    places = [
        Place(name="Expensive Place", coordinates=(41.9, 12.5), visit_duration=60),
        Place(name="Cheap Place", coordinates=(41.9, 12.5), visit_duration=60),
        Place(name="Free Place", coordinates=(41.9, 12.5), visit_duration=60),
    ]
    
    state = PlannerState(
        user_query="test",
        candidate_places=places,
        ticket_info={
            "Expensive Place": TicketInfo(place_name="Expensive Place", ticket_required=True, reservation_required=False, price=50.0),
            "Cheap Place": TicketInfo(place_name="Cheap Place", ticket_required=True, reservation_required=False, price=10.0),
            "Free Place": TicketInfo(place_name="Free Place", ticket_required=False, reservation_required=False, price=0.0),
        },
        feasibility_issues=["Cost (€60) exceeds budget (€30)"],
        iteration_count=0
    )
    
    result = handle_feasibility_issues(state)
    
    assert result.iteration_count == 1
    # Should prefer cheaper places
    assert "Expensive Place" not in [p.name for p in result.selected_places]


def test_iteration_count_increments():
    """Test that iteration count increments correctly."""
    state = PlannerState(
        user_query="test",
        candidate_places=[
            Place(name="Place 1", coordinates=(41.9, 12.5), visit_duration=60),
            Place(name="Place 2", coordinates=(41.9, 12.5), visit_duration=60),
        ],
        feasibility_issues=["Some issue"],
        iteration_count=0,
        max_iterations=3
    )
    
    result = handle_feasibility_issues(state)
    assert result.iteration_count == 1
    
    result.feasibility_issues = ["Another issue"]
    result = handle_feasibility_issues(result)
    assert result.iteration_count == 2


def test_workflow_creation():
    """Test that workflow can be created without errors."""
    workflow = create_planner_workflow()
    assert workflow is not None


def test_workflow_has_all_nodes():
    """Test that workflow contains all expected agent nodes."""
    workflow = create_planner_workflow()
    
    # Get the graph structure
    graph = workflow.get_graph()
    nodes = list(graph.nodes.keys())
    
    expected_nodes = [
        "place_discovery",
        "opening_hours",
        "tickets",
        "travel_time",
        "route_optimization",
        "crowd_prediction",
        "cost_calculation",
        "feasibility_check",
        "planner"
    ]
    
    for node in expected_nodes:
        assert node in nodes, f"Node {node} not found in workflow"


@pytest.mark.parametrize("iteration_count,max_iterations,expected", [
    (0, 3, True),
    (1, 3, True),
    (2, 3, True),
    (3, 3, False),
])
def test_iteration_limits(iteration_count, max_iterations, expected):
    """Test iteration limits with various counts."""
    state = PlannerState(
        user_query="test",
        is_feasible=False,
        iteration_count=iteration_count,
        max_iterations=max_iterations,
        feasibility_issues=["Some issue"]
    )
    
    assert should_iterate(state) is expected



# ============================================================================
# Integration Tests for Iteration Logic
# ============================================================================


def test_infeasible_itinerary_triggers_iteration():
    """Test that an infeasible itinerary triggers iteration logic."""
    # Create an infeasible itinerary with too many places
    places = [
        Place(name=f"Place {i}", coordinates=(41.9 + i*0.01, 12.5 + i*0.01), visit_duration=120)
        for i in range(10)
    ]
    
    # Create travel times that make it infeasible
    travel_times = {}
    for i in range(len(places) - 1):
        key = (places[i].name, places[i+1].name)
        travel_times[key] = TravelTime(
            duration_minutes=30.0,
            distance_km=2.5,
            mode="pedestrian"
        )
    
    state = PlannerState(
        user_query="Show me all the major attractions",
        candidate_places=places,
        travel_times=travel_times,
        user_preferences=UserPreferences(
            interests=["art", "history"],
            available_hours=6.0,
            max_budget=100.0,
            max_walking_km=8.0,
            crowd_tolerance="neutral"
        ),
        is_feasible=False,
        feasibility_issues=["Walking distance (22.5km) exceeds limit (8.0km)", "Total time (30.0h) exceeds available time (6.0h)"],
        iteration_count=0,
        max_iterations=3
    )
    
    # Should trigger iteration
    assert should_iterate(state) is True
    
    # Handle issues
    result = handle_feasibility_issues(state)
    
    # Should have reduced stops
    assert len(result.selected_places) < len(places)
    assert result.iteration_count == 1
    assert len(result.feasibility_issues) == 0  # Cleared for re-evaluation


def test_iteration_reduces_stops_progressively():
    """Test that multiple iterations progressively reduce stops."""
    places = [
        Place(name=f"Place {i}", coordinates=(41.9, 12.5), visit_duration=60)
        for i in range(8)
    ]
    
    state = PlannerState(
        user_query="test",
        candidate_places=places,
        is_feasible=False,
        feasibility_issues=["Distance too long"],
        iteration_count=0,
        max_iterations=3
    )
    
    # First iteration
    result1 = handle_feasibility_issues(state)
    count1 = len(result1.selected_places)
    assert count1 < len(places)
    assert result1.iteration_count == 1
    
    # Second iteration
    result1.is_feasible = False
    result1.feasibility_issues = ["Distance still too long"]
    result2 = handle_feasibility_issues(result1)
    count2 = len(result2.selected_places)
    assert count2 < count1
    assert result2.iteration_count == 2
    
    # Third iteration
    result2.is_feasible = False
    result2.feasibility_issues = ["Distance still too long"]
    result3 = handle_feasibility_issues(result2)
    count3 = len(result3.selected_places)
    assert count3 <= count2
    assert result3.iteration_count == 3


def test_convergence_to_feasible_solution():
    """Test that iteration converges to a feasible solution."""
    places = [
        Place(name=f"Place {i}", coordinates=(41.9, 12.5), visit_duration=60)
        for i in range(6)
    ]
    
    state = PlannerState(
        user_query="test",
        candidate_places=places,
        user_preferences=UserPreferences(
            interests=["art"],
            available_hours=8.0,
            max_budget=100.0,
            max_walking_km=10.0,
            crowd_tolerance="neutral"
        ),
        is_feasible=False,
        feasibility_issues=["Too many stops"],
        iteration_count=0,
        max_iterations=3
    )
    
    # Simulate iterations
    current_state = state
    iterations = 0
    
    while should_iterate(current_state) and iterations < 5:
        current_state = handle_feasibility_issues(current_state)
        iterations += 1
        
        # Simulate feasibility check - becomes feasible when we have 3 or fewer places
        if len(current_state.selected_places) <= 3:
            current_state.is_feasible = True
            current_state.feasibility_issues = []
            break
        else:
            current_state.is_feasible = False
            current_state.feasibility_issues = ["Still too many stops"]
    
    # Should converge to feasible solution
    assert current_state.is_feasible or current_state.iteration_count >= current_state.max_iterations
    assert len(current_state.selected_places) <= 3 or current_state.iteration_count >= current_state.max_iterations


def test_max_iterations_prevents_infinite_loop():
    """Test that max iterations prevents infinite iteration loops."""
    places = [
        Place(name=f"Place {i}", coordinates=(41.9, 12.5), visit_duration=60)
        for i in range(10)
    ]
    
    state = PlannerState(
        user_query="test",
        candidate_places=places,
        is_feasible=False,
        feasibility_issues=["Unsolvable issue"],
        iteration_count=0,
        max_iterations=3
    )
    
    # Simulate iterations that never become feasible
    current_state = state
    iterations = 0
    
    while should_iterate(current_state) and iterations < 10:  # Extra safety limit
        current_state = handle_feasibility_issues(current_state)
        iterations += 1
        # Keep it infeasible
        current_state.is_feasible = False
        current_state.feasibility_issues = ["Still infeasible"]
    
    # Should stop at max_iterations
    assert current_state.iteration_count == 3
    assert iterations == 3
    assert should_iterate(current_state) is False


# ============================================================================
# Property-Based Tests using Hypothesis
# ============================================================================


class TestIterationProperties:
    """Property-based tests for iteration logic."""
    
    @given(
        num_places=st.integers(min_value=2, max_value=20),
        max_iterations=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50)
    def test_property_iterations_never_exceed_max(self, num_places, max_iterations):
        """
        **Validates: Requirements 10.3**
        
        Property: The iteration count should never exceed max_iterations.
        This property is enforced by the PlannerState model validation.
        """
        places = [
            Place(name=f"Place {i}", coordinates=(41.9, 12.5), visit_duration=60)
            for i in range(num_places)
        ]
        
        state = PlannerState(
            user_query="test",
            candidate_places=places,
            is_feasible=False,
            feasibility_issues=["Some issue"],
            iteration_count=0,
            max_iterations=max_iterations
        )
        
        # Simulate iterations
        current_state = state
        iterations_performed = 0
        
        while should_iterate(current_state) and iterations_performed < 20:  # Safety limit
            current_state = handle_feasibility_issues(current_state)
            iterations_performed += 1
            # Keep it infeasible to test max iterations
            current_state.is_feasible = False
            current_state.feasibility_issues = ["Still infeasible"]
        
        # Property: iteration count should never exceed max_iterations
        assert current_state.iteration_count <= max_iterations, \
            f"Iteration count {current_state.iteration_count} exceeded max {max_iterations}"
    
    @given(
        num_places=st.integers(min_value=3, max_value=15),
        max_iterations=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50)
    def test_property_iteration_reduces_places(self, num_places, max_iterations):
        """
        **Validates: Requirements 10.3**
        
        Property: Each iteration should reduce the number of selected places.
        """
        places = [
            Place(name=f"Place {i}", coordinates=(41.9, 12.5), visit_duration=60)
            for i in range(num_places)
        ]
        
        state = PlannerState(
            user_query="test",
            candidate_places=places,
            is_feasible=False,
            feasibility_issues=["Distance too long"],
            iteration_count=0,
            max_iterations=max_iterations
        )
        
        # First iteration
        result = handle_feasibility_issues(state)
        
        # Property: should have fewer places after iteration
        if result.selected_places:
            assert len(result.selected_places) < len(places), \
                "Iteration should reduce number of places"
            # Should keep at least 2 places
            assert len(result.selected_places) >= 2, \
                "Should keep at least 2 places"
    
    @given(
        num_places=st.integers(min_value=2, max_value=10),
        is_feasible=st.booleans(),
        has_issues=st.booleans()
    )
    @settings(max_examples=50)
    def test_property_should_iterate_logic(self, num_places, is_feasible, has_issues):
        """
        **Validates: Requirements 10.3**
        
        Property: should_iterate returns True only when:
        - Not feasible AND
        - Has issues to fix AND
        - Below max iterations
        """
        places = [
            Place(name=f"Place {i}", coordinates=(41.9, 12.5), visit_duration=60)
            for i in range(num_places)
        ]
        
        issues = ["Some issue"] if has_issues else []
        
        state = PlannerState(
            user_query="test",
            candidate_places=places,
            is_feasible=is_feasible,
            feasibility_issues=issues,
            iteration_count=0,
            max_iterations=3
        )
        
        result = should_iterate(state)
        
        # Property: should iterate only when not feasible, has issues, and below max
        expected = (not is_feasible) and has_issues and (state.iteration_count < state.max_iterations)
        assert result == expected, \
            f"should_iterate returned {result}, expected {expected} " \
            f"(feasible={is_feasible}, has_issues={has_issues}, count={state.iteration_count})"
