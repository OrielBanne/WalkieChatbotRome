"""Enhanced Route Optimization with OR-Tools for constrained TSP."""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, time, timedelta

try:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logging.warning("OR-Tools not available, falling back to greedy algorithm")

from .models import Place, OpeningHours, TravelTime
from .route_optimization import build_distance_matrix, solve_tsp_greedy

logger = logging.getLogger(__name__)


def solve_tsp_ortools(
    distance_matrix: np.ndarray,
    time_windows: Optional[List[Tuple[int, int]]] = None,
    service_times: Optional[List[int]] = None
) -> Optional[List[int]]:
    """
    Solve TSP with time windows using OR-Tools.
    
    Args:
        distance_matrix: NxN matrix of travel times in minutes
        time_windows: List of (earliest, latest) time windows for each location
        service_times: List of service times (visit durations) for each location
        
    Returns:
        List of location indices in visit order, or None if no solution found
    """
    if not ORTOOLS_AVAILABLE:
        logger.warning("OR-Tools not available, using greedy fallback")
        return solve_tsp_greedy(distance_matrix)
    
    num_locations = len(distance_matrix)
    
    # Create routing index manager
    manager = pywrapcp.RoutingIndexManager(
        num_locations,
        1,  # Number of vehicles (1 for single traveler)
        0   # Depot (start location)
    )
    
    # Create routing model
    routing = pywrapcp.RoutingModel(manager)
    
    # Create distance callback
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node][to_node] * 100)  # Scale for integer
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    
    # Define cost of each arc
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # Add time window constraints if provided
    if time_windows and service_times:
        # Create time callback
        def time_callback(from_index, to_index):
            """Returns the travel time between nodes."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            travel_time = int(distance_matrix[from_node][to_node] * 100)
            service_time = int(service_times[from_node] * 100)
            return travel_time + service_time
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        
        # Add time dimension
        time = 'Time'
        routing.AddDimension(
            time_callback_index,
            30 * 100,  # Allow waiting time (30 minutes)
            24 * 60 * 100,  # Maximum time per vehicle (24 hours)
            False,  # Don't force start cumul to zero
            time
        )
        time_dimension = routing.GetDimensionOrDie(time)
        
        # Add time window constraints for each location
        for location_idx, (earliest, latest) in enumerate(time_windows):
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(
                int(earliest * 100),
                int(latest * 100)
            )
    
    # Set search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 10
    
    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        # Extract route
        route = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route.append(node)
            index = solution.Value(routing.NextVar(index))
        
        logger.info(f"OR-Tools found solution with cost: {solution.ObjectiveValue() / 100:.1f}")
        return route
    else:
        logger.warning("OR-Tools could not find solution, using greedy fallback")
        return solve_tsp_greedy(distance_matrix)


def create_time_windows(
    places: List[Place],
    opening_hours: Dict[str, OpeningHours],
    ticket_info: Optional[Dict[str, 'TicketInfo']] = None,
    start_time: time = time(9, 0)
) -> List[Tuple[int, int]]:
    """
    Create time windows for each place based on opening hours and ticket time slots.
    
    Args:
        places: List of places
        opening_hours: Dictionary of opening hours
        ticket_info: Optional dictionary of ticket information with time slots
        start_time: Starting time of day
        
    Returns:
        List of (earliest_minutes, latest_minutes) tuples from start_time
    """
    time_windows = []
    start_dt = datetime.combine(datetime.today(), start_time)
    
    for place in places:
        hours = opening_hours.get(place.name)
        tickets = ticket_info.get(place.name) if ticket_info else None
        
        # Start with opening hours constraints
        if hours and hours.opening_time and hours.last_entry_time:
            # Calculate minutes from start time
            opening_dt = datetime.combine(datetime.today(), hours.opening_time)
            last_entry_dt = datetime.combine(datetime.today(), hours.last_entry_time)
            
            earliest = max(0, int((opening_dt - start_dt).total_seconds() / 60))
            latest = int((last_entry_dt - start_dt).total_seconds() / 60)
        else:
            # No opening hours constraints: available all day
            earliest = 0
            latest = 12 * 60  # 12 hours window
        
        # Further constrain by ticket time slots if required
        if tickets and tickets.time_slot_required and tickets.available_time_slots:
            # Find the earliest and latest available time slots
            slot_earliest = float('inf')
            slot_latest = 0
            
            for slot_start, slot_end in tickets.available_time_slots:
                slot_start_dt = datetime.combine(datetime.today(), slot_start)
                slot_end_dt = datetime.combine(datetime.today(), slot_end)
                
                slot_start_min = int((slot_start_dt - start_dt).total_seconds() / 60)
                slot_end_min = int((slot_end_dt - start_dt).total_seconds() / 60)
                
                slot_earliest = min(slot_earliest, slot_start_min)
                slot_latest = max(slot_latest, slot_end_min)
            
            # Intersect with opening hours
            if slot_earliest != float('inf'):
                earliest = max(earliest, slot_earliest)
                latest = min(latest, slot_latest)
        
        time_windows.append((earliest, latest))
    
    return time_windows


def optimize_route_with_ortools(
    places: List[Place],
    travel_times: Dict[Tuple[str, str], TravelTime],
    opening_hours: Optional[Dict[str, OpeningHours]] = None,
    ticket_info: Optional[Dict[str, 'TicketInfo']] = None,
    start_time: time = time(9, 0)
) -> List[str]:
    """
    Optimize route using OR-Tools with time window and ticket time slot constraints.
    
    Args:
        places: List of places to visit
        travel_times: Dictionary of travel times
        opening_hours: Optional opening hours constraints
        ticket_info: Optional ticket information with time slot constraints
        start_time: Starting time of day
        
    Returns:
        List of place names in optimized order
    """
    if len(places) <= 1:
        return [p.name for p in places]
    
    # Build distance matrix
    dist_matrix = build_distance_matrix(places, travel_times)
    
    # Create time windows and service times if opening hours provided
    time_windows = None
    service_times = None
    
    if opening_hours:
        time_windows = create_time_windows(places, opening_hours, ticket_info, start_time)
        service_times = [place.visit_duration for place in places]
    
    # Solve TSP with OR-Tools
    route_indices = solve_tsp_ortools(dist_matrix, time_windows, service_times)
    
    if route_indices is None:
        logger.error("Failed to find route")
        return [p.name for p in places]
    
    # Convert indices to place names
    optimized_route = [places[i].name for i in route_indices]
    
    return optimized_route


def benchmark_algorithms(
    places: List[Place],
    travel_times: Dict[Tuple[str, str], TravelTime],
    opening_hours: Optional[Dict[str, OpeningHours]] = None,
    ticket_info: Optional[Dict[str, 'TicketInfo']] = None,
    start_time: time = time(9, 0)
) -> Dict[str, any]:
    """
    Benchmark OR-Tools vs greedy algorithm for route optimization.
    
    Args:
        places: List of places to visit
        travel_times: Dictionary of travel times
        opening_hours: Optional opening hours constraints
        ticket_info: Optional ticket information
        start_time: Starting time of day
        
    Returns:
        Dictionary with benchmark results including routes, costs, and timings
    """
    import time as time_module
    
    if len(places) <= 1:
        return {
            "places_count": len(places),
            "greedy_route": [p.name for p in places],
            "ortools_route": [p.name for p in places],
            "greedy_cost": 0,
            "ortools_cost": 0,
            "greedy_time_ms": 0,
            "ortools_time_ms": 0,
            "improvement_percent": 0
        }
    
    # Build distance matrix
    dist_matrix = build_distance_matrix(places, travel_times)
    
    # Prepare time windows and service times
    time_windows = None
    service_times = None
    if opening_hours:
        time_windows = create_time_windows(places, opening_hours, ticket_info, start_time)
        service_times = [place.visit_duration for place in places]
    
    # Benchmark greedy algorithm
    start = time_module.perf_counter()
    greedy_indices = solve_tsp_greedy(dist_matrix)
    greedy_time = (time_module.perf_counter() - start) * 1000  # Convert to ms
    
    # Calculate greedy cost
    greedy_cost = 0
    for i in range(len(greedy_indices) - 1):
        greedy_cost += dist_matrix[greedy_indices[i]][greedy_indices[i + 1]]
    
    # Benchmark OR-Tools algorithm
    start = time_module.perf_counter()
    ortools_indices = solve_tsp_ortools(dist_matrix, time_windows, service_times)
    ortools_time = (time_module.perf_counter() - start) * 1000  # Convert to ms
    
    # Calculate OR-Tools cost
    ortools_cost = 0
    if ortools_indices:
        for i in range(len(ortools_indices) - 1):
            ortools_cost += dist_matrix[ortools_indices[i]][ortools_indices[i + 1]]
    else:
        ortools_indices = greedy_indices
        ortools_cost = greedy_cost
    
    # Calculate improvement
    improvement = 0
    if greedy_cost > 0:
        improvement = ((greedy_cost - ortools_cost) / greedy_cost) * 100
    
    return {
        "places_count": len(places),
        "greedy_route": [places[i].name for i in greedy_indices],
        "ortools_route": [places[i].name for i in ortools_indices],
        "greedy_cost": round(greedy_cost, 2),
        "ortools_cost": round(ortools_cost, 2),
        "greedy_time_ms": round(greedy_time, 2),
        "ortools_time_ms": round(ortools_time, 2),
        "improvement_percent": round(improvement, 2),
        "ortools_available": ORTOOLS_AVAILABLE
    }
