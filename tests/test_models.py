"""
Property-based tests for data models.

This module contains property-based tests using Hypothesis to verify
universal properties of the data models across all valid inputs.
"""

import json
from datetime import datetime
from hypothesis import given, strategies as st, settings
from src.models import Message


# Custom strategy for generating datetime objects that are JSON-serializable
def datetime_strategy():
    """Generate datetime objects that can be serialized to ISO format."""
    return st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2100, 12, 31)
    )


def message_to_json(message: Message) -> str:
    """
    Serialize a Message object to JSON string.
    
    Args:
        message: The Message object to serialize
        
    Returns:
        JSON string representation of the message
    """
    return json.dumps({
        "role": message.role,
        "content": message.content,
        "timestamp": message.timestamp.isoformat(),
        "session_id": message.session_id,
        "metadata": message.metadata
    })


def json_to_message(json_str: str) -> Message:
    """
    Deserialize a JSON string to a Message object.
    
    Args:
        json_str: JSON string representation of a message
        
    Returns:
        Reconstructed Message object
    """
    data = json.loads(json_str)
    return Message(
        role=data["role"],
        content=data["content"],
        timestamp=datetime.fromisoformat(data["timestamp"]),
        session_id=data["session_id"],
        metadata=data.get("metadata", {})
    )


# Feature: rome-places-chatbot, Property 1: Message Persistence Round-Trip
@given(
    role=st.sampled_from(["user", "assistant"]),
    content=st.text(min_size=1, max_size=1000),
    timestamp=datetime_strategy(),
    session_id=st.text(min_size=1, max_size=100),
    metadata=st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.one_of(
            st.text(max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.lists(st.text(max_size=50), max_size=10)
        ),
        max_size=5
    )
)
@settings(max_examples=20)
def test_message_persistence_roundtrip(role, content, timestamp, session_id, metadata):
    """
    **Validates: Requirements 1.1, 1.2, 1.3**
    
    Property 1: Message Persistence Round-Trip
    
    For any message (user or assistant) with content, timestamp, and session identifier,
    serializing the message to JSON and then deserializing it back should return a message
    with identical content, timestamp, and session_id.
    
    This test verifies that:
    1. Any Message can be serialized to JSON
    2. The serialized JSON can be deserialized back to a Message
    3. All fields match exactly after the round-trip
    """
    # Create original message
    original = Message(
        role=role,
        content=content,
        timestamp=timestamp,
        session_id=session_id,
        metadata=metadata
    )
    
    # Serialize to JSON
    json_str = message_to_json(original)
    
    # Deserialize back to Message
    retrieved = json_to_message(json_str)
    
    # Verify all fields match exactly
    assert retrieved.role == original.role, \
        f"Role mismatch: {retrieved.role} != {original.role}"
    
    assert retrieved.content == original.content, \
        f"Content mismatch: {retrieved.content} != {original.content}"
    
    assert retrieved.timestamp == original.timestamp, \
        f"Timestamp mismatch: {retrieved.timestamp} != {original.timestamp}"
    
    assert retrieved.session_id == original.session_id, \
        f"Session ID mismatch: {retrieved.session_id} != {original.session_id}"
    
    assert retrieved.metadata == original.metadata, \
        f"Metadata mismatch: {retrieved.metadata} != {original.metadata}"
