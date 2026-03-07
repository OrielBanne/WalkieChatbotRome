"""
Tests for the Geocoder module.

This module contains both property-based tests and unit tests for the
geocoding functionality.
"""

import pytest
from hypothesis import given, strategies as st, settings
from src.geocoder import Geocoder, MANUAL_COORDINATES, ROME_CENTER
from src.models import Coordinates


# Property-Based Tests

# Feature: rome-places-chatbot, Property 14: Geocoding Cache Consistency
@given(place_name=st.text(min_size=3, max_size=50))
@settings(max_examples=20, deadline=None)
def test_geocoding_cache_consistency(place_name):
    """
    **Validates: Property 14 - Geocoding Cache Consistency**
    
    For any place name, repeated geocoding should return same coordinates.
    This verifies that the caching mechanism works correctly and provides
    consistent results across multiple calls.
    """
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    
    # First geocoding attempt
    coords1 = geocoder.geocode_place(place_name, bias_location=ROME_CENTER)
    
    # Second geocoding attempt (should use cache)
    coords2 = geocoder.geocode_place(place_name, bias_location=ROME_CENTER)
    
    # Both should be the same (either both None or both equal)
    if coords1 is not None:
        assert coords2 is not None, f"First call returned coordinates but second returned None for '{place_name}'"
        assert coords1.latitude == coords2.latitude, f"Latitude mismatch for '{place_name}'"
        assert coords1.longitude == coords2.longitude, f"Longitude mismatch for '{place_name}'"
        assert coords1.accuracy == coords2.accuracy, f"Accuracy mismatch for '{place_name}'"
        # Source might differ (geocoder vs cache), but coordinates should match
    else:
        assert coords2 is None, f"First call returned None but second returned coordinates for '{place_name}'"


# Unit Tests

def test_geocode_colosseum():
    """Test geocoding of the Colosseum returns valid coordinates."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    coords = geocoder.geocode_place("Colosseum")
    
    assert coords is not None
    assert isinstance(coords, Coordinates)
    # Should be near the actual Colosseum location
    assert 41.88 < coords.latitude < 41.91
    assert 12.48 < coords.longitude < 12.51


def test_geocode_empty_string():
    """Test that empty place name returns None."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    coords = geocoder.geocode_place("")
    
    assert coords is None


def test_geocode_whitespace_only():
    """Test that whitespace-only place name returns None."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    coords = geocoder.geocode_place("   ")
    
    assert coords is None


def test_cache_behavior():
    """Test that caching works correctly."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    
    # First call - should geocode
    coords1 = geocoder.geocode_place("Trevi Fountain")
    
    # Check cache was populated
    assert "trevi fountain" in geocoder.cache
    
    # Second call - should use cache
    coords2 = geocoder.geocode_place("Trevi Fountain")
    
    # Should return same coordinates
    assert coords1 is not None
    assert coords2 is not None
    assert coords1.latitude == coords2.latitude
    assert coords1.longitude == coords2.longitude


def test_manual_database_fallback():
    """Test fallback to manual coordinate database."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    
    # Use a place from manual database - use a unique name that won't be found online
    # First, add a test entry to the geocoder's manual database
    test_place = "Test Landmark XYZ123"
    test_coords = Coordinates(41.9000, 12.5000, "exact", "manual")
    
    # Directly add to manual coordinates for this test
    from src.geocoder import MANUAL_COORDINATES
    MANUAL_COORDINATES[test_place.lower()] = test_coords
    
    coords = geocoder.geocode_place(test_place)
    
    assert coords is not None
    # Should match manual database entry
    assert coords.latitude == test_coords.latitude
    assert coords.longitude == test_coords.longitude
    assert coords.source == "manual"


def test_case_insensitive_lookup():
    """Test that place name lookup is case-insensitive."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    
    coords1 = geocoder.geocode_place("COLOSSEUM")
    coords2 = geocoder.geocode_place("colosseum")
    coords3 = geocoder.geocode_place("Colosseum")
    
    assert coords1 is not None
    assert coords2 is not None
    assert coords3 is not None
    assert coords1.latitude == coords2.latitude == coords3.latitude
    assert coords1.longitude == coords2.longitude == coords3.longitude


def test_batch_geocode():
    """Test batch geocoding of multiple places."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    
    places = ["Colosseum", "Trevi Fountain", "Pantheon"]
    results = geocoder.batch_geocode(places)
    
    assert len(results) == 3
    assert "Colosseum" in results
    assert "Trevi Fountain" in results
    assert "Pantheon" in results
    
    # All should have valid coordinates
    for place, coords in results.items():
        assert coords is not None, f"Failed to geocode {place}"
        assert isinstance(coords, Coordinates)


def test_batch_geocode_empty_list():
    """Test batch geocoding with empty list."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    
    results = geocoder.batch_geocode([])
    
    assert results == {}


def test_reverse_geocode():
    """Test reverse geocoding of coordinates."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    
    # Colosseum coordinates
    address = geocoder.reverse_geocode(41.8902, 12.4922)
    
    assert address is not None
    assert isinstance(address, str)
    assert len(address) > 0


def test_reverse_geocode_invalid_coordinates():
    """Test reverse geocoding with coordinates far from Rome."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    
    # Coordinates in the middle of the ocean
    address = geocoder.reverse_geocode(0.0, 0.0)
    
    # Should still return something or None, but not crash
    assert address is None or isinstance(address, str)


def test_geocode_nonexistent_place():
    """Test geocoding of a place that doesn't exist."""
    geocoder = Geocoder(user_agent="test_rome_chatbot")
    
    coords = geocoder.geocode_place("XYZ Nonexistent Place 12345")
    
    # Should return None and cache the failure
    assert coords is None
    assert "xyz nonexistent place 12345" in geocoder.cache
    assert geocoder.cache["xyz nonexistent place 12345"] is None
