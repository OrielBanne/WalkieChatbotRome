"""
Demo script to test the itinerary display component.

This script demonstrates how the itinerary display component works
by creating a sample itinerary and generating its text representation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, time
from src.agents.models import (
    Itinerary,
    ItineraryStop,
    Place,
    TicketInfo,
    CrowdLevel,
    UserPreferences
)
from src.components.itinerary_display import generate_text_itinerary


def create_sample_itinerary():
    """Create a sample itinerary for demonstration."""
    
    # Create places
    colosseum = Place(
        name="Colosseum",
        place_type="monument",
        coordinates=(41.8902, 12.4922),
        visit_duration=90,
        description="Ancient Roman amphitheater and iconic symbol of Rome",
        rating=4.8
    )
    
    roman_forum = Place(
        name="Roman Forum",
        place_type="monument",
        coordinates=(41.8925, 12.4853),
        visit_duration=60,
        description="Ancient Roman marketplace and center of political life",
        rating=4.7
    )
    
    trevi_fountain = Place(
        name="Trevi Fountain",
        place_type="monument",
        coordinates=(41.9009, 12.4833),
        visit_duration=30,
        description="Baroque fountain and one of Rome's most famous landmarks",
        rating=4.9
    )
    
    # Create ticket info
    colosseum_ticket = TicketInfo(
        place_name="Colosseum",
        ticket_required=True,
        reservation_required=True,
        price=16.0,
        skip_the_line_available=True,
        booking_url="https://www.coopculture.it/en/colosseo-e-shop.cfm"
    )
    
    forum_ticket = TicketInfo(
        place_name="Roman Forum",
        ticket_required=True,
        reservation_required=False,
        price=12.0,
        skip_the_line_available=False
    )
    
    fountain_ticket = TicketInfo(
        place_name="Trevi Fountain",
        ticket_required=False,
        reservation_required=False,
        price=0.0
    )
    
    # Create stops
    stop1 = ItineraryStop(
        time=datetime(2024, 6, 15, 9, 0),
        place=colosseum,
        duration_minutes=90,
        notes=[
            "Arrive early to avoid crowds",
            "Bring water and sun protection",
            "Audio guide recommended"
        ],
        ticket_info=colosseum_ticket,
        crowd_level=CrowdLevel.HIGH
    )
    
    stop2 = ItineraryStop(
        time=datetime(2024, 6, 15, 10, 45),
        place=roman_forum,
        duration_minutes=60,
        notes=[
            "Walking distance from Colosseum (5 minutes)",
            "Wear comfortable shoes",
            "Combined ticket with Colosseum available"
        ],
        ticket_info=forum_ticket,
        crowd_level=CrowdLevel.MEDIUM
    )
    
    stop3 = ItineraryStop(
        time=datetime(2024, 6, 15, 12, 30),
        place=trevi_fountain,
        duration_minutes=30,
        notes=[
            "Throw a coin for good luck",
            "Watch out for pickpockets",
            "Best photos from the steps"
        ],
        ticket_info=fountain_ticket,
        crowd_level=CrowdLevel.VERY_HIGH
    )
    
    # Create itinerary
    itinerary = Itinerary(
        stops=[stop1, stop2, stop3],
        total_duration_minutes=240,
        total_distance_km=5.2,
        total_cost=45.50,
        feasibility_score=85.0,
        explanation=(
            "Optimized route for ancient Rome exploration. "
            "Route minimizes walking distance while respecting opening hours. "
            "Morning start recommended to avoid peak crowds at major attractions. "
            "Total walking time: approximately 45 minutes between stops."
        )
    )
    
    return itinerary


def main():
    """Run the demo."""
    print("=" * 70)
    print("ITINERARY DISPLAY COMPONENT DEMO")
    print("=" * 70)
    print()
    
    # Create sample itinerary
    print("Creating sample itinerary...")
    itinerary = create_sample_itinerary()
    
    print(f"✓ Created itinerary with {len(itinerary.stops)} stops")
    print(f"✓ Total duration: {itinerary.total_duration_minutes // 60}h {itinerary.total_duration_minutes % 60}m")
    print(f"✓ Total distance: {itinerary.total_distance_km:.1f} km")
    print(f"✓ Total cost: €{itinerary.total_cost:.2f}")
    print(f"✓ Feasibility score: {itinerary.feasibility_score:.0f}/100")
    print()
    
    # Generate text version
    print("Generating text itinerary...")
    text_itinerary = generate_text_itinerary(itinerary)
    
    print("✓ Text itinerary generated")
    print()
    
    # Display the text itinerary
    print(text_itinerary)
    
    # Save to file
    output_file = "sample_itinerary.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text_itinerary)
    
    print()
    print(f"✓ Saved to {output_file}")
    print()
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
