"""
Map Builder module for creating interactive maps with Folium.

This module provides functionality to create maps with markers, routes,
and custom styling for the Rome Places Chatbot.
"""

from typing import List, Tuple, Optional
import folium
from folium import Icon, PolyLine, Popup
import logging

from src.models import PlaceMarker
from src.config import ROME_CENTER, DEFAULT_MAP_ZOOM
from src.router import Router, ROUTE_COLORS

logger = logging.getLogger(__name__)

# Custom marker colors for different place types
PLACE_TYPE_COLORS = {
    "landmark": "red",
    "restaurant": "orange",
    "attraction": "blue",
    "museum": "purple",
    "church": "pink",
    "park": "green",
    "hotel": "lightblue",
    "default": "gray"
}

# Custom marker icons for different place types
PLACE_TYPE_ICONS = {
    "landmark": "star",
    "restaurant": "cutlery",
    "attraction": "camera",
    "museum": "university",
    "church": "home",
    "park": "tree",
    "hotel": "bed",
    "default": "info-sign"
}


class MapBuilder:
    """
    Builder for creating interactive Folium maps with markers and routes.
    
    Provides methods to create base maps, add markers for places,
    add routes between places, and render maps to Streamlit.
    """
    
    def __init__(self):
        """Initialize the MapBuilder."""
        self.router = Router()
        logger.info("MapBuilder initialized with Router")
    
    def create_base_map(
        self, 
        center: Optional[Tuple[float, float]] = None, 
        zoom: int = None
    ) -> folium.Map:
        """
        Create a base Folium map centered on Rome.
        
        Args:
            center: Optional (latitude, longitude) tuple for map center.
                   Defaults to Rome city center from config.
            zoom: Zoom level for the map (uses config default if None)
        
        Returns:
            A Folium Map object
        """
        if center is None:
            center = ROME_CENTER
        
        if zoom is None:
            zoom = DEFAULT_MAP_ZOOM
        
        logger.info("Creating base map centered at %s with zoom %d", center, zoom)
        
        # Create map with OpenStreetMap tiles
        map_obj = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles="OpenStreetMap",
            control_scale=True
        )
        
        return map_obj
    
    def add_markers(
        self, 
        map_obj: folium.Map, 
        places: List[PlaceMarker]
    ) -> None:
        """
        Add markers to the map for each place.
        
        Args:
            map_obj: The Folium map to add markers to
            places: List of PlaceMarker objects to add to the map
        """
        if not places:
            logger.warning("No places provided to add_markers")
            return
        
        logger.info("Adding %d markers to map", len(places))
        
        for place in places:
            # Get color and icon for this place type
            color = PLACE_TYPE_COLORS.get(place.place_type, PLACE_TYPE_COLORS["default"])
            icon_name = PLACE_TYPE_ICONS.get(place.place_type, PLACE_TYPE_ICONS["default"])
            
            # Create popup content
            popup_html = f"<b>{place.name}</b>"
            if place.description:
                popup_html += f"<br>{place.description}"
            popup_html += f"<br><i>Type: {place.place_type}</i>"
            
            # Create marker
            folium.Marker(
                location=place.coordinates,
                popup=Popup(popup_html, max_width=300),
                tooltip=place.name,
                icon=Icon(color=color, icon=icon_name, prefix="fa")
            ).add_to(map_obj)
            
            logger.debug("Added marker for '%s' at %s", place.name, place.coordinates)
    
    def add_route(
        self, 
        map_obj: folium.Map, 
        coordinates: List[Tuple[float, float]],
        color: str = "blue",
        weight: int = 3,
        opacity: float = 0.7
    ) -> None:
        """
        Add a route (polyline) connecting multiple coordinates.
        
        Args:
            map_obj: The Folium map to add the route to
            coordinates: List of (latitude, longitude) tuples defining the route
            color: Color of the route line (default: "blue")
            weight: Width of the route line (default: 3)
            opacity: Opacity of the route line (default: 0.7)
        """
        if not coordinates or len(coordinates) < 2:
            logger.warning("Need at least 2 coordinates to create a route")
            return
        
        logger.info("Adding route with %d points", len(coordinates))
        
        # Create polyline
        PolyLine(
            locations=coordinates,
            color=color,
            weight=weight,
            opacity=opacity,
            popup="Route between places"
        ).add_to(map_obj)
        
        logger.debug("Route added with %d waypoints", len(coordinates))
    
    def render_to_streamlit(self, map_obj: folium.Map) -> str:
        """
        Render the Folium map to HTML for Streamlit display.
        
        Args:
            map_obj: The Folium map to render
        
        Returns:
            HTML string representation of the map
        """
        logger.info("Rendering map to HTML for Streamlit")
        
        # Convert map to HTML
        html = map_obj._repr_html_()
        
        return html
    
    def create_map_with_places(
        self,
        places: List[PlaceMarker],
        center: Optional[Tuple[float, float]] = None,
        zoom: int = None,
        add_route: bool = False,
        transport_mode: Optional[str] = None,
        show_center_marker: bool = True
    ) -> folium.Map:
        """
        Convenience method to create a complete map with places and optional route.
        
        Args:
            places: List of PlaceMarker objects to display
            center: Optional map center (defaults to Rome or first place)
            zoom: Zoom level (uses config default if None)
            add_route: Whether to add a route connecting all places (default: False)
            transport_mode: Transportation mode - "pedestrian", "car", "public_transport", or None for auto (default: None)
            show_center_marker: Whether to show a marker at the map center (default: True)
        
        Returns:
            A Folium Map object with markers and optional route
        """
        if zoom is None:
            zoom = DEFAULT_MAP_ZOOM
        
        if not places:
            logger.warning("No places provided to create_map_with_places")
            return self.create_base_map(center, zoom)
        
        # Determine map center
        if center is None:
            # Calculate center from places
            if len(places) == 1:
                map_center = places[0].coordinates
            else:
                # Use Rome center as default
                map_center = ROME_CENTER
        else:
            map_center = center
        
        # Create base map
        map_obj = self.create_base_map(map_center, zoom)
        
        # Add center marker if requested and center is Rome center
        if show_center_marker and map_center == ROME_CENTER:
            folium.Marker(
                location=map_center,
                popup=Popup("<b>Rome City Center</b>", max_width=200),
                tooltip="Rome Center",
                icon=Icon(color="lightblue", icon="info-sign", prefix="fa")
            ).add_to(map_obj)
        
        # Add place markers
        self.add_markers(map_obj, places)
        
        # Add route if requested and multiple places exist
        # Route only connects the actual places, not the center marker
        if add_route and len(places) > 1:
            waypoints = [place.coordinates for place in places]
            
            # Get route for the specified transport mode (or auto-select)
            logger.info(f"Calculating route through places (mode: {transport_mode or 'auto'})")
            route_coords = self.router.get_multi_point_route(waypoints, mode=transport_mode)
            
            # Determine actual mode used (for color)
            actual_mode = transport_mode if transport_mode else "pedestrian"
            route_color = ROUTE_COLORS.get(actual_mode, "blue")
            
            if route_coords and len(route_coords) > 1:
                # Use the calculated route
                self.add_route(map_obj, route_coords, color=route_color, weight=4, opacity=0.8)
                logger.info(f"Added route with {len(route_coords)} points")
            else:
                # Fallback to straight lines if routing fails
                logger.warning("Route calculation failed, using straight lines")
                self.add_route(map_obj, waypoints, color=route_color, weight=3, opacity=0.7)
        
        logger.info("Created map with %d places", len(places))
        
        return map_obj
