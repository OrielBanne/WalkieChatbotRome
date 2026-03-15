"""
Integration module for the Agentic Travel Planner.

This module provides a simple interface to execute the planning workflow
and can be easily integrated into the Streamlit app.
"""

import logging
from typing import Optional, List

from src.agents.workflow import create_planner_workflow
from src.agents.models import PlannerState, UserPreferences, Itinerary, Place

logger = logging.getLogger(__name__)


def plan_itinerary(
    user_query: str,
    user_preferences: Optional[UserPreferences] = None
) -> Optional[Itinerary]:
    """
    Plan an itinerary based on user query and preferences.
    
    Args:
        user_query: User's travel query (e.g., "I want to see ancient Rome")
        user_preferences: User preferences for the trip
        
    Returns:
        Complete Itinerary object or None if planning failed
        
    Example:
        >>> from datetime import time
        >>> prefs = UserPreferences(
        ...     interests=["art", "history"],
        ...     available_hours=8.0,
        ...     max_budget=100.0,
        ...     max_walking_km=10.0,
        ...     crowd_tolerance="neutral",
        ...     start_time=time(9, 0)
        ... )
        >>> itinerary = plan_itinerary("Show me the best of ancient Rome", prefs)
        >>> if itinerary:
        ...     print(f"Planned {len(itinerary.stops)} stops")
    """
    try:
        # Use default preferences if none provided
        if user_preferences is None:
            user_preferences = UserPreferences()
        
        logger.info(f"Planning itinerary for query: {user_query}")
        logger.info(f"Preferences: {user_preferences.model_dump()}")
        
        # Create workflow
        workflow = create_planner_workflow()
        
        # Create initial state
        initial_state = PlannerState(
            user_query=user_query,
            user_preferences=user_preferences
        )
        
        # Execute workflow
        logger.info("Executing planning workflow...")
        result = workflow.invoke(initial_state)
        
        # LangGraph returns a dict, not a PlannerState object
        if isinstance(result, dict):
            errors = result.get("errors", [])
            itinerary = result.get("itinerary")
            candidate_places = result.get("candidate_places", [])
            selected_places = result.get("selected_places", [])
        else:
            errors = getattr(result, "errors", [])
            itinerary = getattr(result, "itinerary", None)
            candidate_places = getattr(result, "candidate_places", [])
            selected_places = getattr(result, "selected_places", [])
        
        # Check for errors
        if errors:
            logger.error(f"Planning completed with errors: {errors}")
        
        # Log discovery results
        logger.info(f"Place discovery found {len(candidate_places)} candidates, {len(selected_places)} selected")
        
        # Return itinerary
        if itinerary:
            if isinstance(itinerary, dict):
                itinerary = Itinerary(**itinerary)
            logger.info(
                f"Successfully planned itinerary with {len(itinerary.stops)} stops, "
                f"feasibility score: {itinerary.feasibility_score:.0f}/100"
            )
            return itinerary
        else:
            logger.warning("Planning completed but no itinerary was generated")
            return None
            
    except Exception as e:
        logger.error(f"Error planning itinerary: {e}", exc_info=True)
        return None


def get_planning_state(
    user_query: str,
    user_preferences: Optional[UserPreferences] = None
) -> Optional[PlannerState]:
    """
    Get the complete planning state (for debugging or advanced use).
    
    Args:
        user_query: User's travel query
        user_preferences: User preferences for the trip
        
    Returns:
        Complete PlannerState object or None if planning failed
    """
    try:
        if user_preferences is None:
            user_preferences = UserPreferences()
        
        workflow = create_planner_workflow()
        
        initial_state = PlannerState(
            user_query=user_query,
            user_preferences=user_preferences
        )
        
        result = workflow.invoke(initial_state)
        
        # LangGraph returns a dict
        if isinstance(result, dict):
            return PlannerState(**result)
        return result
        
    except Exception as e:
        logger.error(f"Error getting planning state: {e}", exc_info=True)
        return None


# Example usage
if __name__ == "__main__":
    from datetime import time
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Example preferences
    preferences = UserPreferences(
        interests=["art", "history"],
        available_hours=6.0,
        max_budget=80.0,
        max_walking_km=8.0,
        crowd_tolerance="avoid",
        start_time=time(9, 0)
    )
    
    # Plan itinerary
    itinerary = plan_itinerary(
        "I want to see ancient Rome and Renaissance art",
        preferences
    )
    
    if itinerary:
        print("\n" + "=" * 60)
        print("ITINERARY GENERATED")
        print("=" * 60)
        print(f"Stops: {len(itinerary.stops)}")
        print(f"Duration: {itinerary.total_duration_minutes // 60}h {itinerary.total_duration_minutes % 60}m")
        print(f"Distance: {itinerary.total_distance_km:.1f} km")
        print(f"Cost: €{itinerary.total_cost:.2f}")
        print(f"Feasibility: {itinerary.feasibility_score:.0f}/100")
        print("\nStops:")
        for i, stop in enumerate(itinerary.stops, 1):
            print(f"{i}. {stop.place.name} - {stop.time.strftime('%H:%M')} ({stop.duration_minutes} min)")
    else:
        print("Failed to generate itinerary")


def modify_itinerary(
    current_itinerary: Itinerary,
    user_preferences: UserPreferences,
    action_type: str,
    place_name: Optional[str] = None,
    stop_index: Optional[int] = None
) -> Optional[Itinerary]:
    """
    Modify an existing itinerary by adding or removing stops.
    
    Args:
        current_itinerary: The current itinerary to modify
        user_preferences: User preferences for re-optimization
        action_type: Either "add" or "remove"
        place_name: Name of place to add (required for "add" action)
        stop_index: Index of stop to remove (required for "remove" action)
        
    Returns:
        Modified and re-optimized Itinerary or None if modification failed
        
    Example:
        >>> # Remove a stop
        >>> modified = modify_itinerary(
        ...     current_itinerary=itinerary,
        ...     user_preferences=prefs,
        ...     action_type="remove",
        ...     stop_index=2
        ... )
        >>> 
        >>> # Add a stop
        >>> modified = modify_itinerary(
        ...     current_itinerary=itinerary,
        ...     user_preferences=prefs,
        ...     action_type="add",
        ...     place_name="Trevi Fountain"
        ... )
    """
    try:
        logger.info(f"Modifying itinerary: action={action_type}, place={place_name}, index={stop_index}")
        
        # Extract current places from itinerary
        current_places = [stop.place for stop in current_itinerary.stops]
        
        # Modify the places list based on action
        if action_type == "remove":
            if stop_index is None or stop_index < 0 or stop_index >= len(current_places):
                logger.error(f"Invalid stop_index: {stop_index}")
                return None
            
            removed_place = current_places.pop(stop_index)
            logger.info(f"Removed place: {removed_place.name}")
            
            if len(current_places) == 0:
                logger.warning("Cannot remove last stop from itinerary")
                return None
        
        elif action_type == "add":
            if not place_name:
                logger.error("place_name is required for 'add' action")
                return None
            
            # Create a new Place object for the added place
            # We'll let the workflow geocode and enrich it
            new_place = Place(
                name=place_name,
                place_type="attraction",
                coordinates=(41.9028, 12.4964),  # Default Rome center
                visit_duration=60  # Default 1 hour
            )
            current_places.append(new_place)
            logger.info(f"Added place: {place_name}")
        
        else:
            logger.error(f"Invalid action_type: {action_type}")
            return None
        
        # Create workflow
        workflow = create_planner_workflow()
        
        # Create state with modified places
        # We'll use selected_places to skip the discovery phase
        initial_state = PlannerState(
            user_query=f"Re-optimize itinerary with {len(current_places)} places",
            user_preferences=user_preferences,
            selected_places=current_places,
            explanation=f"Itinerary modified: {action_type} operation performed."
        )
        
        # Execute workflow (it will skip place discovery and go straight to optimization)
        logger.info("Re-optimizing itinerary...")
        result = workflow.invoke(initial_state)
        
        # LangGraph returns a dict
        if isinstance(result, dict):
            errors = result.get("errors", [])
            itinerary = result.get("itinerary")
        else:
            errors = getattr(result, "errors", [])
            itinerary = getattr(result, "itinerary", None)
        
        # Check for errors
        if errors:
            logger.error(f"Re-optimization completed with errors: {errors}")
        
        # Return modified itinerary
        if itinerary:
            if isinstance(itinerary, dict):
                itinerary = Itinerary(**itinerary)
            logger.info(
                f"Successfully re-optimized itinerary with {len(itinerary.stops)} stops, "
                f"feasibility score: {itinerary.feasibility_score:.0f}/100"
            )
            return itinerary
        else:
            logger.warning("Re-optimization completed but no itinerary was generated")
            return None
            
    except Exception as e:
        logger.error(f"Error modifying itinerary: {e}", exc_info=True)
        return None
