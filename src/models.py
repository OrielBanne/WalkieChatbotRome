"""
Data models for the Rome Places Chatbot.

This module defines the core data structures used throughout the application
for managing conversations, sessions, place information, and geographic data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


@dataclass
class Message:
    """
    Represents a single message in a conversation.
    
    Attributes:
        role: The message sender role ("user" or "assistant")
        content: The text content of the message
        timestamp: When the message was created
        session_id: The session this message belongs to
        metadata: Optional additional data (extracted_places, sources, etc.)
    """
    role: str
    content: str
    timestamp: datetime
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """
    Represents a conversation session between a user and the chatbot.
    
    Attributes:
        session_id: Unique identifier for the session
        user_id: Identifier for the user
        created_at: When the session was created
        last_interaction: Timestamp of the most recent message
        message_count: Total number of messages in the session
    """
    session_id: str
    user_id: str
    created_at: datetime
    last_interaction: datetime
    message_count: int


@dataclass
class PlaceMention:
    """
    Represents a place name extracted from text using NLP.
    
    Attributes:
        name: The extracted place name
        entity_type: The NER entity type (GPE, LOC, FAC)
        confidence: Confidence score for the extraction (0.0 to 1.0)
        span: Character positions in the source text (start, end)
        context: Surrounding text for disambiguation
    """
    name: str
    entity_type: str
    confidence: float
    span: Tuple[int, int]
    context: str


@dataclass
class PlaceMarker:
    """
    Represents a place to be displayed on a map.
    
    Attributes:
        name: The place name
        coordinates: Geographic coordinates (latitude, longitude)
        place_type: Category of place (landmark, restaurant, attraction, etc.)
        description: Optional description text
        icon: Icon identifier for the map marker
    """
    name: str
    coordinates: Tuple[float, float]
    place_type: str
    description: Optional[str]
    icon: str


@dataclass
class Coordinates:
    """
    Represents geographic coordinates with metadata.
    
    Attributes:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        accuracy: Accuracy level ("exact", "approximate", "fallback")
        source: Where the coordinates came from ("geocoder", "manual", "cache")
    """
    latitude: float
    longitude: float
    accuracy: str
    source: str
