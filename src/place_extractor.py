"""
Place extraction module for the Rome Places Chatbot.

This module provides NLP-based place name extraction using spaCy,
with custom pattern matching for Rome landmarks and a gazetteer
for validation and disambiguation.
"""

import spacy
from typing import List, Optional
from src.models import PlaceMention


class PlaceExtractor:
    """
    Extracts place names from text using spaCy NER and custom patterns.
    
    This class uses spaCy's en_core_web_sm model to identify geographic entities
    (GPE, LOC, FAC) and applies custom pattern matching for well-known Rome landmarks.
    It includes a gazetteer of Rome places for validation and filtering.
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
    
    # Custom patterns for Rome landmarks (case-insensitive)
    LANDMARK_PATTERNS = [
        "colosseum", "colosseo",
        "trevi fountain", "fontana di trevi",
        "pantheon",
        "vatican", "st peter's", "sistine chapel",
        "spanish steps",
        "roman forum", "foro romano",
        "palatine hill",
        "castel sant'angelo",
        "piazza navona",
        "villa borghese",
        "trastevere",
        "campo de' fiori",
    ]
    
    def __init__(self):
        """
        Initialize the PlaceExtractor with spaCy model.
        
        Loads the en_core_web_sm model for named entity recognition.
        Downloads the model automatically if not found.
        """
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Try to download the model automatically
            import subprocess
            import sys
            try:
                subprocess.check_call([
                    sys.executable, "-m", "spacy", "download", "en_core_web_sm"
                ])
                self.nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load or download spaCy model 'en_core_web_sm': {e}. "
                    "Please install it manually with: python -m spacy download en_core_web_sm"
                )
    
    def extract_places(self, text: str) -> List[PlaceMention]:
        """
        Extract place mentions from text using NER and pattern matching.
        
        This method combines spaCy's named entity recognition with custom
        pattern matching for Rome landmarks to identify place mentions.
        Includes error handling to ensure graceful degradation.
        
        Args:
            text: The input text to extract places from
            
        Returns:
            List of PlaceMention objects with extracted places and metadata.
            Returns empty list if extraction fails.
        """
        if not text or not text.strip():
            return []
        
        try:
            places = []
            doc = self.nlp(text)
            
            # Extract entities from spaCy NER (GPE, LOC, FAC)
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC", "FAC"]:
                    try:
                        # Get surrounding context (up to 50 chars before and after)
                        start_context = max(0, ent.start_char - 50)
                        end_context = min(len(text), ent.end_char + 50)
                        context = text[start_context:end_context]
                        
                        # Calculate confidence based on entity type and length
                        confidence = self._calculate_confidence(ent.text, ent.label_)
                        
                        place = PlaceMention(
                            name=ent.text,
                            entity_type=ent.label_,
                            confidence=confidence,
                            span=(ent.start_char, ent.end_char),
                            context=context
                        )
                        places.append(place)
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Error processing entity '{ent.text}': {e}")
                        continue
            
            # Add custom pattern matching for Rome landmarks
            text_lower = text.lower()
            for pattern in self.LANDMARK_PATTERNS:
                try:
                    if pattern in text_lower:
                        # Find all occurrences
                        start = 0
                        while True:
                            pos = text_lower.find(pattern, start)
                            if pos == -1:
                                break
                            
                            # Check if already extracted by NER
                            already_extracted = any(
                                p.span[0] <= pos < p.span[1] or
                                pos <= p.span[0] < pos + len(pattern)
                                for p in places
                            )
                            
                            if not already_extracted:
                                # Get surrounding context
                                start_context = max(0, pos - 50)
                                end_context = min(len(text), pos + len(pattern) + 50)
                                context = text[start_context:end_context]
                                
                                # Extract the actual text (preserving case)
                                actual_text = text[pos:pos + len(pattern)]
                                
                                place = PlaceMention(
                                    name=actual_text,
                                    entity_type="LOC",  # Default to LOC for landmarks
                                    confidence=0.95,  # High confidence for known landmarks
                                    span=(pos, pos + len(pattern)),
                                    context=context
                                )
                                places.append(place)
                            
                            start = pos + 1
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error in pattern matching for '{pattern}': {e}")
                    continue
            
            # Sort by position in text
            places.sort(key=lambda p: p.span[0])
            
            return places
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Place extraction failed for text: {e}", exc_info=True)
            return []  # Graceful degradation: return empty list
    
    def filter_rome_places(self, places: List[PlaceMention]) -> List[PlaceMention]:
        """
        Filter place mentions to only include Rome-related places.
        
        Uses the Rome gazetteer to validate that extracted places are
        actually in Rome or are Rome landmarks.
        
        Args:
            places: List of PlaceMention objects to filter
            
        Returns:
            Filtered list containing only Rome-related places
        """
        rome_places = []
        
        for place in places:
            place_lower = place.name.lower()
            
            # Check if place is in gazetteer
            if place_lower in self.ROME_GAZETTEER:
                rome_places.append(place)
                continue
            
            # Check for partial matches (e.g., "the Colosseum" contains "colosseum")
            if any(landmark in place_lower for landmark in self.ROME_GAZETTEER):
                rome_places.append(place)
                continue
            
            # Check if context mentions Rome
            context_lower = place.context.lower()
            if any(rome_ref in context_lower for rome_ref in ["rome", "roma", "roman"]):
                rome_places.append(place)
        
        return rome_places
    
    def resolve_ambiguous_places(
        self, 
        places: List[PlaceMention], 
        context: str
    ) -> List[PlaceMention]:
        """
        Resolve ambiguous place names using conversation context.
        
        This method uses the conversation context to disambiguate place names
        that could refer to multiple locations. For example, "Pantheon" could
        refer to the one in Rome or Paris, but context mentioning Rome would
        resolve it to the Roman Pantheon.
        
        Args:
            places: List of PlaceMention objects that may be ambiguous
            context: Conversation context to help with disambiguation
            
        Returns:
            List of PlaceMention objects with updated confidence scores
        """
        if not context:
            return places
        
        context_lower = context.lower()
        resolved_places = []
        
        # Check if context mentions Rome
        rome_mentioned = any(
            rome_ref in context_lower 
            for rome_ref in ["rome", "roma", "roman", "italy", "italian"]
        )
        
        for place in places:
            place_lower = place.name.lower()
            
            # Ambiguous places that exist in multiple cities
            ambiguous_names = {
                "pantheon": ["rome", "paris"],
                "forum": ["rome", "roman"],
                "colosseum": ["rome"],
                "capitol": ["rome", "washington"],
            }
            
            # Check if place is ambiguous
            is_ambiguous = any(
                ambig in place_lower 
                for ambig in ambiguous_names.keys()
            )
            
            if is_ambiguous and rome_mentioned:
                # Boost confidence if Rome is mentioned in context
                new_confidence = min(place.confidence + 0.2, 1.0)
                resolved_place = PlaceMention(
                    name=place.name,
                    entity_type=place.entity_type,
                    confidence=new_confidence,
                    span=place.span,
                    context=place.context
                )
                resolved_places.append(resolved_place)
            else:
                resolved_places.append(place)
        
        return resolved_places
    
    def _calculate_confidence(self, text: str, entity_type: str) -> float:
        """
        Calculate confidence score for an extracted place.
        
        Args:
            text: The extracted place name
            entity_type: The NER entity type (GPE, LOC, FAC)
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        text_lower = text.lower()
        
        # High confidence for known Rome places
        if text_lower in self.ROME_GAZETTEER:
            return 0.95
        
        # Medium-high confidence for longer place names
        if len(text) > 10:
            return 0.8
        
        # Base confidence by entity type
        confidence_by_type = {
            "GPE": 0.7,  # Geopolitical entity
            "LOC": 0.75,  # Location
            "FAC": 0.65,  # Facility
        }
        
        return confidence_by_type.get(entity_type, 0.6)
