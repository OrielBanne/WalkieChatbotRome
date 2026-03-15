"""Travel Time Agent for calculating travel times between places."""

import logging
from typing import Dict, Tuple

from ..router import Router
from .models import TravelTime, PlannerState

logger = logging.getLogger(__name__)


def calculate_travel_time(
    start_coords: Tuple[float, float],
    end_coords: Tuple[float, float],
    mode: str = "pedestrian"
) -> TravelTime:
    """
    Calculate travel time between two coordinates.
    
    Args:
        start_coords: Starting coordinates (lat, lon)
        end_coords: Ending coordinates (lat, lon)
        mode: Transport mode (pedestrian, car, public_transport)
        
    Returns:
        TravelTime object with duration and distance
    """
    router = Router()
    
    result = router.get_route(start_coords, end_coords, mode=mode)
    
    if result:
        route_coords, duration_seconds = result
        
        # Calculate distance from route coordinates
        distance_km = calculate_route_distance(route_coords)
        
        return TravelTime(
            duration_minutes=max(duration_seconds / 60, 0.1),
            distance_km=distance_km,
            mode=mode
        )
    else:
        # Fallback: estimate based on straight-line distance
        logger.warning(f"Routing failed, using straight-line estimate")
        distance_km = calculate_haversine_distance(start_coords, end_coords)
        
        # Estimate walking time: 5 km/h average pace
        duration_minutes = max((distance_km / 5.0) * 60, 0.1)
        
        return TravelTime(
            duration_minutes=duration_minutes,
            distance_km=distance_km,
            mode=mode
        )


def calculate_route_distance(route_coords: list) -> float:
    """
    Calculate total distance of a route from coordinates.
    
    Args:
        route_coords: List of (lat, lon) tuples
        
    Returns:
        Distance in kilometers
    """
    if len(route_coords) < 2:
        return 0.0
    
    total_distance = 0.0
    for i in range(len(route_coords) - 1):
        total_distance += calculate_haversine_distance(
            route_coords[i],
            route_coords[i + 1]
        )
    
    return total_distance


def calculate_haversine_distance(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float]
) -> float:
    """
    Calculate straight-line distance between two coordinates using Haversine formula.
    
    Args:
        coord1: First coordinate (lat, lon)
        coord2: Second coordinate (lat, lon)
        
    Returns:
        Distance in kilometers
    """
    from math import radians, sin, cos, sqrt, atan2
    
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = R * c
    return distance


def suggest_transport_mode(distance_km: float) -> str:
    """
    Suggest transport mode based on distance.
    
    Args:
        distance_km: Distance in kilometers
        
    Returns:
        Suggested mode: pedestrian, public_transport, or car
    """
    if distance_km < 2.0:
        return "pedestrian"
    elif distance_km < 5.0:
        return "public_transport"
    else:
        return "car"



def travel_time_agent(state: PlannerState) -> PlannerState:
    """
    Travel Time Agent - Phase 1: fast Manhattan-distance estimates for all pairs.
    No Router calls here; just instant geometric estimates for route ordering.

    Args:
        state: Current planner state

    Returns:
        Updated state with estimated travel_times populated
    """
    logger.info("Travel Time Agent: Computing Manhattan-distance estimates for all pairs")

    places = state.candidate_places
    # Reuse existing estimates — only compute for new pairs
    travel_times = dict(state.travel_times) if state.travel_times else {}

    computed = 0
    for i, place_a in enumerate(places):
        for j, place_b in enumerate(places):
            if i >= j:
                continue
            if (place_a.name, place_b.name) in travel_times:
                continue  # Already have data for this pair

            # Manhattan distance on coordinates (cab-driver distance)
            lat1, lon1 = place_a.coordinates
            lat2, lon2 = place_b.coordinates

            # Convert degree deltas to approximate km
            # At Rome's latitude (~41.9°N): 1° lat ≈ 111 km, 1° lon ≈ 83 km
            dlat_km = abs(lat2 - lat1) * 111.0
            dlon_km = abs(lon2 - lon1) * 83.0
            manhattan_km = dlat_km + dlon_km

            # Estimate walking time: ~5 km/h, with 1.3x factor for real streets
            duration_minutes = max((manhattan_km * 1.3 / 5.0) * 60, 0.1)

            travel_time = TravelTime(
                duration_minutes=duration_minutes,
                distance_km=manhattan_km,
                mode="pedestrian"
            )

            travel_times[(place_a.name, place_b.name)] = travel_time
            travel_times[(place_b.name, place_a.name)] = travel_time
            computed += 1

    state.travel_times = travel_times
    logger.info(f"Travel Time Agent: {computed} new pairs computed, {len(travel_times)} total")

    return state


def refine_travel_times_agent(state: PlannerState) -> PlannerState:
    """
    Phase 2: Refine travel times using the Router, but ONLY for sequential
    pairs in the optimized route. This is O(n) instead of O(n²).

    Args:
        state: Current planner state (must have optimized_route set)

    Returns:
        Updated state with accurate travel_times for route pairs
    """
    route = state.optimized_route
    if len(route) < 2:
        return state

    logger.info(f"Refine Travel Times: Computing exact times for {len(route)-1} sequential pairs")

    place_dict = {p.name: p for p in state.candidate_places}
    router = Router()

    for i in range(len(route) - 1):
        name_a = route[i]
        name_b = route[i + 1]

        # Skip lunch breaks
        if name_a == "LUNCH_BREAK" or name_b == "LUNCH_BREAK":
            continue

        place_a = place_dict.get(name_a)
        place_b = place_dict.get(name_b)
        if not place_a or not place_b:
            continue

        try:
            result = router.get_route(
                place_a.coordinates,
                place_b.coordinates,
                mode="pedestrian"
            )

            if result:
                route_coords, duration_seconds = result
                distance_km = calculate_route_distance(route_coords)
                travel_time = TravelTime(
                    duration_minutes=max(duration_seconds / 60, 0.1),
                    distance_km=distance_km,
                    mode="pedestrian"
                )
            else:
                distance = calculate_haversine_distance(
                    place_a.coordinates, place_b.coordinates
                )
                travel_time = TravelTime(
                    duration_minutes=max((distance / 5.0) * 60, 0.1),
                    distance_km=distance,
                    mode="pedestrian"
                )

            # Overwrite the Manhattan estimate with the real value
            state.travel_times[(name_a, name_b)] = travel_time
            state.travel_times[(name_b, name_a)] = travel_time

        except Exception as e:
            logger.error(f"Error refining travel time {name_a} -> {name_b}: {e}")
            # Keep the Manhattan estimate as fallback

    logger.info("Refine Travel Times: Done")
    return state


