"""Crowd Prediction Agent for predicting crowd levels at attractions."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .models import CrowdLevel, PlannerState

logger = logging.getLogger(__name__)


def load_crowd_patterns() -> Dict[str, dict]:
    """Load crowd pattern data from JSON file."""
    data_path = Path(__file__).parent.parent.parent / "data" / "crowd_patterns.json"
    
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Crowd patterns file not found: {data_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing crowd patterns JSON: {e}")
        return {}


# Cache the data
_CROWD_PATTERNS = load_crowd_patterns()


def get_season(date: datetime) -> str:
    """
    Get season for a given date.
    
    Args:
        date: Date to check
        
    Returns:
        Season name: winter, spring, summer, or fall
    """
    month = date.month
    
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "fall"


def is_cruise_ship_day(date: datetime) -> bool:
    """
    Check if date is a typical cruise ship day.
    
    Simplified heuristic: Tuesdays and Thursdays in cruise season (Apr-Oct)
    
    Args:
        date: Date to check
        
    Returns:
        True if likely cruise ship day
    """
    # Cruise season: April to October
    if date.month < 4 or date.month > 10:
        return False
    
    # Tuesdays (1) and Thursdays (3) are common cruise ship days
    return date.weekday() in [1, 3]


def predict_crowd_level(
    place_name: str,
    visit_time: datetime,
    is_cruise_day: bool = False
) -> CrowdLevel:
    """
    Predict crowd level for a place at a specific time.
    
    Args:
        place_name: Name of the place
        visit_time: Time of visit
        is_cruise_day: Whether it's a cruise ship day
        
    Returns:
        Predicted CrowdLevel
    """
    pattern = _CROWD_PATTERNS.get(place_name)
    
    if not pattern:
        logger.warning(f"No crowd pattern for {place_name}, using default")
        return CrowdLevel.MEDIUM
    
    # Start with base level
    base_level_str = pattern.get("base_level", "medium")
    level_map = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "very_high": 4
    }
    crowd_score = level_map.get(base_level_str, 2)
    
    # Adjust for time of day
    hour = visit_time.hour
    peak_hours = pattern.get("peak_hours", [])
    low_hours = pattern.get("low_hours", [])
    
    if hour in peak_hours:
        crowd_score += 1
    elif hour in low_hours:
        crowd_score -= 1
    
    # Adjust for day of week
    day_name = visit_time.strftime("%A")
    peak_days = pattern.get("peak_days", [])
    
    if day_name in peak_days:
        crowd_score += 1
    
    # Adjust for season
    season = get_season(visit_time)
    seasonal_multiplier = pattern.get("seasonal_multiplier", {}).get(season, 1.0)
    crowd_score = int(crowd_score * seasonal_multiplier)
    
    # Adjust for cruise ship days
    if is_cruise_day:
        cruise_impact = pattern.get("cruise_ship_impact", "medium")
        if cruise_impact == "very_high":
            crowd_score += 2
        elif cruise_impact == "high":
            crowd_score += 1
    
    # Map score back to CrowdLevel
    if crowd_score <= 1:
        return CrowdLevel.LOW
    elif crowd_score == 2:
        return CrowdLevel.MEDIUM
    elif crowd_score == 3:
        return CrowdLevel.HIGH
    else:
        return CrowdLevel.VERY_HIGH


def get_best_visiting_time(
    place_name: str,
    date: datetime
) -> Optional[int]:
    """
    Get the best hour to visit a place to avoid crowds.
    
    Args:
        place_name: Name of the place
        date: Date of visit
        
    Returns:
        Best hour (0-23) or None if no data
    """
    pattern = _CROWD_PATTERNS.get(place_name)
    
    if not pattern:
        return None
    
    low_hours = pattern.get("low_hours", [])
    
    if low_hours:
        # Return the first low hour
        return low_hours[0]
    
    return None


def crowd_prediction_agent(state: PlannerState) -> PlannerState:
    """
    Crowd Prediction Agent - predicts crowd levels for each place in the route.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with crowd_predictions populated
    """
    logger.info("Crowd Prediction Agent: Predicting crowd levels")
    
    if not state.optimized_route:
        logger.warning("No optimized route available")
        return state
    
    crowd_predictions = {}
    visit_date = datetime.now()
    is_cruise_day = is_cruise_ship_day(visit_date)
    
    if is_cruise_day:
        logger.info("Today is a cruise ship day - expect higher crowds")
        state.explanation += "\n⚠️ Cruise ship day - popular attractions will be busier"
    
    # Predict crowd level for each place
    # Estimate visit times based on route order
    current_time = visit_date.replace(
        hour=state.user_preferences.start_time.hour if state.user_preferences.start_time else 9,
        minute=state.user_preferences.start_time.minute if state.user_preferences.start_time else 0
    )
    
    for place_name in state.optimized_route:
        # Skip meal breaks
        if place_name == "LUNCH_BREAK":
            current_time = current_time.replace(hour=current_time.hour + 1)
            continue
        
        # Predict crowd level
        crowd_level = predict_crowd_level(place_name, current_time, is_cruise_day)
        crowd_predictions[place_name] = crowd_level
        
        # Add warning for very high crowds
        if crowd_level == CrowdLevel.VERY_HIGH:
            warning = f"⚠️ {place_name} will be very crowded at {current_time.strftime('%H:%M')}"
            if warning not in state.explanation:
                state.explanation += f"\n{warning}"
            logger.warning(warning)
        
        # Update time for next place (add visit duration + travel time)
        place = next((p for p in state.candidate_places if p.name == place_name), None)
        if place:
            from datetime import timedelta
            current_time = current_time + timedelta(minutes=place.visit_duration)
    
    state.crowd_predictions = crowd_predictions
    logger.info(f"Crowd Prediction Agent: Predicted crowds for {len(crowd_predictions)} places")
    
    return state
