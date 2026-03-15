"""Planner Agent for orchestrating the planning process."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from .models import (
    PlannerState,
    Itinerary,
    ItineraryStop,
    Place
)

logger = logging.getLogger(__name__)


# Curated lunch spots near popular Rome areas with real coordinates
ROME_LUNCH_SPOTS = [
    {
        "name": "Roscioli Salumeria con Cucina",
        "coordinates": (41.8937, 12.4733),
        "area": "Campo de' Fiori",
        "cuisine": "Roman traditional, cured meats & cheese",
        "price_range": "€€-€€€",
        "hours": "12:30-16:00",
        "description": "Renowned Roman deli-restaurant near Campo de' Fiori. Famous for carbonara, cured meats, and an exceptional wine cellar."
    },
    {
        "name": "Trattoria Da Enzo al 29",
        "coordinates": (41.8882, 12.4740),
        "area": "Trastevere",
        "cuisine": "Classic Roman trattoria",
        "price_range": "€€",
        "hours": "12:00-15:00",
        "description": "Beloved Trastevere trattoria serving authentic Roman dishes. Try the cacio e pepe and artichokes. Expect a queue."
    },
    {
        "name": "Armando al Pantheon",
        "coordinates": (41.8984, 12.4756),
        "area": "Pantheon",
        "cuisine": "Traditional Roman",
        "price_range": "€€-€€€",
        "hours": "12:00-15:00",
        "description": "Family-run trattoria steps from the Pantheon since 1961. Classic Roman cuisine with seasonal specials."
    },
    {
        "name": "Picnic at Villa Borghese Gardens",
        "coordinates": (41.9122, 12.4854),
        "area": "Villa Borghese",
        "cuisine": "Picnic spot",
        "price_range": "€",
        "hours": "All day",
        "description": "Beautiful gardens perfect for a picnic. Grab supplies from a nearby alimentari and enjoy under the pine trees by the lake."
    },
    {
        "name": "Picnic at Orange Garden (Giardino degli Aranci)",
        "coordinates": (41.8833, 12.4797),
        "area": "Aventine Hill",
        "cuisine": "Picnic spot with panoramic view",
        "price_range": "€",
        "hours": "7:00-sunset",
        "description": "Stunning hilltop garden with orange trees and a panoramic terrace overlooking Rome. Perfect for a scenic lunch break."
    },
    {
        "name": "Trattoria Luzzi",
        "coordinates": (41.8893, 12.4952),
        "area": "Colosseum",
        "cuisine": "Roman pizza & pasta",
        "price_range": "€-€€",
        "hours": "12:00-15:30",
        "description": "Popular no-frills trattoria near the Colosseum. Great pizza, generous portions, and honest prices for the area."
    },
    {
        "name": "Picnic at Parco degli Acquedotti",
        "coordinates": (41.8558, 12.5558),
        "area": "Appia Antica",
        "cuisine": "Picnic among ancient aqueducts",
        "price_range": "€",
        "hours": "All day",
        "description": "Sprawling park with ancient Roman aqueducts. A peaceful, off-the-beaten-path spot for a picnic lunch."
    },
]


def _find_nearest_lunch_spot(
    prev_coords: Tuple[float, float],
    used_names: List[str]
) -> dict:
    """Find the nearest curated lunch spot to the given coordinates."""
    import math
    
    best = None
    best_dist = float("inf")
    
    for spot in ROME_LUNCH_SPOTS:
        if spot["name"] in used_names:
            continue
        lat1, lon1 = prev_coords
        lat2, lon2 = spot["coordinates"]
        # Simple Euclidean distance (good enough for same-city)
        dist = math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)
        if dist < best_dist:
            best_dist = dist
            best = spot
    
    return best or ROME_LUNCH_SPOTS[0]


def _try_rag_lunch_suggestion(
    prev_place_name: str,
    prev_coords: Tuple[float, float]
) -> Optional[dict]:
    """Try to get a lunch suggestion from the RAG knowledge base."""
    try:
        import streamlit as st
        rag_chain = st.session_state.get("rag_chain")
        if not rag_chain:
            return None
        
        query = (
            f"Recommend a good restaurant or trattoria near {prev_place_name} in Rome "
            f"for lunch. Include the cuisine style, price range, and opening hours."
        )
        response = rag_chain.invoke(query)
        
        if response and len(response) > 20:
            # We got a useful response - use it as the description
            # but still use curated coordinates for accuracy
            return {"rag_description": response}
    except Exception as e:
        logger.debug(f"RAG lunch suggestion failed: {e}")
    
    return None


def should_iterate(state: PlannerState) -> bool:
    """
    Determine if we should iterate to improve the itinerary.
    
    Args:
        state: Current planner state
        
    Returns:
        True if should iterate, False if done
    """
    # Don't iterate if already feasible
    if state.is_feasible:
        return False
    
    # Don't iterate if max iterations reached
    if state.iteration_count >= state.max_iterations:
        logger.warning(f"Max iterations ({state.max_iterations}) reached")
        return False
    
    # Don't iterate if no issues to fix
    if not state.feasibility_issues:
        return False
    
    return True


def reduce_stops(state: PlannerState) -> PlannerState:
    """
    Reduce number of stops to improve feasibility.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with fewer selected places
    """
    current_count = len(state.selected_places) if state.selected_places else len(state.candidate_places)
    
    # Reduce by 1-2 places
    new_count = max(2, current_count - 2)
    
    # Select top places by rating or order
    if state.selected_places:
        state.selected_places = state.selected_places[:new_count]
    else:
        state.selected_places = state.candidate_places[:new_count]
    
    logger.info(f"Reduced stops from {current_count} to {new_count}")
    state.explanation += f"\n🔄 Reduced stops from {current_count} to {new_count} to improve feasibility"
    
    return state


def remove_expensive_places(state: PlannerState) -> PlannerState:
    """
    Remove expensive places to reduce cost.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with cheaper places
    """
    places = state.selected_places if state.selected_places else state.candidate_places
    
    # Sort by ticket price (ascending)
    places_with_prices = []
    for place in places:
        ticket = state.ticket_info.get(place.name)
        price = ticket.price if ticket else 0.0
        places_with_prices.append((place, price))
    
    places_with_prices.sort(key=lambda x: x[1])
    
    # Keep cheaper half
    keep_count = max(2, len(places_with_prices) // 2)
    state.selected_places = [p for p, _ in places_with_prices[:keep_count]]
    
    logger.info(f"Removed expensive places, kept {keep_count} cheaper options")
    state.explanation += f"\n🔄 Removed expensive attractions to meet budget"
    
    return state


def remove_longest_visits(state: PlannerState) -> PlannerState:
    """
    Remove places with longest visit durations to save time.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with shorter visits
    """
    places = state.selected_places if state.selected_places else state.candidate_places
    
    # Sort by visit duration (ascending)
    places.sort(key=lambda p: p.visit_duration)
    
    # Keep shorter visits
    keep_count = max(2, len(places) - 1)
    state.selected_places = places[:keep_count]
    
    logger.info(f"Removed longest visits, kept {keep_count} places")
    state.explanation += f"\n🔄 Removed time-consuming stops to fit schedule"
    
    return state


def handle_feasibility_issues(state: PlannerState) -> PlannerState:
    """
    Try to fix feasibility issues by modifying the itinerary.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with attempted fixes
    """
    issues_str = " ".join(state.feasibility_issues).lower()
    
    # Handle distance issues
    if "distance" in issues_str or "walking" in issues_str:
        state = reduce_stops(state)
    
    # Handle time issues
    elif "time" in issues_str:
        state = remove_longest_visits(state)
    
    # Handle budget issues
    elif "cost" in issues_str or "budget" in issues_str:
        state = remove_expensive_places(state)
    
    # Handle opening hours issues
    elif "closed" in issues_str or "opening" in issues_str:
        # Remove closed places
        places = state.selected_places if state.selected_places else state.candidate_places
        open_places = [
            p for p in places
            if state.opening_hours.get(p.name, None) and state.opening_hours[p.name].is_open_today
        ]
        if open_places:
            state.selected_places = open_places
            logger.info(f"Removed closed places, kept {len(open_places)} open places")
            state.explanation += f"\n🔄 Removed closed attractions"
    
    # Default: reduce stops
    else:
        state = reduce_stops(state)
    
    # Clear issues for re-evaluation
    state.feasibility_issues = []
    state.iteration_count += 1
    
    return state


def build_itinerary(state: PlannerState) -> Itinerary:
    """
    Build final itinerary from optimized route.
    
    Args:
        state: Current planner state
        
    Returns:
        Complete Itinerary object
    """
    stops = []
    place_dict = {p.name: p for p in state.candidate_places}
    
    # Start time
    start_time = datetime.now()
    if state.user_preferences.start_time:
        start_time = start_time.replace(
            hour=state.user_preferences.start_time.hour,
            minute=state.user_preferences.start_time.minute,
            second=0,
            microsecond=0
        )
    
    current_time = start_time
    
    # Build stops
    for i, place_name in enumerate(state.optimized_route):
        # Handle lunch break
        if place_name == "LUNCH_BREAK":
            # Find a good lunch spot near the previous stop
            prev_coords = (41.9028, 12.4964)  # Rome center default
            prev_name = "Rome center"
            used_names = [s.place.name for s in stops]
            
            if stops:
                prev_coords = stops[-1].place.coordinates
                prev_name = stops[-1].place.name
            
            # Find nearest curated lunch spot
            lunch_spot = _find_nearest_lunch_spot(prev_coords, used_names)
            
            # Try to enrich with RAG suggestion
            rag_info = _try_rag_lunch_suggestion(prev_name, prev_coords)
            
            # Build description
            description = lunch_spot["description"]
            if rag_info and rag_info.get("rag_description"):
                description += f"\n\n💡 From our knowledge base:\n{rag_info['rag_description'][:300]}"
            
            lunch_place = Place(
                name=lunch_spot["name"],
                place_type="meal",
                coordinates=lunch_spot["coordinates"],
                visit_duration=60,
                description=description
            )
            
            notes = [
                f"🍽️ Cuisine: {lunch_spot['cuisine']}",
                f"💰 Price range: {lunch_spot['price_range']}",
                f"🕐 Hours: {lunch_spot['hours']}",
                f"📍 Area: {lunch_spot['area']}"
            ]
            
            stop = ItineraryStop(
                time=current_time,
                place=lunch_place,
                duration_minutes=60,
                notes=notes
            )
            stops.append(stop)
            current_time += timedelta(minutes=60)
            continue
        
        place = place_dict.get(place_name)
        if not place:
            logger.warning(f"Place not found: {place_name}")
            continue
        
        # Build notes
        notes = []
        
        # Add opening hours note
        hours = state.opening_hours.get(place_name)
        if hours and hours.opening_time and hours.closing_time:
            notes.append(
                f"Open: {hours.opening_time.strftime('%H:%M')} - "
                f"{hours.closing_time.strftime('%H:%M')}"
            )
            if hours.last_entry_time:
                notes.append(f"Last entry: {hours.last_entry_time.strftime('%H:%M')}")
        
        # Crowd level is displayed separately on the stop card, not in notes
        crowd = state.crowd_predictions.get(place_name)
        
        # Get ticket info (displayed separately, not in notes to avoid duplication)
        ticket = state.ticket_info.get(place_name)
        
        # Add travel note for next place
        if i < len(state.optimized_route) - 1:
            next_place = state.optimized_route[i + 1]
            if next_place != "LUNCH_BREAK":
                travel_key = (place_name, next_place)
                if travel_key in state.travel_times:
                    travel = state.travel_times[travel_key]
                    notes.append(
                        f"Next: {travel.duration_minutes:.0f} min walk "
                        f"({travel.distance_km:.1f} km)"
                    )
        
        # Create stop
        stop = ItineraryStop(
            time=current_time,
            place=place,
            duration_minutes=place.visit_duration,
            notes=notes,
            ticket_info=ticket,
            crowd_level=crowd
        )
        stops.append(stop)
        
        # Update time
        current_time += timedelta(minutes=place.visit_duration)
        
        # Add travel time to next place
        if i < len(state.optimized_route) - 1:
            next_place = state.optimized_route[i + 1]
            if next_place != "LUNCH_BREAK":
                travel_key = (place_name, next_place)
                if travel_key in state.travel_times:
                    current_time += timedelta(minutes=state.travel_times[travel_key].duration_minutes)
    
    # Calculate totals
    total_duration = int((current_time - start_time).total_seconds() / 60)
    
    total_distance = 0.0
    for i in range(len(state.optimized_route) - 1):
        if state.optimized_route[i] == "LUNCH_BREAK" or state.optimized_route[i + 1] == "LUNCH_BREAK":
            continue
        key = (state.optimized_route[i], state.optimized_route[i + 1])
        if key in state.travel_times:
            total_distance += state.travel_times[key].distance_km
    
    # Build itinerary
    itinerary = Itinerary(
        stops=stops,
        total_duration_minutes=total_duration,
        total_distance_km=total_distance,
        total_cost=state.total_cost or 0.0,
        feasibility_score=state.feasibility_score or 0.0,
        explanation=state.explanation
    )
    
    return itinerary


def planner_agent(state: PlannerState) -> PlannerState:
    """
    Planner Agent - orchestrates the planning process and handles iterations.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with final itinerary or iteration instructions
    """
    logger.info(f"Planner Agent: Iteration {state.iteration_count + 1}/{state.max_iterations}")
    
    # Check if we should iterate
    if should_iterate(state):
        logger.info("Itinerary not feasible, attempting to fix issues")
        state = handle_feasibility_issues(state)
        return state
    
    # Generate final itinerary
    if state.optimized_route:
        logger.info("Generating final itinerary")
        itinerary = build_itinerary(state)
        state.itinerary = itinerary
        
        # Add final summary to explanation
        if state.is_feasible:
            state.explanation += f"\n\n✅ Itinerary is feasible (score: {state.feasibility_score:.0f}/100)"
        else:
            state.explanation += f"\n\n⚠️ Itinerary has some issues (score: {state.feasibility_score:.0f}/100)"
            if state.feasibility_issues:
                state.explanation += "\nRemaining issues:"
                for issue in state.feasibility_issues[:3]:
                    state.explanation += f"\n  - {issue}"
        
        logger.info(f"Final itinerary: {len(itinerary.stops)} stops, {itinerary.total_duration_minutes / 60:.1f}h")
    else:
        logger.error("No optimized route available")
        state.explanation += "\n\n❌ Could not generate itinerary"
    
    return state
