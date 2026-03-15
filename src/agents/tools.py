"""Tool functions for agents in the Agentic Travel Planner.

This module provides utility functions that agents can use to gather
information and make decisions during the planning process.
"""

import functools
import platform
from typing import Callable, Any


# Timeout decorator for tool functions
def timeout(seconds: int):
    """Decorator to add timeout to tool functions.
    
    This is a cross-platform timeout decorator. On Unix systems, it uses
    signal.alarm(). On Windows, it's a no-op decorator since signal.SIGALRM
    is not available. For production use on Windows, consider using threading
    or multiprocessing for timeouts.
    
    Args:
        seconds: Maximum execution time in seconds
        
    Raises:
        TimeoutError: If function execution exceeds timeout (Unix only)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Only use signal-based timeout on Unix systems
            if platform.system() != "Windows":
                import signal
                
                def handler(signum, frame):
                    raise TimeoutError(f"{func.__name__} exceeded {seconds}s timeout")
                
                # Set the signal handler and alarm
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(seconds)
                try:
                    result = func(*args, **kwargs)
                finally:
                    # Disable the alarm
                    signal.alarm(0)
                return result
            else:
                # On Windows, just execute the function without timeout
                return func(*args, **kwargs)
        return wrapper
    return decorator


@timeout(10)
def classify_place_type(place_name: str) -> str:
    """Classify a place into a category based on its name.
    
    Uses keyword matching to determine the type of place. This is a simple
    heuristic-based approach that can be enhanced with ML in the future.
    
    Args:
        place_name: Name of the place to classify
        
    Returns:
        Place type as a string (monument, museum, restaurant, church, etc.)
        
    Examples:
        >>> classify_place_type("Colosseum")
        'monument'
        >>> classify_place_type("Vatican Museums")
        'museum'
        >>> classify_place_type("Trattoria da Enzo")
        'restaurant'
    """
    if not place_name or not place_name.strip():
        return "attraction"
    
    place_lower = place_name.lower()
    
    # Museum keywords
    if any(keyword in place_lower for keyword in ["museum", "museo", "gallery", "galleria"]):
        return "museum"
    
    # Church keywords
    if any(keyword in place_lower for keyword in ["church", "basilica", "cathedral", "chapel", "santa", "san ", "st."]):
        return "church"
    
    # Restaurant/food keywords
    if any(keyword in place_lower for keyword in ["restaurant", "trattoria", "osteria", "pizzeria", "cafe", "caffè", "bar"]):
        return "restaurant"
    
    # Park/garden keywords
    if any(keyword in place_lower for keyword in ["park", "garden", "villa", "parco", "giardino"]):
        return "park"
    
    # Monument keywords
    if any(keyword in place_lower for keyword in ["colosseum", "pantheon", "fountain", "fontana", "arch", "arco", "column", "colonna", "monument"]):
        return "monument"
    
    # Square/piazza keywords
    if any(keyword in place_lower for keyword in ["square", "piazza"]):
        return "square"
    
    # Default to attraction
    return "attraction"


@timeout(10)
def estimate_visit_duration(place_name: str, place_type: str = None) -> int:
    """Estimate visit duration for a place in minutes.
    
    Uses heuristics based on place type and specific place names to estimate
    how long a typical visit would take.
    
    Args:
        place_name: Name of the place
        place_type: Optional type of place (if not provided, will classify)
        
    Returns:
        Estimated visit duration in minutes
        
    Examples:
        >>> estimate_visit_duration("Colosseum", "monument")
        120
        >>> estimate_visit_duration("Vatican Museums", "museum")
        180
        >>> estimate_visit_duration("Trevi Fountain", "monument")
        30
    """
    if not place_name or not place_name.strip():
        return 60  # Default 1 hour
    
    # Classify if not provided
    if place_type is None:
        place_type = classify_place_type(place_name)
    
    place_lower = place_name.lower()
    
    # Specific place overrides
    specific_durations = {
        "colosseum": 120,
        "vatican museums": 180,
        "sistine chapel": 60,
        "st. peter's basilica": 90,
        "roman forum": 120,
        "palatine hill": 90,
        "pantheon": 45,
        "trevi fountain": 30,
        "spanish steps": 30,
        "borghese gallery": 120,
        "castel sant'angelo": 90,
        "piazza navona": 45,
        "trastevere": 120,
        "villa borghese": 90,
    }
    
    # Check for specific places
    for place_key, duration in specific_durations.items():
        if place_key in place_lower:
            return duration
    
    # Type-based defaults
    type_durations = {
        "museum": 120,
        "church": 45,
        "monument": 60,
        "restaurant": 90,
        "park": 60,
        "square": 30,
        "attraction": 60,
    }
    
    return type_durations.get(place_type, 60)
