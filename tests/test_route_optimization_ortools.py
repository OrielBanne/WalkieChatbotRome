"""Integration tests for OR-Tools route optimization."""

import pytest
import numpy as np
from datetime import time, datetime
from typing import List, Dict, Tuple

from src.agents.route_optimization_ortools import (
    solve_tsp_ortools,
    create_time_windows,
    optimize_route_with_ortools,
    benchmark_algorithms,
    ORTOOLS_AVAILABLE
)
from src.agents.models import Place, TravelTime, OpeningHours, TicketInfo


# Skip all tests if OR-Tools is not available
pytestmark = pytest.mark.skipif(not ORTOOLS_AVAILABLE, reason="OR-Tools not installed")


class TestSolveTspOrtools:
    """Test OR-Tools TSP solver."""
    
    def test_single_location(self):
        """Test TSP with single location."""
        matrix = np.array([[0]])
        route = solve_tsp_ortools(matrix)
        assert route == [0]
    
    def test_two_locations(self):
        """Test TSP with two locations."""
        matrix = np.array([
            [0, 10],
            [10, 0]
        ])
        route = solve_tsp_ortools(matrix)
        assert route == [0, 1]
    
    def test_three_locations_simple(self):
        """Test TSP with three locations."""
        matrix = np.array([
            [0, 1, 10],
            [1, 0, 1],
            [10, 1, 0]
        ])
        route = solve_tsp_ortools(matrix)
        # Should find optimal route: 0 -> 1 -> 2
        assert len(route) == 3
        assert route[0] == 0  # Starts at depot
        assert set(route) == {0, 1, 2}  # All locations visited
    
    def test_with_time_windows(self):
        """Test TSP with time window constraints."""
        matrix = np.array([
            [0, 10, 20],
            [10, 0, 10],
            [20, 10, 0]
        ])
        # Time windows: location 0 (0-100), location 1 (20-80), location 2 (50-120)
        time_windows = [(0, 100), (20, 80), (50, 120)]
        service_times = [10, 10, 10]
        
        route = solve_tsp_ortools(matrix, time_windows, service_times)
        
        assert len(route) == 3
        assert route[0] == 0  # Starts at depot
        assert set(route) == {0, 1, 2}
    
    def test_with_tight_time_windows(self):
        """Test TSP with tight time windows that force specific order."""
        matrix = np.array([
            [0, 10, 10],
            [10, 0, 10],
            [10, 10, 0]
        ])
        # Force order: 0 -> 1 -> 2 with tight windows
        time_windows = [(0, 10), (10, 30), (30, 50)]
        service_times = [5, 5, 5]
        
        route = solve_tsp_ortools(matrix, time_windows, service_times)
        
        # Should respect time windows
        assert len(route) == 3
        assert route[0] == 0


class TestCreateTimeWindows:
    """Test time window creation from opening hours and ticket slots."""
    
    def test_basic_opening_hours(self):
        """Test time windows from opening hours."""
        places = [
            Place(name="Museum", place_type="museum", coordinates=(0, 0), visit_duration=60),
            Place(name="Monument", place_type="monument", coordinates=(1, 1), visit_duration=90)
        ]
        opening_hours = {
            "Museum": OpeningHours(
                place_name="Museum",
                is_open_today=True,
                opening_time=time(10, 0),
                closing_time=time(18, 0),
                last_entry_time=time(17, 0),
                closed_days=[]
            ),
            "Monument": OpeningHours(
                place_name="Monument",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 30),
                closed_days=[]
            )
        }
        
        windows = create_time_windows(places, opening_hours, start_time=time(9, 0))
        
        # Museum: 10:00-17:00 from 9:00 start = 60-480 minutes
        assert windows[0] == (60, 480)
        # Monument: 9:00-18:30 from 9:00 start = 0-570 minutes
        assert windows[1] == (0, 570)
    
    def test_no_opening_hours(self):
        """Test time windows when no opening hours provided."""
        places = [
            Place(name="Park", place_type="park", coordinates=(0, 0), visit_duration=30)
        ]
        opening_hours = {}
        
        windows = create_time_windows(places, opening_hours)
        
        # Should have wide window (0-720 minutes = 12 hours)
        assert windows[0] == (0, 720)
    
    def test_with_ticket_time_slots(self):
        """Test time windows constrained by ticket time slots."""
        places = [
            Place(name="Vatican", place_type="museum", coordinates=(0, 0), visit_duration=120)
        ]
        opening_hours = {
            "Vatican": OpeningHours(
                place_name="Vatican",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(18, 0),
                last_entry_time=time(16, 0),
                closed_days=[]
            )
        }
        ticket_info = {
            "Vatican": TicketInfo(
                place_name="Vatican",
                ticket_required=True,
                reservation_required=True,
                price=20.0,
                time_slot_required=True,
                available_time_slots=[
                    (time(10, 0), time(12, 0)),
                    (time(14, 0), time(16, 0))
                ]
            )
        }
        
        windows = create_time_windows(places, opening_hours, ticket_info, start_time=time(9, 0))
        
        # Should be constrained by ticket slots: 10:00-16:00 from 9:00 start = 60-420 minutes
        assert windows[0][0] == 60  # Earliest slot start
        assert windows[0][1] == 420  # Latest slot end
    
    def test_multiple_places_mixed_constraints(self):
        """Test time windows with mixed constraints."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(0, 0), visit_duration=90),
            Place(name="Vatican", place_type="museum", coordinates=(1, 1), visit_duration=120),
            Place(name="Park", place_type="park", coordinates=(2, 2), visit_duration=30)
        ]
        opening_hours = {
            "Colosseum": OpeningHours(
                place_name="Colosseum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            ),
            "Vatican": OpeningHours(
                place_name="Vatican",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(18, 0),
                last_entry_time=time(16, 0),
                closed_days=[]
            )
        }
        ticket_info = {
            "Vatican": TicketInfo(
                place_name="Vatican",
                ticket_required=True,
                reservation_required=True,
                price=20.0,
                time_slot_required=True,
                available_time_slots=[(time(10, 0), time(12, 0))]
            )
        }
        
        windows = create_time_windows(places, opening_hours, ticket_info, start_time=time(9, 0))
        
        assert len(windows) == 3
        # Colosseum: 9:00-18:00 = 0-540 minutes
        assert windows[0] == (0, 540)
        # Vatican: constrained by ticket slot 10:00-12:00 = 60-180 minutes
        assert windows[1] == (60, 180)
        # Park: no constraints = 0-720 minutes
        assert windows[2] == (0, 720)


class TestOptimizeRouteWithOrtools:
    """Test full route optimization with OR-Tools."""
    
    def test_simple_route(self):
        """Test optimization with simple route."""
        places = [
            Place(name="A", place_type="monument", coordinates=(0, 0), visit_duration=60),
            Place(name="B", place_type="monument", coordinates=(1, 1), visit_duration=60),
            Place(name="C", place_type="monument", coordinates=(2, 2), visit_duration=60)
        ]
        travel_times = {
            ("A", "B"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian"),
            ("B", "A"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian"),
            ("A", "C"): TravelTime(duration_minutes=20, distance_km=2, mode="pedestrian"),
            ("C", "A"): TravelTime(duration_minutes=20, distance_km=2, mode="pedestrian"),
            ("B", "C"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian"),
            ("C", "B"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian")
        }
        
        route = optimize_route_with_ortools(places, travel_times)
        
        assert len(route) == 3
        assert set(route) == {"A", "B", "C"}
        assert route[0] == "A"  # Should start at first place
    
    def test_with_opening_hours(self):
        """Test optimization respecting opening hours."""
        places = [
            Place(name="Morning", place_type="monument", coordinates=(0, 0), visit_duration=60),
            Place(name="Afternoon", place_type="monument", coordinates=(1, 1), visit_duration=60)
        ]
        travel_times = {
            ("Morning", "Afternoon"): TravelTime(duration_minutes=30, distance_km=2, mode="pedestrian"),
            ("Afternoon", "Morning"): TravelTime(duration_minutes=30, distance_km=2, mode="pedestrian")
        }
        opening_hours = {
            "Morning": OpeningHours(
                place_name="Morning",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(12, 0),
                last_entry_time=time(11, 0),
                closed_days=[]
            ),
            "Afternoon": OpeningHours(
                place_name="Afternoon",
                is_open_today=True,
                opening_time=time(14, 0),
                closing_time=time(18, 0),
                last_entry_time=time(17, 0),
                closed_days=[]
            )
        }
        
        route = optimize_route_with_ortools(
            places, travel_times, opening_hours, start_time=time(9, 0)
        )
        
        # Should visit Morning first (9:00-12:00), then Afternoon (14:00-18:00)
        assert route[0] == "Morning"
        assert route[1] == "Afternoon"
    
    def test_with_ticket_time_slots(self):
        """Test optimization with ticket time slot constraints."""
        places = [
            Place(name="Vatican", place_type="museum", coordinates=(0, 0), visit_duration=120),
            Place(name="Colosseum", place_type="monument", coordinates=(1, 1), visit_duration=90)
        ]
        travel_times = {
            ("Vatican", "Colosseum"): TravelTime(duration_minutes=20, distance_km=2, mode="pedestrian"),
            ("Colosseum", "Vatican"): TravelTime(duration_minutes=20, distance_km=2, mode="pedestrian")
        }
        opening_hours = {
            "Vatican": OpeningHours(
                place_name="Vatican",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(18, 0),
                last_entry_time=time(16, 0),
                closed_days=[]
            ),
            "Colosseum": OpeningHours(
                place_name="Colosseum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            )
        }
        ticket_info = {
            "Vatican": TicketInfo(
                place_name="Vatican",
                ticket_required=True,
                reservation_required=True,
                price=20.0,
                time_slot_required=True,
                available_time_slots=[(time(10, 0), time(12, 0))]
            )
        }
        
        route = optimize_route_with_ortools(
            places, travel_times, opening_hours, ticket_info, start_time=time(9, 0)
        )
        
        assert len(route) == 2
        assert set(route) == {"Vatican", "Colosseum"}


class TestBenchmarkAlgorithms:
    """Test benchmarking functionality."""
    
    def test_benchmark_simple_case(self):
        """Test benchmark with simple case."""
        places = [
            Place(name="A", place_type="monument", coordinates=(0, 0), visit_duration=60),
            Place(name="B", place_type="monument", coordinates=(1, 1), visit_duration=60),
            Place(name="C", place_type="monument", coordinates=(2, 2), visit_duration=60)
        ]
        travel_times = {
            ("A", "B"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian"),
            ("B", "A"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian"),
            ("A", "C"): TravelTime(duration_minutes=20, distance_km=2, mode="pedestrian"),
            ("C", "A"): TravelTime(duration_minutes=20, distance_km=2, mode="pedestrian"),
            ("B", "C"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian"),
            ("C", "B"): TravelTime(duration_minutes=10, distance_km=1, mode="pedestrian")
        }
        
        results = benchmark_algorithms(places, travel_times)
        
        # Check result structure
        assert "places_count" in results
        assert "greedy_route" in results
        assert "ortools_route" in results
        assert "greedy_cost" in results
        assert "ortools_cost" in results
        assert "greedy_time_ms" in results
        assert "ortools_time_ms" in results
        assert "improvement_percent" in results
        assert "ortools_available" in results
        
        # Check values
        assert results["places_count"] == 3
        assert len(results["greedy_route"]) == 3
        assert len(results["ortools_route"]) == 3
        assert results["greedy_cost"] >= 0
        assert results["ortools_cost"] >= 0
        assert results["greedy_time_ms"] >= 0
        assert results["ortools_time_ms"] >= 0
        assert results["ortools_available"] == True
    
    def test_benchmark_ortools_better_or_equal(self):
        """Test that OR-Tools finds solution at least as good as greedy."""
        places = [
            Place(name=f"Place{i}", place_type="monument", coordinates=(i, i), visit_duration=60)
            for i in range(5)
        ]
        travel_times = {
            (f"Place{i}", f"Place{j}"): TravelTime(
                duration_minutes=abs(i-j)*10,
                distance_km=abs(i-j),
                mode="pedestrian"
            )
            for i in range(5) for j in range(5) if i != j
        }
        
        results = benchmark_algorithms(places, travel_times)
        
        # OR-Tools should find solution at least as good as greedy
        assert results["ortools_cost"] <= results["greedy_cost"]
        assert results["improvement_percent"] >= 0
    
    def test_benchmark_with_constraints(self):
        """Test benchmark with opening hours constraints."""
        places = [
            Place(name="A", place_type="monument", coordinates=(0, 0), visit_duration=60),
            Place(name="B", place_type="monument", coordinates=(1, 1), visit_duration=60),
            Place(name="C", place_type="monument", coordinates=(2, 2), visit_duration=60)
        ]
        travel_times = {
            (p1.name, p2.name): TravelTime(duration_minutes=15, distance_km=1.5, mode="pedestrian")
            for p1 in places for p2 in places if p1 != p2
        }
        opening_hours = {
            place.name: OpeningHours(
                place_name=place.name,
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(18, 0),
                last_entry_time=time(17, 0),
                closed_days=[]
            )
            for place in places
        }
        
        results = benchmark_algorithms(places, travel_times, opening_hours)
        
        assert results["places_count"] == 3
        assert len(results["greedy_route"]) == 3
        assert len(results["ortools_route"]) == 3
    
    def test_benchmark_single_place(self):
        """Test benchmark with single place."""
        places = [
            Place(name="A", place_type="monument", coordinates=(0, 0), visit_duration=60)
        ]
        travel_times = {}
        
        results = benchmark_algorithms(places, travel_times)
        
        assert results["places_count"] == 1
        assert results["greedy_cost"] == 0
        assert results["ortools_cost"] == 0
        assert results["improvement_percent"] == 0


class TestOrtoolsIntegration:
    """Integration tests for OR-Tools functionality."""
    
    def test_full_rome_itinerary(self):
        """Test optimization with realistic Rome itinerary."""
        places = [
            Place(name="Colosseum", place_type="monument", coordinates=(41.8902, 12.4922), visit_duration=90),
            Place(name="Roman Forum", place_type="monument", coordinates=(41.8925, 12.4853), visit_duration=60),
            Place(name="Pantheon", place_type="monument", coordinates=(41.8986, 12.4768), visit_duration=30),
            Place(name="Trevi Fountain", place_type="monument", coordinates=(41.9009, 12.4833), visit_duration=20),
            Place(name="Spanish Steps", place_type="monument", coordinates=(41.9058, 12.4823), visit_duration=15)
        ]
        
        # Create travel times (simplified)
        travel_times = {}
        for i, p1 in enumerate(places):
            for j, p2 in enumerate(places):
                if i != j:
                    # Simplified distance calculation
                    dist = abs(i - j) * 10
                    travel_times[(p1.name, p2.name)] = TravelTime(
                        duration_minutes=dist,
                        distance_km=dist/10,
                        mode="pedestrian"
                    )
        
        # Create opening hours
        opening_hours = {
            place.name: OpeningHours(
                place_name=place.name,
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0),
                last_entry_time=time(18, 0),
                closed_days=[]
            )
            for place in places
        }
        
        route = optimize_route_with_ortools(
            places, travel_times, opening_hours, start_time=time(9, 0)
        )
        
        assert len(route) == 5
        assert set(route) == {p.name for p in places}
        
        # Run benchmark
        results = benchmark_algorithms(places, travel_times, opening_hours)
        
        print(f"\nBenchmark Results for Rome Itinerary:")
        print(f"  Places: {results['places_count']}")
        print(f"  Greedy cost: {results['greedy_cost']} minutes")
        print(f"  OR-Tools cost: {results['ortools_cost']} minutes")
        print(f"  Improvement: {results['improvement_percent']}%")
        print(f"  Greedy time: {results['greedy_time_ms']:.2f} ms")
        print(f"  OR-Tools time: {results['ortools_time_ms']:.2f} ms")
        
        assert results["ortools_cost"] <= results["greedy_cost"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
