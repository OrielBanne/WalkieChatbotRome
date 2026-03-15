"""Opening Hours Agent for checking place availability."""

import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Dict, Optional

from .models import OpeningHours, PlannerState

logger = logging.getLogger(__name__)


def load_opening_hours_data() -> Dict[str, dict]:
    """Load opening hours data from JSON file."""
    data_path = Path(__file__).parent.parent.parent / "data" / "opening_hours.json"
    
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {item["place_name"]: item for item in data}
    except FileNotFoundError:
        logger.error(f"Opening hours data file not found: {data_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing opening hours JSON: {e}")
        return {}


# Cache the data
_OPENING_HOURS_DATA = load_opening_hours_data()


def get_opening_hours(place_name: str, date: Optional[datetime] = None) -> Optional[OpeningHours]:
    """
    Get opening hours for a specific place.
    
    Args:
        place_name: Name of the place
        date: Date to check (defaults to today)
        
    Returns:
        OpeningHours object or None if not found
    """
    if date is None:
        date = datetime.now()
    
    data = _OPENING_HOURS_DATA.get(place_name)
    if not data:
        logger.warning(f"No opening hours data found for: {place_name}")
        return None
    
    # Check if closed today (simplified - doesn't handle day of week yet)
    day_name = date.strftime("%A")
    closed_days = data.get("closed_days", [])
    is_open_today = day_name not in closed_days
    
    # Parse times
    opening_time = None
    closing_time = None
    last_entry_time = None
    
    if data.get("opening_time"):
        try:
            opening_time = datetime.strptime(data["opening_time"], "%H:%M").time()
        except ValueError:
            logger.warning(f"Invalid opening_time format for {place_name}")
    
    if data.get("closing_time"):
        try:
            closing_time = datetime.strptime(data["closing_time"], "%H:%M").time()
        except ValueError:
            logger.warning(f"Invalid closing_time format for {place_name}")
    
    if data.get("last_entry_time"):
        try:
            last_entry_time = datetime.strptime(data["last_entry_time"], "%H:%M").time()
        except ValueError:
            logger.warning(f"Invalid last_entry_time format for {place_name}")
    
    return OpeningHours(
        place_name=place_name,
        is_open_today=is_open_today,
        opening_time=opening_time,
        closing_time=closing_time,
        last_entry_time=last_entry_time,
        closed_days=closed_days
    )


def check_is_open(place_name: str, check_time: datetime) -> bool:
    """
    Check if a place is open at a specific time.
    
    Args:
        place_name: Name of the place
        check_time: Time to check
        
    Returns:
        True if open, False otherwise
    """
    hours = get_opening_hours(place_name, check_time)
    if not hours:
        return True  # Assume open if no data
    
    if not hours.is_open_today:
        return False
    
    if hours.opening_time and hours.closing_time:
        current_time = check_time.time()
        return hours.opening_time <= current_time <= hours.closing_time
    
    return True  # Assume open if no time restrictions


def get_last_entry_time(place_name: str) -> Optional[time]:
    """
    Get the last entry time for a place.
    
    Args:
        place_name: Name of the place
        
    Returns:
        Last entry time or None
    """
    hours = get_opening_hours(place_name)
    return hours.last_entry_time if hours else None


def opening_hours_agent(state: PlannerState) -> PlannerState:
    """
    Opening Hours Agent - checks opening hours for all candidate places.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with opening_hours populated
    """
    logger.info("Opening Hours Agent: Checking opening hours for candidate places")
    
    opening_hours = {}
    
    for place in state.candidate_places:
        hours = get_opening_hours(place.name, datetime.now())
        
        if hours:
            opening_hours[place.name] = hours
            
            # Flag if closed today
            if not hours.is_open_today:
                issue = f"{place.name} is closed today"
                if issue not in state.feasibility_issues:
                    state.feasibility_issues.append(issue)
                logger.warning(issue)
        else:
            # Create default hours if no data available
            opening_hours[place.name] = OpeningHours(
                place_name=place.name,
                is_open_today=True,
                opening_time=None,
                closing_time=None,
                last_entry_time=None,
                closed_days=[]
            )
    
    state.opening_hours = opening_hours
    logger.info(f"Opening Hours Agent: Processed {len(opening_hours)} places")
    
    return state
