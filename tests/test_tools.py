"""Unit tests for agent tools."""

import pytest
from src.agents.tools import classify_place_type, estimate_visit_duration


class TestClassifyPlaceType:
    """Tests for classify_place_type function."""
    
    def test_classify_museum(self):
        """Test classification of museums."""
        assert classify_place_type("Vatican Museums") == "museum"
        assert classify_place_type("Borghese Gallery") == "museum"
        assert classify_place_type("Museo Nazionale Romano") == "museum"
    
    def test_classify_church(self):
        """Test classification of churches."""
        assert classify_place_type("St. Peter's Basilica") == "church"
        assert classify_place_type("Santa Maria Maggiore") == "church"
        assert classify_place_type("San Giovanni in Laterano") == "church"
    
    def test_classify_restaurant(self):
        """Test classification of restaurants."""
        assert classify_place_type("Trattoria da Enzo") == "restaurant"
        assert classify_place_type("Pizzeria da Baffetto") == "restaurant"
        assert classify_place_type("Caffè Sant'Eustachio") == "restaurant"
    
    def test_classify_monument(self):
        """Test classification of monuments."""
        assert classify_place_type("Colosseum") == "monument"
        assert classify_place_type("Pantheon") == "monument"
        assert classify_place_type("Trevi Fountain") == "monument"
    
    def test_classify_park(self):
        """Test classification of parks."""
        assert classify_place_type("Villa Borghese") == "park"
        assert classify_place_type("Parco degli Acquedotti") == "park"
    
    def test_classify_square(self):
        """Test classification of squares."""
        assert classify_place_type("Piazza Navona") == "square"
        assert classify_place_type("Piazza di Spagna") == "square"
    
    def test_classify_empty_string(self):
        """Test classification with empty string."""
        assert classify_place_type("") == "attraction"
        assert classify_place_type("   ") == "attraction"
    
    def test_classify_unknown(self):
        """Test classification of unknown places."""
        assert classify_place_type("Some Random Place") == "attraction"


class TestEstimateVisitDuration:
    """Tests for estimate_visit_duration function."""
    
    def test_estimate_colosseum(self):
        """Test duration estimate for Colosseum."""
        assert estimate_visit_duration("Colosseum") == 120
        assert estimate_visit_duration("Colosseum", "monument") == 120
    
    def test_estimate_vatican_museums(self):
        """Test duration estimate for Vatican Museums."""
        assert estimate_visit_duration("Vatican Museums") == 180
        assert estimate_visit_duration("Vatican Museums", "museum") == 180
    
    def test_estimate_trevi_fountain(self):
        """Test duration estimate for Trevi Fountain."""
        assert estimate_visit_duration("Trevi Fountain") == 30
    
    def test_estimate_by_type_museum(self):
        """Test duration estimate for generic museum."""
        assert estimate_visit_duration("Unknown Museum", "museum") == 120
    
    def test_estimate_by_type_church(self):
        """Test duration estimate for generic church."""
        assert estimate_visit_duration("Unknown Church", "church") == 45
    
    def test_estimate_by_type_restaurant(self):
        """Test duration estimate for generic restaurant."""
        assert estimate_visit_duration("Unknown Restaurant", "restaurant") == 90
    
    def test_estimate_by_type_monument(self):
        """Test duration estimate for generic monument."""
        assert estimate_visit_duration("Unknown Monument", "monument") == 60
    
    def test_estimate_empty_string(self):
        """Test duration estimate with empty string."""
        assert estimate_visit_duration("") == 60
        assert estimate_visit_duration("   ") == 60
    
    def test_estimate_without_type(self):
        """Test duration estimate without providing type."""
        # Should auto-classify and estimate
        duration = estimate_visit_duration("Some Museum")
        assert duration == 120  # Should classify as museum
    
    def test_estimate_unknown_place(self):
        """Test duration estimate for unknown place."""
        assert estimate_visit_duration("Unknown Place", "attraction") == 60


class TestTimeoutDecorator:
    """Tests for timeout decorator functionality."""
    
    def test_classify_completes_within_timeout(self):
        """Test that classify_place_type completes within timeout."""
        # Should not raise TimeoutError
        result = classify_place_type("Colosseum")
        assert result == "monument"
    
    def test_estimate_completes_within_timeout(self):
        """Test that estimate_visit_duration completes within timeout."""
        # Should not raise TimeoutError
        result = estimate_visit_duration("Vatican Museums")
        assert result == 180
