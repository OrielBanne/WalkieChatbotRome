"""Demo script for map integration with itinerary display."""

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


def create_sample_itinerary():
    """Create a sample itinerary for demonstration."""
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
            notes=["Arrive early to avoid crowds", "Bring water"],
            ticket_info=TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=True,
                price=16.0,
                skip_the_line_available=True,
                booking_url="https://example.com/colosseum"
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
            notes=["Explore the ruins", "Visit the Temple of Saturn"],
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
            notes=["Throw a coin for good luck"],
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
        explanation="Optimized route for ancient Rome highlights"
    )


def create_map_from_itinerary(itinerary):
    """Create an interactive map from an itinerary."""
    map_builder = MapBuilder()
    
    # Convert itinerary stops to markers with detailed popups
    markers = []
    for i, stop in enumerate(itinerary.stops, 1):
        # Create detailed popup content
        popup_html = f"<b>{i}. {stop.place.name}</b><br>"
        popup_html += f"<i>Time: {stop.time.strftime('%H:%M')}</i><br>"
        popup_html += f"<i>Duration: {stop.duration_minutes} min</i><br>"
        
        if stop.place.description:
            popup_html += f"<br>{stop.place.description}<br>"
        
        if stop.ticket_info and stop.ticket_info.ticket_required:
            popup_html += f"<br>💳 Ticket: €{stop.ticket_info.price:.2f}"
            if stop.ticket_info.reservation_required:
                popup_html += " (booking required)"
        
        if stop.crowd_level:
            crowd_emoji = {
                CrowdLevel.LOW: "🟢",
                CrowdLevel.MEDIUM: "🟡",
                CrowdLevel.HIGH: "🟠",
                CrowdLevel.VERY_HIGH: "🔴"
            }
            popup_html += f"<br>{crowd_emoji.get(stop.crowd_level, '⚪')} Crowds: {stop.crowd_level.value.replace('_', ' ').title()}"
        
        marker = PlaceMarker(
            name=f"{i}. {stop.place.name}",
            coordinates=stop.place.coordinates,
            place_type=stop.place.place_type,
            description=popup_html,
            icon="info-sign"
        )
        markers.append(marker)
    
    # Create map with numbered markers and route
    map_obj = map_builder.create_map_with_places(
        places=markers,
        add_route=True,
        transport_mode="pedestrian",
        show_center_marker=False,
        numbered_markers=True
    )
    
    return map_obj


if __name__ == "__main__":
    print("Creating sample itinerary...")
    itinerary = create_sample_itinerary()
    
    print(f"\nItinerary Summary:")
    print(f"  Stops: {len(itinerary.stops)}")
    print(f"  Duration: {itinerary.total_duration_minutes // 60}h {itinerary.total_duration_minutes % 60}m")
    print(f"  Distance: {itinerary.total_distance_km:.1f} km")
    print(f"  Cost: €{itinerary.total_cost:.2f}")
    print(f"  Feasibility: {itinerary.feasibility_score:.0f}/100")
    
    print("\nCreating map with route...")
    map_obj = create_map_from_itinerary(itinerary)
    
    print("\nSaving map to HTML...")
    map_obj.save("itinerary_map_demo.html")
    
    print("\n✅ Map saved to 'itinerary_map_demo.html'")
    print("Open this file in a web browser to view the interactive map!")
