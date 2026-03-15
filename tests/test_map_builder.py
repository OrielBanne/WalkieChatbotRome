"""
Tests for the MapBuilder module.

This module contains both property-based tests and unit tests for the
map building functionality.
"""

import pytest
from hypothesis import given, strategies as st, settings
import folium
from src.map_builder import MapBuilder, ROME_CENTER, PLACE_TYPE_COLORS
from src.models import PlaceMarker


# Helper strategies for generating test data
@st.composite
def place_marker_strategy(draw):
    """Generate a random PlaceMarker for testing."""
    name = draw(st.text(min_size=1, max_size=50))
    # Generate coordinates near Rome
    lat = draw(st.floats(min_value=41.8, max_value=41.95))
    lon = draw(st.floats(min_value=12.4, max_value=12.6))
    place_type = draw(st.sampled_from(["landmark", "restaurant", "attraction", "museum", "park"]))
    description = draw(st.one_of(st.none(), st.text(min_size=1, max_size=100)))
    icon = draw(st.text(min_size=1, max_size=20))
    
    return PlaceMarker(
        name=name,
        coordinates=(lat, lon),
        place_type=place_type,
        description=description,
        icon=icon
    )


# Property-Based Tests

# Feature: rome-places-chatbot, Property 15: Map Marker Correspondence
@given(places=st.lists(place_marker_strategy(), min_size=1, max_size=10, unique_by=lambda p: p.name))
@settings(max_examples=20)
def test_map_marker_correspondence(places):
    """
    **Validates: Property 15 - Map Marker Correspondence**
    
    For any list of place mentions with valid coordinates, the generated
    Folium map should contain exactly one marker for each unique place.
    """
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    # Add markers
    builder.add_markers(map_obj, places)
    
    # Count markers in the map
    # Folium stores markers as children of the map
    markers = [child for child in map_obj._children.values() 
               if isinstance(child, folium.Marker)]
    
    # Should have exactly one marker per place
    assert len(markers) == len(places), \
        f"Expected {len(places)} markers but found {len(markers)}"
    
    # Verify each marker has correct coordinates
    place_coords = {place.coordinates for place in places}
    marker_coords = {tuple(marker.location) for marker in markers}
    
    assert place_coords == marker_coords, \
        "Marker coordinates don't match place coordinates"


# Unit Tests

def test_create_base_map_default():
    """Test creating a base map with default parameters."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    assert isinstance(map_obj, folium.Map)
    assert map_obj.location == list(ROME_CENTER)
    assert map_obj.options['zoom'] == 13


def test_create_base_map_custom_center():
    """Test creating a base map with custom center."""
    builder = MapBuilder()
    custom_center = (41.9, 12.5)
    map_obj = builder.create_base_map(center=custom_center, zoom=15)
    
    assert isinstance(map_obj, folium.Map)
    assert map_obj.location == list(custom_center)
    assert map_obj.options['zoom'] == 15


def test_add_markers_single_place():
    """Test adding a single marker to the map."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    place = PlaceMarker(
        name="Colosseum",
        coordinates=(41.8902, 12.4922),
        place_type="landmark",
        description="Ancient Roman amphitheater",
        icon="star"
    )
    
    builder.add_markers(map_obj, [place])
    
    # Check that marker was added
    markers = [child for child in map_obj._children.values() 
               if isinstance(child, folium.Marker)]
    assert len(markers) == 1
    assert markers[0].location == list(place.coordinates)


def test_add_markers_multiple_places():
    """Test adding multiple markers to the map."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    places = [
        PlaceMarker("Colosseum", (41.8902, 12.4922), "landmark", "Ancient amphitheater", "star"),
        PlaceMarker("Trevi Fountain", (41.9009, 12.4833), "landmark", "Famous fountain", "star"),
        PlaceMarker("Pantheon", (41.8986, 12.4768), "landmark", "Ancient temple", "star")
    ]
    
    builder.add_markers(map_obj, places)
    
    # Check that all markers were added
    markers = [child for child in map_obj._children.values() 
               if isinstance(child, folium.Marker)]
    assert len(markers) == 3


def test_add_markers_empty_list():
    """Test adding markers with empty list."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    builder.add_markers(map_obj, [])
    
    # Should have no markers
    markers = [child for child in map_obj._children.values() 
               if isinstance(child, folium.Marker)]
    assert len(markers) == 0


def test_add_route_multiple_points():
    """Test adding a route with multiple points."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    coordinates = [
        (41.8902, 12.4922),  # Colosseum
        (41.9009, 12.4833),  # Trevi Fountain
        (41.8986, 12.4768)   # Pantheon
    ]
    
    builder.add_route(map_obj, coordinates)
    
    # Check that polyline was added
    polylines = [child for child in map_obj._children.values() 
                 if isinstance(child, folium.PolyLine)]
    assert len(polylines) == 1
    assert len(polylines[0].locations) == 3


def test_add_route_two_points():
    """Test adding a route with exactly two points."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    coordinates = [
        (41.8902, 12.4922),  # Colosseum
        (41.9009, 12.4833)   # Trevi Fountain
    ]
    
    builder.add_route(map_obj, coordinates)
    
    # Check that polyline was added
    polylines = [child for child in map_obj._children.values() 
                 if isinstance(child, folium.PolyLine)]
    assert len(polylines) == 1


def test_add_route_single_point():
    """Test that adding a route with single point does nothing."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    coordinates = [(41.8902, 12.4922)]
    
    builder.add_route(map_obj, coordinates)
    
    # Should have no polylines
    polylines = [child for child in map_obj._children.values() 
                 if isinstance(child, folium.PolyLine)]
    assert len(polylines) == 0


def test_add_route_empty_list():
    """Test that adding a route with empty list does nothing."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    builder.add_route(map_obj, [])
    
    # Should have no polylines
    polylines = [child for child in map_obj._children.values() 
                 if isinstance(child, folium.PolyLine)]
    assert len(polylines) == 0


def test_render_to_streamlit():
    """Test rendering map to HTML."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    html = builder.render_to_streamlit(map_obj)
    
    assert isinstance(html, str)
    assert len(html) > 0
    # Should contain HTML tags
    assert "<" in html and ">" in html


def test_create_map_with_places():
    """Test convenience method to create map with places."""
    builder = MapBuilder()
    
    places = [
        PlaceMarker("Colosseum", (41.8902, 12.4922), "landmark", "Ancient amphitheater", "star"),
        PlaceMarker("Trevi Fountain", (41.9009, 12.4833), "landmark", "Famous fountain", "star")
    ]
    
    map_obj = builder.create_map_with_places(places, show_center_marker=False)
    
    assert isinstance(map_obj, folium.Map)
    
    # Check markers were added
    markers = [child for child in map_obj._children.values() 
               if isinstance(child, folium.Marker)]
    assert len(markers) == 2


def test_create_map_with_places_and_route():
    """Test creating map with places and route."""
    builder = MapBuilder()
    
    places = [
        PlaceMarker("Colosseum", (41.8902, 12.4922), "landmark", "Ancient amphitheater", "star"),
        PlaceMarker("Trevi Fountain", (41.9009, 12.4833), "landmark", "Famous fountain", "star"),
        PlaceMarker("Pantheon", (41.8986, 12.4768), "landmark", "Ancient temple", "star")
    ]
    
    map_obj = builder.create_map_with_places(places, add_route=True, show_center_marker=False)
    
    assert isinstance(map_obj, folium.Map)
    
    # Check markers were added
    markers = [child for child in map_obj._children.values() 
               if isinstance(child, folium.Marker)]
    assert len(markers) == 3
    
    # Check route was added
    polylines = [child for child in map_obj._children.values() 
                 if isinstance(child, folium.PolyLine)]
    assert len(polylines) == 1


def test_create_map_with_empty_places():
    """Test creating map with empty places list."""
    builder = MapBuilder()
    
    map_obj = builder.create_map_with_places([])
    
    assert isinstance(map_obj, folium.Map)
    
    # Should have no markers
    markers = [child for child in map_obj._children.values() 
               if isinstance(child, folium.Marker)]
    assert len(markers) == 0


def test_marker_popup_content():
    """Test that markers have proper popup content."""
    builder = MapBuilder()
    map_obj = builder.create_base_map()
    
    place = PlaceMarker(
        name="Test Place",
        coordinates=(41.9, 12.5),
        place_type="restaurant",
        description="A test restaurant",
        icon="cutlery"
    )
    
    builder.add_markers(map_obj, [place])
    
    markers = [child for child in map_obj._children.values() 
               if isinstance(child, folium.Marker)]
    assert len(markers) == 1
    
    # Check that marker has children (popup is added as a child)
    marker = markers[0]
    popups = [child for child in marker._children.values() 
              if isinstance(child, folium.Popup)]
    assert len(popups) > 0
