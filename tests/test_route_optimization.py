"""Unit and property tests for Route Optimization Agent."""

import pytest
import numpy as np
from datetime import time, datetime, timedelta
from typing import List, Dict, Tuple

from src.agents.route_optimization import (
    build_distance_matrix,
    solve_tsp_greedy,
    check_opening_hours_feasibility,
    add_meal_breaks,
    optimize_route,
    route_optimization_agent
)
from src.agents.models import (
    Place,
    TravelTime,
    OpeningHours,
    PlannerState,
    UserPreferences
)


# ============================================================================
# Unit Tests
# ============================================================================

class TestBuildDistanceMatrix:
    """Test distance matrix construction."""
    
    def test_single_place(self):
        """Test matrix with single place."""
        places = [Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90)]
        travel_times = {}
        
        matrix = build_distance_matrix(places, travel_times)
        
        assert matrix.shape == (1, 1)
        assert matrix[0][0] == 0
    
    def test_two_places(self):
        """Test matrix with two places."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90),
            Place(name="Forum", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60)
        ]
        travel_times = {
            ("Colosseum", "Forum"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian"),
            ("Forum", "Colosseum"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian")
        }
        
        matrix = build_distance_matrix(places, travel_times)
        
        assert matrix.shape == (2, 2)
        assert matrix[0][0] == 0
        assert matrix[1][1] == 0
        assert matrix[0][1] == 10
        assert matrix[1][0] == 10
    
    def test_missing_travel_time(self):
        """Test matrix with missing travel time uses large value."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90),
            Place(name="Forum", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60)
        ]
        travel_times = {}  # No travel times
        
        matrix = build_distance_matrix(places, travel_times)
        
        assert matrix[0][1] == 999
        assert matrix[1][0] == 999


class TestSolveTspGreedy:
    """Test greedy TSP solver."""
    
    def test_single_city(self):
        """Test TSP with single city."""
        matrix = np.array([[0]])
        route = solve_tsp_greedy(matrix)
        assert route == [0]
    
    def test_two_cities(self):
        """Test TSP with two cities."""
        matrix = np.array([
            [0, 10],
            [10, 0]
        ])
        route = solve_tsp_greedy(matrix)
        assert route == [0, 1]
    
    def test_three_cities_simple(self):
        """Test TSP with three cities in obvious order."""
        matrix = np.array([
            [0, 1, 10],
            [1, 0, 1],
            [10, 1, 0]
        ])
        route = solve_tsp_greedy(matrix)
        # Should go 0 -> 1 -> 2 (nearest neighbor)
        assert route == [0, 1, 2]
    
    def test_different_start_index(self):
        """Test TSP starting from different city."""
        matrix = np.array([
            [0, 10, 20],
            [10, 0, 5],
            [20, 5, 0]
        ])
        route = solve_tsp_greedy(matrix, start_index=1)
        assert route[0] == 1
        assert len(route) == 3
        assert len(set(route)) == 3  # All cities visited


class TestCheckOpeningHoursFeasibility:
    """Test opening hours constraint checking."""
    
    def test_all_open(self):
        """Test route where all places are open."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=60),
            Place(name="Forum", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60)
        ]
        route = ["Colosseum", "Forum"]
        opening_hours = {
            "Colosseum": OpeningHours(
                place_name="Colosseum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            ),
            "Forum": OpeningHours(
                place_name="Forum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            )
        }
        travel_times = {
            ("Colosseum", "Forum"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian")
        }
        
        is_feasible, issues = check_opening_hours_feasibility(
            route, places, opening_hours, travel_times, start_time=time(10, 0)
        )
        
        assert is_feasible
        assert len(issues) == 0
    
    def test_place_closed(self):
        """Test route with closed place."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=60)
        ]
        route = ["Colosseum"]
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
        
        is_feasible, issues = check_opening_hours_feasibility(
            route, places, opening_hours, travel_times
        )
        
        assert not is_feasible
        assert len(issues) == 1
        assert "closed today" in issues[0]
    
    def test_arrive_before_opening(self):
        """Test arriving before opening time."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=60)
        ]
        route = ["Colosseum"]
        opening_hours = {
            "Colosseum": OpeningHours(
                place_name="Colosseum",
                is_open_today=True,
                opening_time=time(10, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            )
        }
        travel_times = {}
        
        is_feasible, issues = check_opening_hours_feasibility(
            route, places, opening_hours, travel_times, start_time=time(8, 0)
        )
        
        assert not is_feasible
        assert len(issues) == 1
        assert "before opening" in issues[0]
    
    def test_arrive_after_last_entry(self):
        """Test arriving after last entry time."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=60)
        ]
        route = ["Colosseum"]
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
        
        is_feasible, issues = check_opening_hours_feasibility(
            route, places, opening_hours, travel_times, start_time=time(18, 30)
        )
        
        assert not is_feasible
        assert len(issues) == 1
        assert "after last entry" in issues[0]


class TestAddMealBreaks:
    """Test meal break insertion."""
    
    def test_no_lunch_needed(self):
        """Test route that finishes before lunch time."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=60)
        ]
        route = ["Colosseum"]
        travel_times = {}
        
        result = add_meal_breaks(route, places, travel_times, start_time=time(9, 0))
        
        assert result == ["Colosseum"]
        assert "LUNCH_BREAK" not in result
    
    def test_lunch_added(self):
        """Test lunch break is added during lunch window."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=120),
            Place(name="Forum", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60)
        ]
        route = ["Colosseum", "Forum"]
        travel_times = {
            ("Colosseum", "Forum"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian")
        }
        
        result = add_meal_breaks(route, places, travel_times, start_time=time(11, 0))
        
        assert "LUNCH_BREAK" in result
        # Lunch should be added before Forum (after 12:30)
        assert result.index("LUNCH_BREAK") < result.index("Forum")
    
    def test_lunch_only_added_once(self):
        """Test lunch break is only added once."""
        places = [
            Place(name="Place1", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=60),
            Place(name="Place2", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60),
            Place(name="Place3", place_type="monument", coordinates=(41.8950, 12.4800), visit_duration=60)
        ]
        route = ["Place1", "Place2", "Place3"]
        travel_times = {
            ("Place1", "Place2"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian"),
            ("Place2", "Place3"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian")
        }
        
        result = add_meal_breaks(route, places, travel_times, start_time=time(11, 0))
        
        lunch_count = result.count("LUNCH_BREAK")
        assert lunch_count == 1


class TestOptimizeRoute:
    """Test route optimization function."""
    
    def test_single_place(self):
        """Test optimization with single place."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90)
        ]
        travel_times = {}
        
        result = optimize_route(places, travel_times)
        
        assert result == ["Colosseum"]
    
    def test_two_places(self):
        """Test optimization with two places."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90),
            Place(name="Forum", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60)
        ]
        travel_times = {
            ("Colosseum", "Forum"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian"),
            ("Forum", "Colosseum"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian")
        }
        
        result = optimize_route(places, travel_times)
        
        assert len(result) == 2
        assert "Colosseum" in result
        assert "Forum" in result


class TestRouteOptimizationAgent:
    """Test the route optimization agent function."""
    
    def test_empty_places(self):
        """Test agent with no places."""
        state = PlannerState(
            user_query="test",
            user_preferences=UserPreferences(
                interests=["art"],
                available_hours=8,
                max_budget=100,
                max_walking_km=10,
                crowd_tolerance="neutral"
            ),
            candidate_places=[],
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={}
        )
        
        result = route_optimization_agent(state)
        
        assert result.optimized_route == []
    
    def test_single_place(self):
        """Test agent with single place."""
        state = PlannerState(
            user_query="test",
            user_preferences=UserPreferences(
                interests=["art"],
                available_hours=8,
                max_budget=100,
                max_walking_km=10,
                crowd_tolerance="neutral"
            ),
            candidate_places=[
                Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90)
            ],
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={}
        )
        
        result = route_optimization_agent(state)
        
        assert result.optimized_route == ["Colosseum"]
    
    def test_multiple_places(self):
        """Test agent with multiple places."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90),
            Place(name="Forum", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60),
            Place(name="Pantheon", place_type="monument", coordinates=(41.8986, 12.4768), visit_duration=30)
        ]
        travel_times = {
            ("Colosseum", "Forum"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian"),
            ("Forum", "Colosseum"): TravelTime(duration_minutes=10, distance_km=0.5, mode="pedestrian"),
            ("Colosseum", "Pantheon"): TravelTime(duration_minutes=20, distance_km=1.5, mode="pedestrian"),
            ("Pantheon", "Colosseum"): TravelTime(duration_minutes=20, distance_km=1.5, mode="pedestrian"),
            ("Forum", "Pantheon"): TravelTime(duration_minutes=15, distance_km=1.0, mode="pedestrian"),
            ("Pantheon", "Forum"): TravelTime(duration_minutes=15, distance_km=1.0, mode="pedestrian")
        }
        
        state = PlannerState(
            user_query="test",
            user_preferences=UserPreferences(
                interests=["art"],
                available_hours=8,
                max_budget=100,
                max_walking_km=10,
                crowd_tolerance="neutral"
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times=travel_times
        )
        
        result = route_optimization_agent(state)
        
        assert len(result.optimized_route) >= 3  # May include LUNCH_BREAK
        assert "Colosseum" in result.optimized_route
        assert "Forum" in result.optimized_route
        assert "Pantheon" in result.optimized_route


# ============================================================================
# Property Tests
# ============================================================================

class TestRouteOptimizationProperties:
    """Property-based tests for route optimization."""
    
    def test_property_all_places_visited_once(self):
        """
        Property: Route visits all places exactly once.
        
        **Validates: Requirements 6.1, 6.2**
        
        For any set of places with travel times, the optimized route must:
        1. Include every place exactly once
        2. Not include any place more than once
        3. Not include any place not in the input
        """
        # Test with various sizes
        test_cases = [
            # 2 places
            {
                "places": [
                    Place(name="A", place_type="monument", coordinates=(0, 0), visit_duration=60),
                    Place(name="B", place_type="monument", coordinates=(1, 1), visit_duration=60)
                ],
                "travel_times": {
                    ("A", "B"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian"),
                    ("B", "A"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian")
                }
            },
            # 3 places
            {
                "places": [
                    Place(name="A", place_type="monument", coordinates=(0, 0), visit_duration=60),
                    Place(name="B", place_type="monument", coordinates=(1, 1), visit_duration=60),
                    Place(name="C", place_type="monument", coordinates=(2, 2), visit_duration=60)
                ],
                "travel_times": {
                    ("A", "B"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian"),
                    ("B", "A"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian"),
                    ("A", "C"): TravelTime(duration_minutes=20, distance_km=2, mode="pedestrian"),
                    ("C", "A"): TravelTime(duration_minutes=20, distance_km=2, mode="pedestrian"),
                    ("B", "C"): TravelTime(duration_minutes=15, distance_km=1.5, mode="pedestrian"),
                    ("C", "B"): TravelTime(duration_minutes=15, distance_km=1.5, mode="pedestrian")
                }
            },
            # 5 places
            {
                "places": [
                    Place(name=f"Place{i}", place_type="monument", coordinates=(i, i), visit_duration=60)
                    for i in range(5)
                ],
                "travel_times": {
                    (f"Place{i}", f"Place{j}"): TravelTime(duration_minutes=abs(i-j)*10, distance_km=abs(i-j), mode="pedestrian")
                    for i in range(5) for j in range(5) if i != j
                }
            }
        ]
        
        for test_case in test_cases:
            places = test_case["places"]
            travel_times = test_case["travel_times"]
            
            # Get optimized route
            route = optimize_route(places, travel_times)
            
            # Filter out LUNCH_BREAK if present
            place_names = [name for name in route if name != "LUNCH_BREAK"]
            input_place_names = [p.name for p in places]
            
            # Property 1: All places are visited
            for place_name in input_place_names:
                assert place_name in place_names, f"Place {place_name} not in route"
            
            # Property 2: Each place visited exactly once
            for place_name in input_place_names:
                count = place_names.count(place_name)
                assert count == 1, f"Place {place_name} visited {count} times, expected 1"
            
            # Property 3: No extra places
            for place_name in place_names:
                assert place_name in input_place_names, f"Unexpected place {place_name} in route"
            
            # Property 4: Route length equals number of places
            assert len(place_names) == len(places), f"Route has {len(place_names)} places, expected {len(places)}"
    
    def test_property_route_is_valid_permutation(self):
        """
        Property: Route is a valid permutation of input places.
        
        **Validates: Requirements 6.1**
        
        The optimized route must be a permutation of the input places.
        """
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90),
            Place(name="Forum", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60),
            Place(name="Pantheon", place_type="monument", coordinates=(41.8986, 12.4768), visit_duration=30),
            Place(name="Trevi", place_type="monument", coordinates=(41.9009, 12.4833), visit_duration=20)
        ]
        travel_times = {
            (p1.name, p2.name): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian")
            for p1 in places for p2 in places if p1 != p2
        }
        
        route = optimize_route(places, travel_times)
        
        # Filter out LUNCH_BREAK
        place_names = [name for name in route if name != "LUNCH_BREAK"]
        input_place_names = sorted([p.name for p in places])
        route_place_names = sorted(place_names)
        
        assert route_place_names == input_place_names, "Route is not a valid permutation"
    
    def test_property_greedy_minimizes_distance(self):
        """
        Property: Greedy algorithm chooses nearest neighbor at each step.
        
        **Validates: Requirements 6.2**
        
        The greedy TSP solver should always choose the nearest unvisited place.
        """
        # Create a simple case where greedy choice is obvious
        matrix = np.array([
            [0, 1, 100, 100],
            [1, 0, 2, 100],
            [100, 2, 0, 3],
            [100, 100, 3, 0]
        ])
        
        route = solve_tsp_greedy(matrix, start_index=0)
        
        # Greedy should go: 0 -> 1 (nearest) -> 2 (nearest) -> 3
        assert route == [0, 1, 2, 3], f"Expected [0, 1, 2, 3], got {route}"
    
    def test_property_meal_break_in_lunch_window(self):
        """
        Property: Meal break is added during lunch window (12:30-14:00).
        
        **Validates: Requirements 6.5**
        
        If the itinerary spans lunch time, a meal break should be added.
        """
        places = [
            Place(name="Morning", place_type="monument", coordinates=(0, 0), visit_duration=120),
            Place(name="Afternoon", place_type="monument", coordinates=(1, 1), visit_duration=120)
        ]
        route = ["Morning", "Afternoon"]
        travel_times = {
            ("Morning", "Afternoon"): TravelTime(duration_minutes=30, distance_km=2, mode="pedestrian")
        }
        
        # Start at 11:00, should cross lunch window
        result = add_meal_breaks(route, places, travel_times, start_time=time(11, 0))
        
        if "LUNCH_BREAK" in result:
            # Calculate when lunch break occurs
            current_time = datetime.combine(datetime.today(), time(11, 0))
            
            for item in result:
                if item == "LUNCH_BREAK":
                    # Lunch should be added when time >= 12:30
                    assert current_time.time() >= time(12, 30), "Lunch break added too early"
                    break
                else:
                    place = next(p for p in places if p.name == item)
                    current_time += timedelta(minutes=place.visit_duration)
                    # Add travel time if not last
                    if item != result[-1] and result[result.index(item) + 1] != "LUNCH_BREAK":
                        next_item = result[result.index(item) + 1]
                        if next_item != "LUNCH_BREAK":
                            key = (item, next_item)
                            if key in travel_times:
                                current_time += timedelta(minutes=travel_times[key].duration_minutes)
    
    def test_property_opening_hours_validation(self):
        """
        Property: Opening hours validation correctly identifies conflicts.
        
        **Validates: Requirements 6.3**
        
        If a place is closed or visited outside opening hours, it should be flagged.
        """
        places = [
            Place(name="Museum", place_type="museum", coordinates=(0, 0), visit_duration=120)
        ]
        route = ["Museum"]
        opening_hours = {
            "Museum": OpeningHours(
                place_name="Museum",
                is_open_today=True,
                opening_time=time(10, 0),
                closing_time=time(18, 0),
                last_entry_time=time(17, 0),
                closed_days=[]
            )
        }
        travel_times = {}
        
        # Test various start times
        test_cases = [
            (time(9, 0), False, "before opening"),  # Too early
            (time(10, 0), True, None),  # Just right
            (time(17, 30), False, "after last entry"),  # Too late
        ]
        
        for start_time, expected_feasible, expected_issue in test_cases:
            is_feasible, issues = check_opening_hours_feasibility(
                route, places, opening_hours, travel_times, start_time
            )
            
            assert is_feasible == expected_feasible, f"Start time {start_time}: expected feasible={expected_feasible}, got {is_feasible}"
            
            if expected_issue:
                assert any(expected_issue in issue for issue in issues), f"Expected issue containing '{expected_issue}', got {issues}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
