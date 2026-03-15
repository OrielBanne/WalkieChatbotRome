"""
Geocoder module for converting place names to geographic coordinates.

This module provides geocoding functionality with caching and fallback to a
manual coordinate database for major Rome landmarks.
"""

from typing import Optional, Dict, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geopy.adapters import RequestsAdapter
import logging

from src.models import Coordinates
from src.config import (
    ROME_BBOX,
    ROME_CENTER,
    GEOCODING_USER_AGENT,
    GEOCODING_MAX_RETRIES,
    GEOCODING_TIMEOUT
)

logger = logging.getLogger(__name__)

# Manual coordinate database for major Rome landmarks
MANUAL_COORDINATES = {
    "colosseum": Coordinates(41.8902, 12.4922, "exact", "manual"),
    "colosseo": Coordinates(41.8902, 12.4922, "exact", "manual"),
    "trevi fountain": Coordinates(41.9009, 12.4833, "exact", "manual"),
    "fontana di trevi": Coordinates(41.9009, 12.4833, "exact", "manual"),
    "pantheon": Coordinates(41.8986, 12.4768, "exact", "manual"),
    "spanish steps": Coordinates(41.9058, 12.4823, "exact", "manual"),
    "piazza di spagna": Coordinates(41.9058, 12.4823, "exact", "manual"),
    "vatican": Coordinates(41.9029, 12.4534, "exact", "manual"),
    "vatican city": Coordinates(41.9029, 12.4534, "exact", "manual"),
    "st peter's basilica": Coordinates(41.9022, 12.4539, "exact", "manual"),
    "basilica di san pietro": Coordinates(41.9022, 12.4539, "exact", "manual"),
    "sistine chapel": Coordinates(41.9029, 12.4545, "exact", "manual"),
    "cappella sistina": Coordinates(41.9029, 12.4545, "exact", "manual"),
    "roman forum": Coordinates(41.8925, 12.4853, "exact", "manual"),
    "foro romano": Coordinates(41.8925, 12.4853, "exact", "manual"),
    "piazza navona": Coordinates(41.8992, 12.4731, "exact", "manual"),
    "campo de' fiori": Coordinates(41.8955, 12.4722, "exact", "manual"),
    "castel sant'angelo": Coordinates(41.9031, 12.4663, "exact", "manual"),
    "villa borghese": Coordinates(41.9142, 12.4922, "exact", "manual"),
    "trastevere": Coordinates(41.8897, 12.4689, "approximate", "manual"),
    "piazza del popolo": Coordinates(41.9109, 12.4761, "exact", "manual"),
    "circus maximus": Coordinates(41.8857, 12.4856, "exact", "manual"),
    "circo massimo": Coordinates(41.8857, 12.4856, "exact", "manual"),
    "baths of caracalla": Coordinates(41.8797, 12.4925, "exact", "manual"),
    "terme di caracalla": Coordinates(41.8797, 12.4925, "exact", "manual"),
    "capitoline hill": Coordinates(41.8931, 12.4828, "exact", "manual"),
    "campidoglio": Coordinates(41.8931, 12.4828, "exact", "manual"),
}


class Geocoder:
    """
    Geocoder for converting place names to coordinates with caching.
    
    Uses Geopy with Nominatim geocoder, biased to Rome's bounding box.
    Implements in-memory caching and fallback to manual coordinate database.
    """
    
    def __init__(self, user_agent: str = None):
        """
        Initialize the geocoder.
        
        Args:
            user_agent: User agent string for Nominatim API (uses config default if None)
        """
        if user_agent is None:
            user_agent = GEOCODING_USER_AGENT
        
        self.geocoder = Nominatim(
            user_agent=user_agent,
            adapter_factory=RequestsAdapter,
        )
        self.cache: Dict[str, Optional[Coordinates]] = {}
        logger.info("Geocoder initialized with user_agent: %s", user_agent)
    
    def geocode_place(
        self, 
        place_name: str, 
        bias_location: Optional[Tuple[float, float]] = None,
        max_retries: int = None
    ) -> Optional[Coordinates]:
        """
        Geocode a place name to coordinates with retry logic and fallback.
        
        Args:
            place_name: Name of the place to geocode
            bias_location: Optional (lat, lon) tuple to bias search results
            max_retries: Maximum number of retry attempts (uses config default if None)
        
        Returns:
            Coordinates object if successful, None otherwise
        """
        if max_retries is None:
            max_retries = GEOCODING_MAX_RETRIES
        
        if not place_name or not place_name.strip():
            logger.warning("Empty place name provided to geocode_place")
            return None
        
        # Normalize place name for cache lookup
        normalized_name = place_name.lower().strip()
        
        # Check cache first
        if normalized_name in self.cache:
            logger.debug("Cache hit for place: %s", place_name)
            return self.cache[normalized_name]
        
        # Check manual database before trying API
        if normalized_name in MANUAL_COORDINATES:
            coords = MANUAL_COORDINATES[normalized_name]
            self.cache[normalized_name] = coords
            logger.info("Using manual coordinates for '%s'", place_name)
            return coords
        
        # Try geocoding with Nominatim with retry logic
        for attempt in range(max_retries):
            try:
                # Build query with Rome bias
                query = f"{place_name}, Rome, Italy"
                
                # Use viewbox to bias results to Rome area
                location = self.geocoder.geocode(
                    query,
                    viewbox=ROME_BBOX,
                    bounded=False,  # Allow results outside viewbox if no matches inside
                    timeout=GEOCODING_TIMEOUT
                )
                
                if location:
                    coords = Coordinates(
                        latitude=location.latitude,
                        longitude=location.longitude,
                        accuracy="exact",
                        source="geocoder"
                    )
                    self.cache[normalized_name] = coords
                    logger.info("Geocoded '%s' to (%f, %f)", place_name, coords.latitude, coords.longitude)
                    return coords
                else:
                    logger.warning("No geocoding result for: %s", place_name)
                    break  # No point retrying if no result found
            
            except GeocoderTimedOut as e:
                logger.warning(f"Geocoding timeout for '{place_name}' (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1 * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Geocoding failed after {max_retries} attempts for '{place_name}'")
            
            except GeocoderServiceError as e:
                logger.error("Geocoding service error for '%s': %s", place_name, str(e))
                break  # Service error, no point retrying
            
            except Exception as e:
                logger.error("Unexpected error geocoding '%s': %s", place_name, str(e), exc_info=True)
                break
        
        # Cache the failure to avoid repeated lookups
        self.cache[normalized_name] = None
        logger.info("Geocoding failed for '%s', cached as None", place_name)
        return None
    
    def batch_geocode(self, places: list[str]) -> Dict[str, Optional[Coordinates]]:
        """
        Geocode multiple places in batch.
        
        Args:
            places: List of place names to geocode
        
        Returns:
            Dictionary mapping place names to their coordinates (or None)
        """
        results = {}
        for place in places:
            results[place] = self.geocode_place(place)
        return results
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Reverse geocode coordinates to a place name.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
        
        Returns:
            Place name if successful, None otherwise
        """
        try:
            location = self.geocoder.reverse(
                (lat, lon),
                timeout=GEOCODING_TIMEOUT,
                language="en"
            )
            
            if location:
                logger.info("Reverse geocoded (%f, %f) to '%s'", lat, lon, location.address)
                return location.address
            else:
                logger.warning("No reverse geocoding result for (%f, %f)", lat, lon)
                return None
        
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error("Reverse geocoding service error for (%f, %f): %s", lat, lon, str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error reverse geocoding (%f, %f): %s", lat, lon, str(e))
            return None
