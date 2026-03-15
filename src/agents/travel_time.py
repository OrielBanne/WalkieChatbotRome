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
            duration_minutes=duration_seconds / 60,
            distance_km=distance_km,
            mode=mode
        )
    else:
        # Fallback: estimate based on straight-line distance
        logger.warning(f"Routing failed, using straight-line estimate")
        distance_km = calculate_haversine_distance(start_coords, end_coords)
        
        # Estimate walking time: 5 km/h average pace
        duration_minutes = (distance_km / 5.0) * 60
        
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
    Travel Time Agent - calculates travel times between all place pairs.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with travel_times populated
    """
    logger.info("Travel Time Agent: Calculating travel times between places")
    
    places = state.candidate_places
    travel_times = {}
    
    # Calculate pairwise travel times
    for i, place_a in enumerate(places):
        for j, place_b in enumerate(places):
            if i >= j:
                continue  # Skip same place and already calculated pairs
            
            logger.debug(f"Calculating travel time: {place_a.name} -> {place_b.name}")
            
            try:
                travel_time = calculate_travel_time(
                    place_a.coordinates,
                    place_b.coordinates,
                    mode="pedestrian"
                )
                
                # Store both directions (symmetric)
                travel_times[(place_a.name, place_b.name)] = travel_time
                travel_times[(place_b.name, place_a.name)] = travel_time
                
                logger.debug(
                    f"Travel time {place_a.name} <-> {place_b.name}: "
                    f"{travel_time.duration_minutes:.1f} min, "
                    f"{travel_time.distance_km:.2f} km"
                )
                
            except Exception as e:
                logger.error(f"Error calculating travel time: {e}")
                # Use fallback estimate
                distance = calculate_haversine_distance(
                    place_a.coordinates,
                    place_b.coordinates
                )
                fallback_time = TravelTime(
                    duration_minutes=(distance / 5.0) * 60,
                    distance_km=distance,
                    mode="pedestrian"
                )
                travel_times[(place_a.name, place_b.name)] = fallback_time
                travel_times[(place_b.name, place_a.name)] = fallback_time
    
    state.travel_times = travel_times
    logger.info(f"Travel Time Agent: Calculated {len(travel_times)} travel time pairs")
    
    return state
