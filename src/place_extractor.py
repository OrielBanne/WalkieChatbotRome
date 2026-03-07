"""
Place extraction module for the Rome Places Chatbot.

This module provides pattern-based place name extraction using regex,
with a gazetteer for validation and disambiguation.
"""

import re
from typing import List, Optional
from src.models import PlaceMention


class PlaceExtractor:
    """
    Extracts place names from text using pattern matching and a gazetteer.
    
    This class uses regex patterns and a gazetteer of Rome places for
    identification and validation.
    """
    
    # Gazetteer of known Rome places (lowercase for case-insensitive matching)
    ROME_GAZETTEER = {
        # Major landmarks
        "colosseum", "colosseo", "roman colosseum",
        "trevi fountain", "fontana di trevi",
        "pantheon",
        "vatican", "vatican city", "st peter's basilica", "sistine chapel",
        "spanish steps", "piazza di spagna",
        "roman forum", "foro romano",
        "palatine hill", "palatino",
        "castel sant'angelo", "castle of the holy angel",
        "piazza navona",
        "villa borghese", "borghese gallery",
        "trastevere",
        "campo de' fiori",
        "piazza del popolo",
        "circus maximus", "circo massimo",
        "capitoline hill", "campidoglio",
        "ara pacis",
        "baths of caracalla", "terme di caracalla",
        "appian way", "via appia antica",
        "catacombs",
        "mouth of truth", "bocca della verità",
        "piazza venezia",
        "vittoriano", "altare della patria",
        "tiber river", "fiume tevere",
        "janiculum hill", "gianicolo",
        "aventine hill", "aventino",
        "testaccio",
        "monti",
        "prati",
        "esquiline hill", "esquilino",
        "quirinal hill", "quirinale",
        "viminal hill", "viminale",
        "caelian hill", "celio",
        
        # Churches
        "santa maria maggiore",
        "san giovanni in laterano",
        "santa maria in trastevere",
        "santa prassede",
        "san clemente",
        "santa cecilia",
        
        # Museums
        "capitoline museums", "musei capitolini",
        "national roman museum",
        "galleria borghese",
        "maxxi",
        
        # Squares and streets
        "piazza della repubblica",
        "via del corso",
        "via veneto",
        "via condotti",
        
        # General
        "rome", "roma",
    }
    
    def __init__(self):
        """Initialize the PlaceExtractor."""
        # Create regex pattern from gazetteer
        escaped_places = [re.escape(place) for place in self.ROME_GAZETTEER]
        self.pattern = re.compile(
            r'\b(' + '|'.join(escaped_places) + r')\b',
            re.IGNORECASE
        )
    
    def extract_places(self, text: str) -> List[PlaceMention]:
        """
        Extract place mentions from text using pattern matching.
        
        Args:
            text: The input text to extract places from
            
        Returns:
            List of PlaceMention objects with extracted places and metadata.
        """
        if not text or not text.strip():
            return []
        
        places = []
        seen = set()
        
        # Find all matches
        for match in self.pattern.finditer(text):
            place_name = match.group(0)
            place_lower = place_name.lower()
            
            # Avoid duplicates
            if place_lower not in seen:
                seen.add(place_lower)
                places.append(PlaceMention(
                    name=place_name,
                    entity_type="GPE",
                    confidence=1.0,
                    start_char=match.start(),
                    end_char=match.end()
                ))
        
        return places
    
    def filter_rome_places(self, places: List[PlaceMention]) -> List[PlaceMention]:
        """
        Filter places to only include those in Rome.
        
        Args:
            places: List of place mentions to filter
            
        Returns:
            Filtered list containing only Rome places
        """
        rome_places = []
        
        for place in places:
            place_lower = place.name.lower()
            
            # Check if place is in gazetteer
            if place_lower in self.ROME_GAZETTEER:
                rome_places.append(place)
        
        return rome_places
