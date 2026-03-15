"""
Geocoder module for converting place names to geographic coordinates.

This module provides geocoding functionality with caching and fallback to a
manual coordinate database for major Rome landmarks.

Uses direct HTTP requests to the Nominatim API instead of geopy to avoid
signal-based timeout issues in threaded environments (e.g., Streamlit Cloud).
"""

from typing import Optional, Dict, Tuple
import requests
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

# Nominatim API endpoint
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

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
    "borghese gallery": Coordinates(41.9142, 12.4922, "exact", "manual"),
    "galleria borghese": Coordinates(41.9142, 12.4922, "exact", "manual"),
    "palatine hill": Coordinates(41.8892, 12.4874, "exact", "manual"),
    "palatino": Coordinates(41.8892, 12.4874, "exact", "manual"),
    "piazza venezia": Coordinates(41.8964, 12.4827, "exact", "manual"),
    "vittoriano": Coordinates(41.8946, 12.4833, "exact", "manual"),
    "altare della patria": Coordinates(41.8946, 12.4833, "exact", "manual"),
    "mouth of truth": Coordinates(41.8882, 12.4815, "exact", "manual"),
    "bocca della verita": Coordinates(41.8882, 12.4815, "exact", "manual"),
    "ara pacis": Coordinates(41.9060, 12.4754, "exact", "manual"),
    "appian way": Coordinates(41.8422, 12.5244, "approximate", "manual"),
    "via appia antica": Coordinates(41.8422, 12.5244, "approximate", "manual"),
    "janiculum hill": Coordinates(41.8893, 12.4614, "exact", "manual"),
    "gianicolo": Coordinates(41.8893, 12.4614, "exact", "manual"),
    "santa maria maggiore": Coordinates(41.8976, 12.4984, "exact", "manual"),
    "san giovanni in laterano": Coordinates(41.8859, 12.5057, "exact", "manual"),
    "santa maria in trastevere": Coordinates(41.8895, 12.4694, "exact", "manual"),
    "san clemente": Coordinates(41.8893, 12.4976, "exact", "manual"),
    "capitoline museums": Coordinates(41.8931, 12.4828, "exact", "manual"),
    "musei capitolini": Coordinates(41.8931, 12.4828, "exact", "manual"),
    "maxxi": Coordinates(41.9280, 12.4672, "exact", "manual"),
    "vatican museums": Coordinates(41.9065, 12.4536, "exact", "manual"),
    "catacombs": Coordinates(41.8578, 12.5147, "approximate", "manual"),
    "testaccio": Coordinates(41.8764, 12.4756, "approximate", "manual"),
    "monti": Coordinates(41.8953, 12.4942, "approximate", "manual"),
    "prati": Coordinates(41.9078, 12.4600, "approximate", "manual"),
}


class Geocoder:
    """
    Geocoder for converting place names to coordinates with caching.
    
    Uses direct HTTP requests to the Nominatim API (no geopy) to avoid
    signal-based timeout issues in threaded environments like Streamlit Cloud.
    Implements in-memory caching and fallback to manual coordinate database.
    """
    
    def __init__(self, user_agent: str = None):
        """Initialize the geocoder.
        
        Args:
            user_agent: User agent string for Nominatim API (uses config default if None)
        """
        if user_agent is None:
            user_agent = GEOCODING_USER_AGENT
        
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.cache: Dict[str, Optional[Coordinates]] = {}
        logger.info("Geocoder initialized with user_agent: %s (direct HTTP)", user_agent)
    
    def geocode_place(
        self, 
        place_name: str, 
        bias_location: Optional[Tuple[float, float]] = None,
        max_retries: int = None
    ) -> Optional[Coordinates]:
        """Geocode a place name to coordinates with retry logic and fallback.
        
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
        
        # Try geocoding with direct Nominatim HTTP API
        for attempt in range(max_retries):
            try:
                query = f"{place_name}, Rome, Italy"
                # viewbox format: left,top,right,bottom (lon,lat,lon,lat)
                viewbox = f"{ROME_BBOX[0][1]},{ROME_BBOX[1][0]},{ROME_BBOX[1][1]},{ROME_BBOX[0][0]}"
                
                params = {
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "viewbox": viewbox,
                    "bounded": 0,
                }
                
                resp = self.session.get(
                    NOMINATIM_URL,
                    params=params,
                    timeout=GEOCODING_TIMEOUT,
                )
                resp.raise_for_status()
                results = resp.json()
                
                if results:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])
                    coords = Coordinates(
                        latitude=lat,
                        longitude=lon,
                        accuracy="exact",
                        source="geocoder",
                    )
                    self.cache[normalized_name] = coords
                    logger.info("Geocoded '%s' to (%f, %f)", place_name, lat, lon)
                    return coords
                else:
                    logger.warning("No geocoding result for: %s", place_name)
                    break  # No point retrying if no result found
            
            except requests.exceptions.Timeout:
                logger.warning(
                    "Geocoding timeout for '%s' (attempt %d/%d)",
                    place_name, attempt + 1, max_retries,
                )
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1 * (2 ** attempt))
                    continue
                else:
                    logger.error("Geocoding failed after %d attempts for '%s'", max_retries, place_name)
            
            except requests.exceptions.RequestException as e:
                logger.error("Geocoding request error for '%s': %s", place_name, str(e))
                break
            
            except Exception as e:
                logger.error("Unexpected error geocoding '%s': %s", place_name, str(e), exc_info=True)
                break
        
        # Cache the failure to avoid repeated lookups
        self.cache[normalized_name] = None
        logger.info("Geocoding failed for '%s', cached as None", place_name)
        return None
    
    def batch_geocode(self, places: list[str]) -> Dict[str, Optional[Coordinates]]:
        """Geocode multiple places in batch.
        
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
        """Reverse geocode coordinates to a place name.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
        
        Returns:
            Place name if successful, None otherwise
        """
        try:
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json",
                "accept-language": "en",
            }
            resp = self.session.get(
                NOMINATIM_REVERSE_URL,
                params=params,
                timeout=GEOCODING_TIMEOUT,
            )
            resp.raise_for_status()
            result = resp.json()
            
            if "display_name" in result:
                address = result["display_name"]
                logger.info("Reverse geocoded (%f, %f) to '%s'", lat, lon, address)
                return address
            else:
                logger.warning("No reverse geocoding result for (%f, %f)", lat, lon)
                return None
        
        except requests.exceptions.RequestException as e:
            logger.error("Reverse geocoding request error for (%f, %f): %s", lat, lon, str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error reverse geocoding (%f, %f): %s", lat, lon, str(e))
            return None
