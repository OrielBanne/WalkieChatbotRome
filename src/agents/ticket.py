"""Ticket Agent for checking ticket requirements and pricing."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from .models import TicketInfo, PlannerState

logger = logging.getLogger(__name__)


def load_ticket_data() -> Dict[str, dict]:
    """Load ticket information from JSON file."""
    data_path = Path(__file__).parent.parent.parent / "data" / "ticket_info.json"
    
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {item["place_name"]: item for item in data}
    except FileNotFoundError:
        logger.error(f"Ticket data file not found: {data_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing ticket JSON: {e}")
        return {}


# Cache the data
_TICKET_DATA = load_ticket_data()


def get_ticket_info(place_name: str) -> Optional[TicketInfo]:
    """
    Get ticket information for a specific place.
    
    Args:
        place_name: Name of the place
        
    Returns:
        TicketInfo object or None if not found
    """
    data = _TICKET_DATA.get(place_name)
    if not data:
        logger.warning(f"No ticket data found for: {place_name}")
        return None
    
    return TicketInfo(
        place_name=place_name,
        ticket_required=data.get("ticket_required", False),
        reservation_required=data.get("reservation_required", False),
        price=data.get("price", 0.0),
        skip_the_line_available=data.get("skip_the_line_available", False),
        booking_url=data.get("booking_url")
    )


def check_reservation_required(place_name: str) -> bool:
    """
    Check if a place requires advance reservation.
    
    Args:
        place_name: Name of the place
        
    Returns:
        True if reservation required, False otherwise
    """
    info = get_ticket_info(place_name)
    return info.reservation_required if info else False


def get_ticket_price(place_name: str) -> float:
    """
    Get the ticket price for a place.
    
    Args:
        place_name: Name of the place
        
    Returns:
        Price in EUR
    """
    info = get_ticket_info(place_name)
    return info.price if info else 0.0


def ticket_agent(state: PlannerState) -> PlannerState:
    """
    Ticket Agent - checks ticket requirements for all candidate places.
    
    Args:
        state: Current planner state
        
    Returns:
        Updated state with ticket_info populated
    """
    logger.info("Ticket Agent: Checking ticket requirements for candidate places")
    
    ticket_info = {}
    
    for place in state.candidate_places:
        info = get_ticket_info(place.name)
        
        if info:
            ticket_info[place.name] = info
            
            # Flag if reservation required
            if info.reservation_required:
                warning = f"⚠️ {place.name} requires advance booking"
                if warning not in state.explanation:
                    state.explanation += f"\n{warning}"
                logger.info(f"Reservation required for {place.name}")
            
            # Flag if expensive
            if info.price > 15.0:
                logger.info(f"{place.name} has high ticket price: €{info.price}")
        else:
            # Create default ticket info if no data available
            ticket_info[place.name] = TicketInfo(
                place_name=place.name,
                ticket_required=False,
                reservation_required=False,
                price=0.0,
                skip_the_line_available=False,
                booking_url=None
            )
    
    state.ticket_info = ticket_info
    logger.info(f"Ticket Agent: Processed {len(ticket_info)} places")
    
    return state
