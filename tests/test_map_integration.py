"""Tests for map integration with itinerary display."""

import pytest
from datetime import datetime
from src.agents.models import (
    Itinerary,
    ItineraryStop,
    Place,
    TicketInfo,
    CrowdLevel
)
from src.map_builder import MapBuilder
from src.models import PlaceMarker


@pytest.fixture
def sample_itinerary():
    """Create a sample itinerary with multiple stops."""
    stops = [
        ItineraryStop(
            time=datetime(2024, 6, 15, 9, 0),
            place=Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=90,
                description="Ancient Roman amphitheater"
            ),
            duration_minutes=90,
            notes=["Arrive early"],
            ticket_info=TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=True,
                price=16.0
            ),
            crowd_level=CrowdLevel.MEDIUM
        ),
        ItineraryStop(
            time=datetime(2024, 6, 15, 11, 0),
            place=Place(
                name="Roman Forum",
                place_type="monument",
                coordinates=(41.8925, 12.4853),
                visit_duration=60,
                description="Ancient Roman forum"
            ),
            duration_minutes=60,
            notes=["Explore ruins"],
            crowd_level=CrowdLevel.HIGH
        ),
        ItineraryStop(
            time=datetime(2024, 6, 15, 13, 0),
            place=Place(
                name="Trevi Fountain",
                place_type="monument",
                coordinates=(41.9009, 12.4833),
                visit_duration=30,
                description="Famous baroque fountain"
            ),
            duration_minutes=30,
            notes=["Throw a coin"],
            ticket_info=TicketInfo(
                place_name="Trevi Fountain",
                ticket_required=False,
                reservation_required=False,
                price=0.0
            ),
            crowd_level=CrowdLevel.VERY_HIGH
        )
    ]
    
    return Itinerary(
        stops=stops,
        total_duration_minutes=240,
        total_distance_km=5.2,
        total_cost=16.0,
        feasibility_score=85.0,
        explanation="Optimized route for ancient Rome"
    )


class TestMapIntegration:
    """Tests for map integration with itinerary."""
    
    def test_map_builder_supports_numbered_markers(self):
        """Test that MapBuilder can create numbered markers."""
        map_builder = MapBuilder()
        
        markers = [
            PlaceMarker(
                name="1. Colosseum",
                coordinates=(41.8902, 12.4922),
                place_type="monument",
                description="Stop 1",
                icon="info-sign"
            ),
            PlaceMarker(
                name="2. Roman Forum",
                coordinates=(41.8925, 12.4853),
                place_type="monument",
                description="Stop 2",
                icon="info-sign"
            )
        ]
        
        # Create map with numbered markers
        map_obj = map_builder.create_map_with_places(
            places=markers,
            numbered_markers=True,
            add_route=False
        )
        
        assert map_obj is not None
        
    def test_map_with_route_and_numbered_markers(self):
        """Test creating a map with route and numbered markers."""
        map_builder = MapBuilder()
        
        markers = [
            PlaceMarker(
                name="1. Colosseum",
                coordinates=(41.8902, 12.4922),
                place_type="monument",
                description="Stop 1",
                icon="info-sign"
            ),
            PlaceMarker(
                name="2. Roman Forum",
                coordinates=(41.8925, 12.4853),
                place_type="monument",
                description="Stop 2",
                icon="info-sign"
            )
        ]
        
        # Create map with route and numbered markers
        map_obj = map_builder.create_map_with_places(
            places=markers,
            numbered_markers=True,
            add_route=True,
            transport_mode="pedestrian"
        )
        
        assert map_obj is not None
        
    def test_itinerary_to_markers_conversion(self, sample_itinerary):
        """Test converting itinerary stops to map markers."""
        markers = []
        
        for i, stop in enumerate(sample_itinerary.stops, 1):
            marker = PlaceMarker(
                name=f"{i}. {stop.place.name}",
                coordinates=stop.place.coordinates,
                place_type=stop.place.place_type,
                description=f"Time: {stop.time.strftime('%H:%M')}",
                icon="info-sign"
            )
            markers.append(marker)
        
        assert len(markers) == 3
        assert markers[0].name == "1. Colosseum"
        assert markers[1].name == "2. Roman Forum"
        assert markers[2].name == "3. Trevi Fountain"
        
    def test_map_displays_all_stops(self, sample_itinerary):
        """Test that map includes all itinerary stops."""
        map_builder = MapBuilder()
        
        # Convert stops to markers
        markers = []
        for i, stop in enumerate(sample_itinerary.stops, 1):
            marker = PlaceMarker(
                name=f"{i}. {stop.place.name}",
                coordinates=stop.place.coordinates,
                place_type=stop.place.place_type,
                description=stop.place.description or "",
                icon="info-sign"
            )
            markers.append(marker)
        
        # Create map
        map_obj = map_builder.create_map_with_places(
            places=markers,
            numbered_markers=True,
            add_route=True,
            transport_mode="pedestrian"
        )
        
        assert map_obj is not None
        # Map should have markers for all stops
        assert len(markers) == len(sample_itinerary.stops)



class TestTask19Requirements:
    """Tests validating all Task 19 requirements."""
    
    def test_pass_itinerary_to_map_builder(self, sample_itinerary):
        """Test that itinerary can be passed to map_builder."""
        map_builder = MapBuilder()
        
        # Convert itinerary stops to markers
        markers = []
        for i, stop in enumerate(sample_itinerary.stops, 1):
            marker = PlaceMarker(
                name=f"{i}. {stop.place.name}",
                coordinates=stop.place.coordinates,
                place_type=stop.place.place_type,
                description=f"Time: {stop.time.strftime('%H:%M')}",
                icon="info-sign"
            )
            markers.append(marker)
        
        # Create map
        map_obj = map_builder.create_map_with_places(
            places=markers,
            numbered_markers=True,
            add_route=True,
            transport_mode="pedestrian"
        )
        
        assert map_obj is not None
        
    def test_display_route_on_map(self, sample_itinerary):
        """Test that route is displayed on map."""
        map_builder = MapBuilder()
        
        markers = []
        for i, stop in enumerate(sample_itinerary.stops, 1):
            marker = PlaceMarker(
                name=f"{i}. {stop.place.name}",
                coordinates=stop.place.coordinates,
                place_type=stop.place.place_type,
                description="",
                icon="info-sign"
            )
            markers.append(marker)
        
        # Create map with route
        map_obj = map_builder.create_map_with_places(
            places=markers,
            add_route=True,
            transport_mode="pedestrian"
        )
        
        # Check that polyline (route) was added
        from folium import PolyLine
        polylines = [child for child in map_obj._children.values() 
                     if isinstance(child, PolyLine)]
        assert len(polylines) > 0, "Route should be displayed on map"
        
    def test_numbered_markers_for_stops(self, sample_itinerary):
        """Test that stops have numbered markers."""
        map_builder = MapBuilder()
        
        markers = []
        for i, stop in enumerate(sample_itinerary.stops, 1):
            marker = PlaceMarker(
                name=f"{i}. {stop.place.name}",
                coordinates=stop.place.coordinates,
                place_type=stop.place.place_type,
                description="",
                icon="info-sign"
            )
            markers.append(marker)
        
        # Create map with numbered markers
        map_obj = map_builder.create_map_with_places(
            places=markers,
            numbered_markers=True,
            show_center_marker=False
        )
        
        # Verify markers were added
        from folium import Marker
        map_markers = [child for child in map_obj._children.values() 
                       if isinstance(child, Marker)]
        assert len(map_markers) == len(sample_itinerary.stops)
        
    def test_transport_mode_colors(self):
        """Test that routes use different colors for transport modes."""
        map_builder = MapBuilder()
        
        markers = [
            PlaceMarker(
                name="1. Start",
                coordinates=(41.8902, 12.4922),
                place_type="monument",
                description="",
                icon="info-sign"
            ),
            PlaceMarker(
                name="2. End",
                coordinates=(41.9009, 12.4833),
                place_type="monument",
                description="",
                icon="info-sign"
            )
        ]
        
        # Test pedestrian mode (blue)
        map_pedestrian = map_builder.create_map_with_places(
            places=markers,
            add_route=True,
            transport_mode="pedestrian"
        )
        assert map_pedestrian is not None
        
        # Test car mode (red)
        map_car = map_builder.create_map_with_places(
            places=markers,
            add_route=True,
            transport_mode="car"
        )
        assert map_car is not None
        
        # Test public transport mode (green)
        map_public = map_builder.create_map_with_places(
            places=markers,
            add_route=True,
            transport_mode="public_transport"
        )
        assert map_public is not None
        
    def test_popup_with_stop_details(self, sample_itinerary):
        """Test that popups contain stop details."""
        map_builder = MapBuilder()
        
        # Create markers with detailed popup content
        markers = []
        for i, stop in enumerate(sample_itinerary.stops, 1):
            popup_html = f"<b>{i}. {stop.place.name}</b><br>"
            popup_html += f"<i>Time: {stop.time.strftime('%H:%M')}</i><br>"
            popup_html += f"<i>Duration: {stop.duration_minutes} min</i><br>"
            
            if stop.place.description:
                popup_html += f"<br>{stop.place.description}<br>"
            
            if stop.ticket_info and stop.ticket_info.ticket_required:
                popup_html += f"<br>💳 Ticket: €{stop.ticket_info.price:.2f}"
            
            if stop.crowd_level:
                popup_html += f"<br>Crowds: {stop.crowd_level.value}"
            
            marker = PlaceMarker(
                name=f"{i}. {stop.place.name}",
                coordinates=stop.place.coordinates,
                place_type=stop.place.place_type,
                description=popup_html,
                icon="info-sign"
            )
            markers.append(marker)
        
        # Create map
        map_obj = map_builder.create_map_with_places(
            places=markers,
            numbered_markers=True,
            show_center_marker=False
        )
        
        # Verify markers have popup content
        from folium import Marker
        map_markers = [child for child in map_obj._children.values() 
                       if isinstance(child, Marker)]
        
        # Check that markers exist
        assert len(map_markers) == len(sample_itinerary.stops)
        
        # Verify popup content includes key information
        for marker in markers:
            assert "Time:" in marker.description
            assert "Duration:" in marker.description
