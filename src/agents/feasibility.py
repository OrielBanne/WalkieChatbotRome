"""Feasibility Agent for validating itinerary feasibility."""

import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

from .models import PlannerState, Place, OpeningHours, TravelTime

logger = logging.getLogger(__name__)


def calculate_total_distance(
    route: List[str],
    travel_times: Dict[Tuple[str, str], TravelTime]
) -> float:
    """
    Calculate total walking distance for the route.
    
    Args:
        route: List of place names
        travel_times: Dictionary of travel times
        
    Returns:
        Total distance in kilometers
    """
    total_distance = 0.0
    
    for i in range(len(route) - 1):
        if route[i] == "LUNCH_BREAK" or route[i + 1] == "LUNCH_BREAK":
            continue
        
        key = (route[i], route[i + 1])
        if key in travel_times:
            total_distance += travel_times[key].distance_km
    
    return total_distance


def calculate_total_time(
    route: List[str],
    places: List[Place],
    travel_times: Dict[Tuple[str, str], TravelTime]
) -> int:
    """
    Calculate total time including visits and travel.
    
    Args:
        route: List of place names
        places: List of Place objects
        travel_times: Dictionary of travel times
        
    Returns:
        Total time in minutes
    """
    place_dict = {p.name: p for p in places}
    total_time = 0
    
    for i, place_name in enumerate(route):
        # Add lunch break time
        if place_name == "LUNCH_BREAK":
            total_time += 60  # 1 hour
            continue
        
        # Add visit duration
        place = place_dict.get(place_name)
        if place:
            total_time += place.visit_duration
        
        # Add travel time to next place
        if i < len(route) - 1:
            next_place = route[i + 1]
            if next_place != "LUNCH_BREAK":
                key = (place_name, next_place)
                if key in travel_times:
                    total_time += travel_times[key].duration_minutes
    
    return int(total_time)


def check_opening_hours_conflicts(
    route: List[str],
    places: List[Place],
    opening_hours: Dict[str, OpeningHours],
    travel_times: Dict[Tuple[str, str], TravelTime],
    start_time: datetime
) -> List[str]:
    """
    Check for opening hours conflicts in the route.
    
    Args:
        route: List of place names
        places: List of Place objects
        opening_hours: Dictionary of opening hours
        travel_times: Dictionary of travel times
        start_time: Starting time
        
    Returns:
        List of conflict descriptions
    """
    conflicts = []
    place_dict = {p.name: p for p in places}
    current_time = start_time
    
    for i, place_name in enumerate(route):
        if place_name == "LUNCH_BREAK":
            current_time += timedelta(minutes=60)
            continue
        
        hours = opening_hours.get(place_name)
        if not hours:
            continue
        
        # Check if closed today
        if not hours.is_open_today:
            conflicts.append(f"{place_name} is closed today")
            continue
        
        # Check if arrive before opening
        if hours.opening_time:
            opening_dt = datetime.combine(current_time.date(), hours.opening_time)
            if current_time < opening_dt:
                conflicts.append(
                    f"Arrive at {place_name} at {current_time.strftime('%H:%M')} "
                    f"before opening ({hours.opening_time.strftime('%H:%M')})"
                )
        
        # Check if arrive after last entry
        if hours.last_entry_time:
            last_entry_dt = datetime.combine(current_time.date(), hours.last_entry_time)
            if current_time > last_entry_dt:
                conflicts.append(
                    f"Arrive at {place_name} at {current_time.strftime('%H:%M')} "
                    f"after last entry ({hours.last_entry_time.strftime('%H:%M')})"
                )
        
        # Update current time
        place = place_dict.get(place_name)
        if place:
            current_time += timedelta(minutes=place.visit_duration)
        
        # Add travel time to next place
        if i < len(route) - 1:
            next_place = route[i + 1]
            if next_place != "LUNCH_BREAK":
                key = (place_name, next_place)
                if key in travel_times:
                    current_time += timedelta(minutes=travel_times[key].duration_minutes)
    
    return conflicts


def calculate_feasibility_score(
    total_distance: float,
    total_time: int,
    total_cost: float,
    conflicts: List[str],
    max_walking_km: float,
    available_hours: float,
    max_budget: float
) -> float:
    """
    Calculate feasibility score (0-100).
    
    Args:
        total_distance: Total walking distance in km
        total_time: Total time in minutes
        total_cost: Total cost in EUR
        conflicts: List of conflicts
        max_walking_km: Maximum walking distance preference
        available_hours: Available hours preference
        max_budget: Maximum budget preference
        
    Returns:
        Feasibility score (0-100)
    """
    score = 100.0
    
    # Distance penalty
    if total_distance > max_walking_km:
        excess_ratio = (total_distance - max_walking_km) / max_walking_km
        penalty = min(30, excess_ratio * 30)
        score -= penalty
    
    # Time penalty
    available_minutes = available_hours * 60
    if total_time > available_minutes:
        excess_ratio = (total_time - available_minutes) / available_minutes
        penalty = min(40, excess_ratio * 40)
        score -= penalty
    
    # Budget penalty
    if max_budget and total_cost > max_budget:
        excess_ratio = (total_cost - max_budget) / max_budget
        penalty = min(20, excess_ratio * 20)
        score -= penalty
    
    # Conflict penalty
    score -= len(conflicts) * 10
    
    return max(0.0, score)


def suggest_improvements(
    issues: List[str],
    route: List[str],
    places: List[Place]
) -> List[str]:
    """
    Suggest improvements to make itinerary feasible.
    
    Args:
        issues: List of feasibility issues
        route: Current route
        places: List of places
        
    Returns:
        List of suggestions
    """
    suggestions = []
    
    # Check for distance issues
    if any("distance" in issue.lower() for issue in issues):
        suggestions.append(f"Consider reducing stops from {len(route)} to {len(route) - 2}")
        suggestions.append("Consider using public transport for longer distances")
    
    # Check for time issues
    if any("time" in issue.lower() for issue in issues):
        suggestions.append("Reduce visit duration at some attractions")
        suggestions.append(f"Consider splitting into a multi-day itinerary")
    
    # Check for budget issues
    if any("cost" in issue.lower() or "budget" in issue.lower() for issue in issues):
        suggestions.append("Skip paid attractions and focus on free sites")
        suggestions.append("Bring packed lunch to reduce meal costs")
    
    # Check for opening hours conflicts
    if any("closed" in issue.lower() or "opening" in issue.lower() for issue in issues):
        suggestions.append("Adjust start time to match opening hours")
        suggestions.append("Reorder stops to visit places during opening hours")
    
    return suggestions


def feasibility_agent(state: PlannerState) -> PlannerState:
    """
    Feasibility Agent - validates itinerary feasibility.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with feasibility_score and is_feasible populated
    """
    logger.info("Feasibility Agent: Validating itinerary feasibility")
    
    if not state.optimized_route:
        logger.warning("No optimized route available")
        state.is_feasible = False
        state.feasibility_score = 0.0
        return state
    
    issues = list(state.feasibility_issues)  # Copy existing issues
    
    # Calculate total distance
    total_distance = calculate_total_distance(state.optimized_route, state.travel_times)
    logger.info(f"Total walking distance: {total_distance:.2f} km")
    
    max_walking = state.user_preferences.max_walking_km
    if total_distance > max_walking:
        issue = f"Walking distance ({total_distance:.1f}km) exceeds limit ({max_walking:.1f}km)"
        if issue not in issues:
            issues.append(issue)
        logger.warning(issue)
    
    # Calculate total time
    total_time = calculate_total_time(
        state.optimized_route,
        state.candidate_places,
        state.travel_times
    )
    logger.info(f"Total time: {total_time / 60:.1f} hours")
    
    available_minutes = state.user_preferences.available_hours * 60
    if total_time > available_minutes:
        issue = f"Total time ({total_time / 60:.1f}h) exceeds available time ({state.user_preferences.available_hours:.1f}h)"
        if issue not in issues:
            issues.append(issue)
        logger.warning(issue)
    
    # Check opening hours conflicts
    start_time = datetime.now()
    if state.user_preferences.start_time:
        start_time = start_time.replace(
            hour=state.user_preferences.start_time.hour,
            minute=state.user_preferences.start_time.minute
        )
    
    conflicts = check_opening_hours_conflicts(
        state.optimized_route,
        state.candidate_places,
        state.opening_hours,
        state.travel_times,
        start_time
    )
    issues.extend(conflicts)
    
    # Check budget (already checked in cost agent, but verify)
    if state.total_cost and state.user_preferences.max_budget:
        if state.total_cost > state.user_preferences.max_budget:
            issue = f"Cost (€{state.total_cost:.0f}) exceeds budget (€{state.user_preferences.max_budget:.0f})"
            if issue not in issues:
                issues.append(issue)
    
    # Calculate feasibility score
    score = calculate_feasibility_score(
        total_distance,
        total_time,
        state.total_cost or 0.0,
        issues,
        max_walking,
        state.user_preferences.available_hours,
        state.user_preferences.max_budget or float('inf')
    )
    
    state.feasibility_score = score
    state.feasibility_issues = issues
    state.is_feasible = score >= 70  # Threshold for feasibility
    
    logger.info(f"Feasibility score: {score:.1f}/100, Feasible: {state.is_feasible}")
    
    # Add suggestions if not feasible
    if not state.is_feasible:
        suggestions = suggest_improvements(issues, state.optimized_route, state.candidate_places)
        if suggestions:
            state.explanation += "\n\n💡 Suggestions to improve feasibility:\n"
            for suggestion in suggestions[:3]:  # Limit to top 3
                state.explanation += f"  - {suggestion}\n"
    
    return state
