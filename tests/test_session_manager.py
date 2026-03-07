"""
Tests for SessionManager.

This module contains both unit tests and property-based tests for the
SessionManager class, verifying session management, conversation persistence,
and file-based storage operations.
"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import pytest
from hypothesis import given, strategies as st, settings

from src.session_manager import SessionManager, SessionMetadata
from src.models import Message


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for session storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def session_manager(temp_storage_dir):
    """Create a SessionManager instance with temporary storage."""
    return SessionManager(storage_dir=temp_storage_dir)


# ============================================================================
# Unit Tests
# ============================================================================

def test_session_creation_generates_uuid(session_manager):
    """Test that session creation generates a valid UUID."""
    session = session_manager.get_or_create_session("user123")
    
    assert session.session_id is not None
    assert len(session.session_id) == 36  # UUID format
    assert session.user_id == "user123"
    assert session.message_count == 0


def test_empty_message_rejected(session_manager):
    """Test that empty messages are rejected."""
    session = session_manager.get_or_create_session("user123")
    
    with pytest.raises(ValueError):
        message = Message(
            role="user",
            content="",
            timestamp=datetime.now(),
            session_id=session.session_id
        )
        session_manager.save_message(session.session_id, message)


def test_whitespace_only_message_rejected(session_manager):
    """Test that whitespace-only messages are rejected."""
    session = session_manager.get_or_create_session("user123")
    
    with pytest.raises(ValueError):
        message = Message(
            role="user",
            content="   ",
            timestamp=datetime.now(),
            session_id=session.session_id
        )
        session_manager.save_message(session.session_id, message)


def test_load_nonexistent_session_returns_empty(session_manager):
    """Test that loading a non-existent session returns empty history."""
    history = session_manager.load_conversation_history("nonexistent-session-id")
    assert history == []


def test_save_and_load_single_message(session_manager):
    """Test saving and loading a single message."""
    session = session_manager.get_or_create_session("user123")
    
    message = Message(
        role="user",
        content="Hello, chatbot!",
        timestamp=datetime.now(),
        session_id=session.session_id
    )
    
    session_manager.save_message(session.session_id, message)
    history = session_manager.load_conversation_history(session.session_id)
    
    assert len(history) == 1
    assert history[0].content == "Hello, chatbot!"
    assert history[0].role == "user"


def test_save_multiple_messages_chronological_order(session_manager):
    """Test that multiple messages are stored in chronological order."""
    session = session_manager.get_or_create_session("user123")
    
    # Create messages with different timestamps
    messages = []
    for i in range(5):
        msg = Message(
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
            timestamp=datetime(2024, 1, 1, 12, i, 0),
            session_id=session.session_id
        )
        messages.append(msg)
        session_manager.save_message(session.session_id, msg)
    
    history = session_manager.load_conversation_history(session.session_id)
    
    assert len(history) == 5
    for i, msg in enumerate(history):
        assert msg.content == f"Message {i}"
        assert msg.timestamp == messages[i].timestamp


def test_clear_history(session_manager):
    """Test clearing conversation history."""
    session = session_manager.get_or_create_session("user123")
    
    # Add some messages
    for i in range(3):
        msg = Message(
            role="user",
            content=f"Message {i}",
            timestamp=datetime.now(),
            session_id=session.session_id
        )
        session_manager.save_message(session.session_id, msg)
    
    # Verify messages exist
    history = session_manager.load_conversation_history(session.session_id)
    assert len(history) == 3
    
    # Clear history
    session_manager.clear_history(session.session_id)
    
    # Verify history is empty
    history = session_manager.load_conversation_history(session.session_id)
    assert history == []


def test_clear_nonexistent_session(session_manager):
    """Test that clearing a non-existent session doesn't raise an error."""
    # Should not raise an exception
    session_manager.clear_history("nonexistent-session-id")


def test_list_sessions_single_user(session_manager):
    """Test listing sessions for a single user."""
    # Create multiple sessions for the same user
    session1 = session_manager.get_or_create_session("user123")
    session2 = session_manager.get_or_create_session("user123")
    
    sessions = session_manager.list_sessions("user123")
    
    assert len(sessions) == 2
    session_ids = [s.session_id for s in sessions]
    assert session1.session_id in session_ids
    assert session2.session_id in session_ids


def test_list_sessions_multiple_users(session_manager):
    """Test that sessions are properly isolated by user."""
    session_manager.get_or_create_session("user1")
    session_manager.get_or_create_session("user1")
    session_manager.get_or_create_session("user2")
    
    user1_sessions = session_manager.list_sessions("user1")
    user2_sessions = session_manager.list_sessions("user2")
    
    assert len(user1_sessions) == 2
    assert len(user2_sessions) == 1


def test_export_history_empty_session(session_manager):
    """Test exporting history from an empty session."""
    export = session_manager.export_history("nonexistent-session")
    assert "No conversation history found" in export


def test_export_history_with_messages(session_manager):
    """Test exporting conversation history."""
    session = session_manager.get_or_create_session("user123")
    
    # Add messages
    msg1 = Message(
        role="user",
        content="Hello!",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        session_id=session.session_id
    )
    msg2 = Message(
        role="assistant",
        content="Hi there!",
        timestamp=datetime(2024, 1, 1, 12, 0, 5),
        session_id=session.session_id
    )
    
    session_manager.save_message(session.session_id, msg1)
    session_manager.save_message(session.session_id, msg2)
    
    export = session_manager.export_history(session.session_id)
    
    assert "Hello!" in export
    assert "Hi there!" in export
    assert "User:" in export
    assert "Assistant:" in export
    assert session.session_id in export


def test_message_with_metadata(session_manager):
    """Test that message metadata is preserved."""
    session = session_manager.get_or_create_session("user123")
    
    message = Message(
        role="assistant",
        content="Check out the Colosseum!",
        timestamp=datetime.now(),
        session_id=session.session_id,
        metadata={
            "extracted_places": ["Colosseum"],
            "sources": ["https://example.com"]
        }
    )
    
    session_manager.save_message(session.session_id, message)
    history = session_manager.load_conversation_history(session.session_id)
    
    assert len(history) == 1
    assert history[0].metadata["extracted_places"] == ["Colosseum"]
    assert history[0].metadata["sources"] == ["https://example.com"]


# ============================================================================
# Property-Based Tests
# ============================================================================

def datetime_strategy():
    """Generate datetime objects that can be serialized to ISO format."""
    return st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2100, 12, 31)
    )


# Feature: rome-places-chatbot, Property 1: Message Persistence Round-Trip
@given(
    content=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),  # Ensure non-whitespace content
    role=st.sampled_from(["user", "assistant"]),
    timestamp=datetime_strategy()
)
@settings(max_examples=20, deadline=500)
def test_property_message_persistence_roundtrip(content, role, timestamp):
    """
    **Validates: Requirements 1.1, 1.2, 1.3**
    
    Property 1: Message Persistence Round-Trip
    
    For any message, persisting and retrieving should return identical content.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        manager = SessionManager(storage_dir=temp_dir)
        session = manager.get_or_create_session("test_user")
        
        message = Message(
            role=role,
            content=content,
            timestamp=timestamp,
            session_id=session.session_id
        )
        
        manager.save_message(session.session_id, message)
        history = manager.load_conversation_history(session.session_id)
        
        assert len(history) > 0
        retrieved = history[-1]
        assert retrieved.content == content
        assert retrieved.role == role
        assert retrieved.session_id == session.session_id
    finally:
        shutil.rmtree(temp_dir)


# Feature: rome-places-chatbot, Property 2: Chronological Message Ordering
@given(
    messages=st.lists(
        st.tuples(
            st.sampled_from(["user", "assistant"]),
            st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),  # Ensure non-whitespace content
            datetime_strategy()
        ),
        min_size=2,
        max_size=20
    )
)
@settings(max_examples=20, deadline=500)
def test_property_chronological_ordering(messages):
    """
    **Validates: Requirements 1.5**
    
    Property 2: Chronological Message Ordering
    
    For any set of messages, retrieval should return them in chronological order.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        manager = SessionManager(storage_dir=temp_dir)
        session = manager.get_or_create_session("test_user")
        
        # Save all messages
        for role, content, timestamp in messages:
            msg = Message(
                role=role,
                content=content,
                timestamp=timestamp,
                session_id=session.session_id
            )
            manager.save_message(session.session_id, msg)
        
        # Retrieve history
        history = manager.load_conversation_history(session.session_id)
        
        # Verify chronological order
        timestamps = [msg.timestamp for msg in history]
        assert timestamps == sorted(timestamps)
    finally:
        shutil.rmtree(temp_dir)


# Feature: rome-places-chatbot, Property 9: History Deletion Round-Trip
@given(
    messages=st.lists(
        st.tuples(
            st.sampled_from(["user", "assistant"]),
            st.text(min_size=1, max_size=100).filter(lambda x: x.strip())  # Ensure non-whitespace content
        ),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=20, deadline=500)
def test_property_history_deletion_roundtrip(messages):
    """
    **Validates: Requirements 5.1**
    
    Property 9: History Deletion Round-Trip
    
    For any session with messages, clearing history should result in empty retrieval.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        manager = SessionManager(storage_dir=temp_dir)
        session = manager.get_or_create_session("test_user")
        
        # Save messages
        for role, content in messages:
            msg = Message(
                role=role,
                content=content,
                timestamp=datetime.now(),
                session_id=session.session_id
            )
            manager.save_message(session.session_id, msg)
        
        # Verify messages exist
        history_before = manager.load_conversation_history(session.session_id)
        assert len(history_before) > 0
        
        # Clear history
        manager.clear_history(session.session_id)
        
        # Verify history is empty
        history_after = manager.load_conversation_history(session.session_id)
        assert history_after == []
    finally:
        shutil.rmtree(temp_dir)


# Feature: rome-places-chatbot, Property 10: Unique Session Identifiers
@given(user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126)))  # Printable ASCII only
@settings(max_examples=20)
def test_property_unique_session_identifiers(user_id):
    """
    **Validates: Requirements 5.2**
    
    Property 10: Unique Session Identifiers
    
    For any two consecutive session creations, IDs should be different.
    """
    # Filter out invalid filename characters
    if any(c in user_id for c in '/\\:*?"<>|'):
        return
    
    temp_dir = tempfile.mkdtemp()
    try:
        manager = SessionManager(storage_dir=temp_dir)
        
        session1 = manager.get_or_create_session(user_id)
        session2 = manager.get_or_create_session(user_id)
        
        assert session1.session_id != session2.session_id
    finally:
        shutil.rmtree(temp_dir)


# Feature: rome-places-chatbot, Property 11: Session Listing Completeness
@given(
    user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),  # Printable ASCII only
    num_sessions=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20)
def test_property_session_listing_completeness(user_id, num_sessions):
    """
    **Validates: Requirements 5.3**
    
    Property 11: Session Listing Completeness
    
    For any user with N sessions, listing should return exactly N session metadata objects.
    """
    # Filter out invalid filename characters
    if any(c in user_id for c in '/\\:*?"<>|'):
        return
    
    temp_dir = tempfile.mkdtemp()
    try:
        manager = SessionManager(storage_dir=temp_dir)
        
        # Create N sessions
        created_sessions = []
        for _ in range(num_sessions):
            session = manager.get_or_create_session(user_id)
            created_sessions.append(session)
        
        # List sessions
        listed_sessions = manager.list_sessions(user_id)
        
        # Verify count
        assert len(listed_sessions) == num_sessions
        
        # Verify all session IDs are present
        created_ids = {s.session_id for s in created_sessions}
        listed_ids = {s.session_id for s in listed_sessions}
        assert created_ids == listed_ids
    finally:
        shutil.rmtree(temp_dir)


# Feature: rome-places-chatbot, Property 12: History Export Round-Trip
@given(
    messages=st.lists(
        st.tuples(
            st.sampled_from(["user", "assistant"]),
            st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),  # Ensure non-whitespace content
            datetime_strategy()
        ),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=100)
def test_property_history_export_preserves_content(messages):
    """
    **Validates: Requirements 5.4**
    
    Property 12: History Export Round-Trip
    
    For any conversation history, exporting should preserve all message content, roles, and timestamps.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        manager = SessionManager(storage_dir=temp_dir)
        session = manager.get_or_create_session("test_user")
        
        # Save messages
        for role, content, timestamp in messages:
            msg = Message(
                role=role,
                content=content,
                timestamp=timestamp,
                session_id=session.session_id
            )
            manager.save_message(session.session_id, msg)
        
        # Export history
        export = manager.export_history(session.session_id)
        
        # Verify all message content is present in export
        for role, content, timestamp in messages:
            assert content in export
            
            # Verify role is present (as "User" or "Assistant")
            role_label = "User" if role == "user" else "Assistant"
            assert role_label in export
            
            # Verify timestamp is present (formatted as YYYY-MM-DD HH:MM:SS)
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            assert timestamp_str in export
    finally:
        shutil.rmtree(temp_dir)

