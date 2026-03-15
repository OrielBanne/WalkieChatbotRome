"""Route Optimization Agent for optimizing place visit order."""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, time, timedelta

from .models import Place, PlannerState, OpeningHours, TravelTime

logger = logging.getLogger(__name__)


def build_distance_matrix(
    places: List[Place],
    travel_times: Dict[Tuple[str, str], TravelTime]
) -> np.ndarray:
    """
    Build distance matrix from travel times.
    
    Args:
        places: List of places
        travel_times: Dictionary of travel times between places
        
    Returns:
        NxN numpy array of travel times in minutes
    """
    n = len(places)
    matrix = np.zeros((n, n))
    
    for i, place_a in enumerate(places):
        for j, place_b in enumerate(places):
            if i == j:
                matrix[i][j] = 0
            else:
                key = (place_a.name, place_b.name)
                if key in travel_times:
                    matrix[i][j] = travel_times[key].duration_minutes
                else:
                    # Use large value if no travel time available
                    matrix[i][j] = 999
    
    return matrix


def solve_tsp_greedy(distance_matrix: np.ndarray, start_index: int = 0) -> List[int]:
    """
    Solve TSP using greedy nearest neighbor algorithm.
    
    Args:
        distance_matrix: NxN matrix of distances
        start_index: Starting city index
        
    Returns:
        List of city indices in visit order
    """
    n = len(distance_matrix)
    unvisited = set(range(n))
    route = [start_index]
    unvisited.remove(start_index)
    
    current = start_index
    
    while unvisited:
        # Find nearest unvisited city
        nearest = min(unvisited, key=lambda city: distance_matrix[current][city])
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest
    
    return route


def solve_tsp_greedy_coords(places: List[Place], start_index: int = 0) -> List[int]:
    """
    Solve TSP using greedy nearest neighbor on raw coordinates.
    Fallback when travel_times are unavailable.
    
    Args:
        places: List of places with coordinates
        start_index: Starting place index
        
    Returns:
        List of place indices in visit order
    """
    import math
    n = len(places)
    unvisited = set(range(n))
    route = [start_index]
    unvisited.remove(start_index)
    current = start_index

    while unvisited:
        lat1, lon1 = places[current].coordinates
        nearest = min(
            unvisited,
            key=lambda j: math.sqrt(
                (lat1 - places[j].coordinates[0]) ** 2 +
                (lon1 - places[j].coordinates[1]) ** 2
            )
        )
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest

    return route


def check_opening_hours_feasibility(
    route: List[str],
    places: List[Place],
    opening_hours: Dict[str, OpeningHours],
    travel_times: Dict[Tuple[str, str], TravelTime],
    start_time: time = time(9, 0)
) -> Tuple[bool, List[str]]:
    """
    Check if route respects opening hours constraints.
    
    Args:
        route: List of place names in visit order
        places: List of Place objects
        opening_hours: Dictionary of opening hours
        travel_times: Dictionary of travel times
        start_time: Starting time of day
        
    Returns:
        Tuple of (is_feasible, list of issues)
    """
    issues = []
    current_time = datetime.combine(datetime.today(), start_time)
    place_dict = {p.name: p for p in places}
    
    for i, place_name in enumerate(route):
        place = place_dict.get(place_name)
        if not place:
            continue
        
        hours = opening_hours.get(place_name)
        if not hours:
            continue
        
        # Check if place is open
        if not hours.is_open_today:
            issues.append(f"{place_name} is closed today")
            continue
        
        # Check if we arrive before opening
        if hours.opening_time:
            opening_dt = datetime.combine(datetime.today(), hours.opening_time)
            if current_time < opening_dt:
                issues.append(f"Arrive at {place_name} before opening ({hours.opening_time})")
        
        # Check if we arrive after last entry
        if hours.last_entry_time:
            last_entry_dt = datetime.combine(datetime.today(), hours.last_entry_time)
            if current_time > last_entry_dt:
                issues.append(f"Arrive at {place_name} after last entry ({hours.last_entry_time})")
        
        # Update current time (add visit duration + travel to next)
        current_time += timedelta(minutes=place.visit_duration)
        
        if i < len(route) - 1:
            next_place = route[i + 1]
            travel_key = (place_name, next_place)
            if travel_key in travel_times:
                current_time += timedelta(minutes=travel_times[travel_key].duration_minutes)
    
    is_feasible = len(issues) == 0
    return is_feasible, issues


def add_meal_breaks(
    route: List[str],
    places: List[Place],
    travel_times: Dict[Tuple[str, str], TravelTime],
    start_time: time = time(9, 0)
) -> List[str]:
    """
    Add meal breaks to route if needed.
    
    Args:
        route: List of place names
        places: List of Place objects
        travel_times: Dictionary of travel times
        start_time: Starting time
        
    Returns:
        Route with meal breaks inserted
    """
    place_dict = {p.name: p for p in places}
    current_time = datetime.combine(datetime.today(), start_time)
    new_route = []
    lunch_added = False
    
    # Lunch time window: 12:30 - 14:00
    lunch_start = datetime.combine(datetime.today(), time(12, 30))
    lunch_end = datetime.combine(datetime.today(), time(14, 0))
    
    for i, place_name in enumerate(route):
        place = place_dict.get(place_name)
        if not place:
            new_route.append(place_name)
            continue
        
        # Check if we should add lunch before this place
        if not lunch_added and current_time >= lunch_start:
            new_route.append("LUNCH_BREAK")
            lunch_added = True
            current_time += timedelta(minutes=60)  # 1 hour lunch
        
        new_route.append(place_name)
        current_time += timedelta(minutes=place.visit_duration)
        
        # Add travel time to next place
        if i < len(route) - 1:
            next_place = route[i + 1]
            travel_key = (place_name, next_place)
            if travel_key in travel_times:
                current_time += timedelta(minutes=travel_times[travel_key].duration_minutes)
    
    return new_route


def optimize_route(
    places: List[Place],
    travel_times: Dict[Tuple[str, str], TravelTime],
    opening_hours: Optional[Dict[str, OpeningHours]] = None,
    start_time: time = time(9, 0)
) -> List[str]:
    """
    Optimize route order to minimize travel time.
    
    Args:
        places: List of places to visit
        travel_times: Dictionary of travel times
        opening_hours: Optional opening hours constraints
        start_time: Starting time of day
        
    Returns:
        List of place names in optimized order
    """
    if len(places) <= 1:
        return [p.name for p in places]
    
    # Check if we have enough travel_times to use the distance matrix approach
    has_travel_data = len(travel_times) > 0
    
    if has_travel_data:
        # Build distance matrix
        dist_matrix = build_distance_matrix(places, travel_times)
        # Solve TSP using greedy algorithm
        route_indices = solve_tsp_greedy(dist_matrix, start_index=0)
    else:
        # Fallback: use coordinate-based nearest neighbor
        logger.info("No travel times available, using coordinate-based route optimization")
        route_indices = solve_tsp_greedy_coords(places, start_index=0)
    
    # Convert indices to place names
    optimized_route = [places[i].name for i in route_indices]
    
    # Check opening hours feasibility if provided
    if opening_hours:
        is_feasible, issues = check_opening_hours_feasibility(
            optimized_route,
            places,
            opening_hours,
            travel_times,
            start_time
        )
        
        if not is_feasible:
            logger.warning(f"Route has opening hours issues: {issues}")
    
    return optimized_route


def route_optimization_agent(state: PlannerState) -> PlannerState:
    """
    Route Optimization Agent - optimizes the order of places to minimize travel time.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with optimized_route populated
    """
    logger.info("Route Optimization Agent: Optimizing route order")
    
    # Use selected places if available, otherwise use top candidate places
    places = state.selected_places if state.selected_places else state.candidate_places[:5]
    
    if len(places) == 0:
        logger.warning("No places to optimize")
        state.optimized_route = []
        return state
    
    if len(places) == 1:
        logger.info("Only one place, no optimization needed")
        state.optimized_route = [places[0].name]
        return state
    
    # Get start time from user preferences or use default
    start_time = state.user_preferences.start_time if state.user_preferences.start_time else time(9, 0)
    
    # Optimize route
    optimized_route = optimize_route(
        places,
        state.travel_times,
        state.opening_hours,
        start_time
    )
    
    # Add meal breaks
    route_with_meals = add_meal_breaks(
        optimized_route,
        places,
        state.travel_times,
        start_time
    )
    
    state.optimized_route = route_with_meals
    
    # Calculate total distance
    total_distance = 0.0
    for i in range(len(optimized_route) - 1):
        key = (optimized_route[i], optimized_route[i + 1])
        if key in state.travel_times:
            total_distance += state.travel_times[key].distance_km
    
    logger.info(
        f"Route Optimization Agent: Optimized route with {len(optimized_route)} places, "
        f"total distance: {total_distance:.2f} km"
    )
    
    return state
