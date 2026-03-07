"""
Router module for calculating routes between places.

This module provides functionality to calculate routes for different
transportation modes: pedestrian, car, and public transportation.
"""

from typing import List, Tuple, Optional, Literal
import requests
import logging
from time import sleep

logger = logging.getLogger(__name__)

# Transportation mode type
TransportMode = Literal["pedestrian", "car", "public_transport"]

# OSRM routing endpoints for different modes
OSRM_ENDPOINTS = {
    "pedestrian": "https://routing.openstreetmap.de/routed-foot/route/v1/foot",
    "car": "https://routing.openstreetmap.de/routed-car/route/v1/driving",
    # Public transport uses pedestrian as fallback (proper PT routing requires different API)
    "public_transport": "https://routing.openstreetmap.de/routed-foot/route/v1/foot"
}

# Route colors for different modes
ROUTE_COLORS = {
    "pedestrian": "blue",
    "car": "red",
    "public_transport": "green"
}


class Router:
    """
    Router for calculating routes between coordinates.
    
    Supports multiple transportation modes: pedestrian, car, and public transport.
    Uses OSRM (Open Source Routing Machine) for routing.
    """
    
    def __init__(self):
        """Initialize the Router."""
        logger.info("Router initialized with multi-mode support")
    
    def get_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        mode: TransportMode = "pedestrian",
        prefer_shortest: bool = True
    ) -> Optional[Tuple[List[Tuple[float, float]], float]]:
        """
        Get route coordinates between two points for specified transport mode.
        
        Args:
            start: Starting coordinates (latitude, longitude)
            end: Ending coordinates (latitude, longitude)
            mode: Transportation mode ("pedestrian", "car", or "public_transport")
            prefer_shortest: If True, prefer shortest distance; if False, prefer fastest route
        
        Returns:
            Tuple of (route coordinates, duration in seconds) or None if routing fails
        """
        try:
            # Get the appropriate endpoint for the mode
            base_url = OSRM_ENDPOINTS.get(mode, OSRM_ENDPOINTS["pedestrian"])
            
            # OSRM expects coordinates as longitude,latitude
            start_lon_lat = f"{start[1]},{start[0]}"
            end_lon_lat = f"{end[1]},{end[0]}"
            
            # Build request URL
            url = f"{base_url}/{start_lon_lat};{end_lon_lat}"
            params = {
                "overview": "full",
                "geometries": "geojson",
                "annotations": "true"
            }
            
            # Add preference for shortest distance
            if prefer_shortest:
                params["alternatives"] = "true"  # Get alternative routes
            
            logger.debug(f"Requesting {mode} route from {start} to {end} (prefer_shortest={prefer_shortest})")
            
            # Make request
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("code") != "Ok":
                logger.warning(f"OSRM routing failed: {data.get('message', 'Unknown error')}")
                return None
            
            # Extract route coordinates
            routes = data.get("routes", [])
            if not routes:
                logger.warning("No routes found in OSRM response")
                return None
            
            # If we requested alternatives and prefer shortest, pick the shortest route
            selected_route = routes[0]
            if prefer_shortest and len(routes) > 1:
                # Find route with shortest distance
                selected_route = min(routes, key=lambda r: r.get("distance", float('inf')))
                logger.debug(f"Selected shortest route: {selected_route.get('distance', 0):.0f}m")
            
            # Get geometry coordinates (they're in [lon, lat] format)
            geometry = selected_route.get("geometry", {})
            coordinates = geometry.get("coordinates", [])
            
            if not coordinates:
                logger.warning("No coordinates in route geometry")
                return None
            
            # Convert from [lon, lat] to (lat, lon) for Folium
            route_coords = [(coord[1], coord[0]) for coord in coordinates]
            
            distance = selected_route.get("distance", 0)
            duration = selected_route.get("duration", 0)
            logger.info(f"Got {mode} route with {len(route_coords)} points, distance: {distance:.0f}m, duration: {duration/60:.1f}min")
            
            return (route_coords, duration)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error requesting route from OSRM: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting route: {e}", exc_info=True)
            return None
    
    def auto_select_mode(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> TransportMode:
        """
        Automatically select the best transport mode based on walking time.
        
        Uses pedestrian mode if walking time < 30 minutes, otherwise public transport.
        
        Args:
            start: Starting coordinates (latitude, longitude)
            end: Ending coordinates (latitude, longitude)
        
        Returns:
            Recommended transport mode
        """
        # Try to get pedestrian route to check duration
        result = self.get_route(start, end, mode="pedestrian")
        
        if result:
            route_coords, duration = result
            walking_time_minutes = duration / 60
            
            if walking_time_minutes < 30:
                logger.info(f"Auto-selected pedestrian mode (walking time: {walking_time_minutes:.1f} min)")
                return "pedestrian"
            else:
                logger.info(f"Auto-selected public_transport mode (walking time: {walking_time_minutes:.1f} min)")
                return "public_transport"
        
        # Default to pedestrian if we can't determine
        logger.info("Auto-selected pedestrian mode (default)")
        return "pedestrian"
    
    def get_multi_point_route(
        self,
        waypoints: List[Tuple[float, float]],
        mode: Optional[TransportMode] = None,
        delay_between_requests: float = 0.5,
        prefer_shortest: bool = True
    ) -> List[Tuple[float, float]]:
        """
        Get route through multiple waypoints for specified transport mode.
        
        Args:
            waypoints: List of (latitude, longitude) tuples to visit in order
            mode: Transportation mode ("pedestrian", "car", "public_transport"), or None for auto-select
            delay_between_requests: Delay in seconds between API requests (default: 0.5)
            prefer_shortest: If True, prefer shortest distance routes (default: True)
        
        Returns:
            List of (latitude, longitude) tuples representing the complete route
        """
        if len(waypoints) < 2:
            logger.warning("Need at least 2 waypoints for a route")
            return waypoints
        
        # Auto-select mode if not specified
        if mode is None:
            mode = self.auto_select_mode(waypoints[0], waypoints[-1])
        
        logger.info(f"Calculating {mode} route through {len(waypoints)} waypoints (prefer_shortest={prefer_shortest})")
        
        complete_route = []
        
        # Get route between each consecutive pair of waypoints
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            
            result = self.get_route(start, end, mode=mode, prefer_shortest=prefer_shortest)
            
            if result:
                segment, duration = result
                # Add segment to complete route
                if i == 0:
                    # First segment: add all points
                    complete_route.extend(segment)
                else:
                    # Subsequent segments: skip first point to avoid duplicates
                    complete_route.extend(segment[1:])
            else:
                # Fallback to straight line if routing fails
                logger.warning(f"Routing failed for segment {i}, using straight line")
                if i == 0:
                    complete_route.append(start)
                complete_route.append(end)
            
            # Add delay to avoid rate limiting
            if i < len(waypoints) - 2:
                sleep(delay_between_requests)
        
        logger.info(f"Complete {mode} route has {len(complete_route)} points")
        return complete_route
