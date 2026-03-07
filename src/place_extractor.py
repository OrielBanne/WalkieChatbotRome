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
        "vatican", "vatican city", "vatican museums",
        "st peter's basilica", "st. peter's basilica", "saint peter's basilica",
        "sistine chapel",
        "spanish steps", "piazza di spagna",
        "roman forum", "foro romano",
        "palatine hill", "palatino",
        "castel sant'angelo", "castel sant angelo", "castle of the holy angel",
        "piazza navona",
        "villa borghese", "borghese gallery",
        "trastevere",
        "campo de' fiori", "campo de fiori",
        "piazza del popolo",
        "circus maximus", "circo massimo",
        "capitoline hill", "campidoglio",
        "ara pacis",
        "baths of caracalla", "terme di caracalla",
        "appian way", "via appia antica",
        "catacombs",
        "mouth of truth", "bocca della verità", "bocca della verita",
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
    }
    
    def __init__(self):
        """Initialize the PlaceExtractor."""
        # Create regex pattern from gazetteer
        # Sort by length (longest first) to match longer phrases first
        sorted_places = sorted(self.ROME_GAZETTEER, key=len, reverse=True)
        escaped_places = [re.escape(place) for place in sorted_places]
        self.pattern = re.compile(
            r'(?i)\b(' + '|'.join(escaped_places) + r')\b'
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
        text_lower = text.lower()
        
        # Check each place in gazetteer
        for place in self.ROME_GAZETTEER:
            # Simple substring search (case-insensitive)
            if place in text_lower:
                # Find the actual text (preserving case)
                start = text_lower.find(place)
                if start != -1:
                    end = start + len(place)
                    actual_text = text[start:end]
                    place_lower = place.lower()
                    
                    # Get context (50 chars before and after)
                    context_start = max(0, start - 50)
                    context_end = min(len(text), end + 50)
                    context = text[context_start:context_end]
                    
                    # Avoid duplicates
                    if place_lower not in seen:
                        seen.add(place_lower)
                        places.append(PlaceMention(
                            name=actual_text.title(),  # Capitalize properly
                            entity_type="GPE",
                            confidence=1.0,
                            span=(start, end),
                            context=context
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
