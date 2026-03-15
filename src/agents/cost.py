"""Cost Agent for calculating itinerary costs."""

import logging
from typing import Dict, Tuple

from .models import PlannerState, TicketInfo, TravelTime

logger = logging.getLogger(__name__)


def calculate_ticket_costs(
    route: list,
    ticket_info: Dict[str, TicketInfo]
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate total ticket costs for the route.
    
    Args:
        route: List of place names
        ticket_info: Dictionary of ticket information
        
    Returns:
        Tuple of (total_cost, breakdown_dict)
    """
    total = 0.0
    breakdown = {}
    
    for place_name in route:
        if place_name == "LUNCH_BREAK":
            continue
        
        info = ticket_info.get(place_name)
        if info and info.ticket_required:
            total += info.price
            breakdown[place_name] = info.price
    
    return total, breakdown


def estimate_meal_costs(route: list, visit_durations: Dict[str, int]) -> Tuple[float, int]:
    """
    Estimate meal costs based on itinerary duration.
    
    Args:
        route: List of place names
        visit_durations: Dictionary of visit durations in minutes
        
    Returns:
        Tuple of (total_meal_cost, number_of_meals)
    """
    # Check if LUNCH_BREAK is in route
    has_lunch = "LUNCH_BREAK" in route
    
    # Calculate total duration
    total_duration = sum(
        visit_durations.get(place, 0)
        for place in route
        if place != "LUNCH_BREAK"
    )
    
    # Estimate number of meals
    num_meals = 0
    if has_lunch or total_duration > 4 * 60:  # More than 4 hours
        num_meals += 1  # Lunch
    
    if total_duration > 8 * 60:  # More than 8 hours
        num_meals += 1  # Dinner or snack
    
    # Average meal cost in Rome
    avg_meal_cost = 15.0  # EUR
    total_cost = num_meals * avg_meal_cost
    
    return total_cost, num_meals


def estimate_transport_costs(travel_times: Dict[Tuple[str, str], TravelTime]) -> float:
    """
    Estimate transport costs based on travel modes.
    
    Args:
        travel_times: Dictionary of travel times
        
    Returns:
        Estimated transport cost in EUR
    """
    # Check if any travel requires public transport (metro or bus)
    uses_public_transport = any(
        tt.mode in ["metro", "bus"]
        for tt in travel_times.values()
    )
    
    if uses_public_transport:
        # Day pass for Rome public transport
        return 7.0
    else:
        # Walking only - no cost
        return 0.0


def calculate_total_cost(
    route: list,
    ticket_info: Dict[str, TicketInfo],
    travel_times: Dict[Tuple[str, str], TravelTime],
    visit_durations: Dict[str, int]
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate total itinerary cost with breakdown.
    
    Args:
        route: List of place names
        ticket_info: Dictionary of ticket information
        travel_times: Dictionary of travel times
        visit_durations: Dictionary of visit durations
        
    Returns:
        Tuple of (total_cost, breakdown_dict)
    """
    breakdown = {}
    
    # Ticket costs
    ticket_cost, ticket_breakdown = calculate_ticket_costs(route, ticket_info)
    breakdown["tickets"] = ticket_cost
    breakdown["ticket_details"] = ticket_breakdown
    
    # Meal costs
    meal_cost, num_meals = estimate_meal_costs(route, visit_durations)
    breakdown["meals"] = meal_cost
    breakdown["num_meals"] = num_meals
    
    # Transport costs
    transport_cost = estimate_transport_costs(travel_times)
    breakdown["transport"] = transport_cost
    
    # Total
    total_cost = ticket_cost + meal_cost + transport_cost
    
    return total_cost, breakdown


def cost_agent(state: PlannerState) -> PlannerState:
    """
    Cost Agent - calculates total cost of the itinerary.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with total_cost populated
    """
    logger.info("Cost Agent: Calculating itinerary costs")
    
    if not state.optimized_route:
        logger.warning("No optimized route available")
        return state
    
    # Build visit durations dictionary
    visit_durations = {
        place.name: place.visit_duration
        for place in state.candidate_places
    }
    
    # Calculate costs
    total_cost, breakdown = calculate_total_cost(
        state.optimized_route,
        state.ticket_info,
        state.travel_times,
        visit_durations
    )
    
    state.total_cost = total_cost
    
    # Add cost explanation
    ticket_cost = breakdown.get("tickets", 0)
    meal_cost = breakdown.get("meals", 0)
    transport_cost = breakdown.get("transport", 0)
    num_meals = breakdown.get("num_meals", 0)
    
    cost_explanation = (
        f"\n💰 Total estimated cost: €{total_cost:.2f}\n"
        f"  - Tickets: €{ticket_cost:.2f}\n"
        f"  - Meals ({num_meals}): €{meal_cost:.2f}\n"
        f"  - Transport: €{transport_cost:.2f}"
    )
    
    state.explanation += cost_explanation
    
    logger.info(f"Cost Agent: Total cost €{total_cost:.2f}")
    
    # Check budget constraint
    if state.user_preferences.max_budget and total_cost > state.user_preferences.max_budget:
        warning = f"\n⚠️ Cost (€{total_cost:.0f}) exceeds budget (€{state.user_preferences.max_budget:.0f})"
        state.explanation += warning
        state.feasibility_issues.append(f"Cost exceeds budget by €{total_cost - state.user_preferences.max_budget:.0f}")
        logger.warning(warning)
    
    return state
