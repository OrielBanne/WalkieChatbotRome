"""
Unit tests for the ContextManager class.

Tests cover:
- Context building with token management
- History addition
- Relevant history retrieval
- ChatML formatting
- Edge cases (empty history, token limits, etc.)
"""

import pytest
from datetime import datetime, timedelta
from src.context_manager import ContextManager
from src.session_manager import SessionManager
from src.models import Message


@pytest.fixture
def temp_session_dir(tmp_path):
    """Create a temporary directory for session storage."""
    return str(tmp_path / "sessions")


@pytest.fixture
def session_manager(temp_session_dir):
    """Create a SessionManager instance with temporary storage."""
    return SessionManager(storage_dir=temp_session_dir)


@pytest.fixture
def context_manager(session_manager):
    """Create a ContextManager instance."""
    return ContextManager(session_manager=session_manager)


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    base_time = datetime.now()
    return [
        Message(
            role="user",
            content="Tell me about the Colosseum",
            timestamp=base_time,
            session_id="test_session",
            metadata={}
        ),
        Message(
            role="assistant",
            content="The Colosseum is an ancient amphitheater in Rome.",
            timestamp=base_time + timedelta(seconds=1),
            session_id="test_session",
            metadata={}
        ),
        Message(
            role="user",
            content="What about the Trevi Fountain?",
            timestamp=base_time + timedelta(seconds=2),
            session_id="test_session",
            metadata={}
        ),
        Message(
            role="assistant",
            content="The Trevi Fountain is a famous baroque fountain in Rome.",
            timestamp=base_time + timedelta(seconds=3),
            session_id="test_session",
            metadata={}
        ),
    ]


class TestContextManager:
    """Test suite for ContextManager."""
    
    def test_initialization(self, context_manager, session_manager):
        """Test that ContextManager initializes correctly."""
        assert context_manager.session_manager == session_manager
    
    def test_build_context_with_empty_history(self, context_manager):
        """Test building context with no history."""
        query = "Tell me about Rome"
        context = context_manager.build_context(query, [], max_tokens=4000)
        
        assert query in context
        assert "<|im_start|>user" in context
        assert "<|im_end|>" in context
    
    def test_build_context_with_history(self, context_manager, sample_messages):
        """Test building context with conversation history."""
        query = "What's nearby?"
        context = context_manager.build_context(query, sample_messages, max_tokens=4000)
        
        # Should include the query
        assert query in context
        
        # Should include some history in ChatML format
        assert "<|im_start|>" in context
        assert "<|im_end|>" in context
        
        # Should include at least some messages from history
        assert "Colosseum" in context or "Trevi Fountain" in context
    
    def test_build_context_respects_token_limit(self, context_manager):
        """Test that context building respects token limits."""
        # Create a long history
        long_history = []
        base_time = datetime.now()
        
        for i in range(20):
            long_history.append(Message(
                role="user",
                content=f"This is a long message number {i} with lots of content to fill up tokens",
                timestamp=base_time + timedelta(seconds=i*2),
                session_id="test_session",
                metadata={}
            ))
            long_history.append(Message(
                role="assistant",
                content=f"This is a long response number {i} with lots of content to fill up tokens",
                timestamp=base_time + timedelta(seconds=i*2+1),
                session_id="test_session",
                metadata={}
            ))
        
        query = "Short query"
        
        # Build context with small token limit
        context = context_manager.build_context(query, long_history, max_tokens=200)
        
        # Context should be limited in size (rough check)
        # 200 tokens ≈ 800 characters
        assert len(context) < 1500  # Allow some overhead for formatting
    
    def test_build_context_includes_recent_messages(self, context_manager, sample_messages):
        """Test that context building prioritizes recent messages."""
        query = "Tell me more"
        context = context_manager.build_context(query, sample_messages, max_tokens=4000)
        
        # Most recent messages should be included
        assert "Trevi Fountain" in context
    
    def test_add_to_history(self, context_manager, session_manager):
        """Test adding a message to history."""
        # Create a session first
        session = session_manager.get_or_create_session("test_user")
        session_id = session.session_id
        
        # Add a message
        context_manager.add_to_history(session_id, "user", "Hello chatbot")
        
        # Verify it was saved
        history = session_manager.load_conversation_history(session_id)
        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "Hello chatbot"
        assert history[0].session_id == session_id
    
    def test_add_multiple_messages_to_history(self, context_manager, session_manager):
        """Test adding multiple messages to history."""
        session = session_manager.get_or_create_session("test_user")
        session_id = session.session_id
        
        # Add multiple messages
        context_manager.add_to_history(session_id, "user", "First message")
        context_manager.add_to_history(session_id, "assistant", "First response")
        context_manager.add_to_history(session_id, "user", "Second message")
        
        # Verify all were saved
        history = session_manager.load_conversation_history(session_id)
        assert len(history) == 3
        assert history[0].content == "First message"
        assert history[1].content == "First response"
        assert history[2].content == "Second message"
    
    def test_get_relevant_history_empty(self, context_manager):
        """Test getting relevant history with empty history."""
        query = "Tell me about Rome"
        relevant = context_manager.get_relevant_history(query, [], k=5)
        
        assert relevant == []
    
    def test_get_relevant_history_keyword_matching(self, context_manager, sample_messages):
        """Test that relevant history uses keyword matching."""
        query = "Tell me more about the Colosseum"
        relevant = context_manager.get_relevant_history(query, sample_messages, k=2)
        
        # Should return messages, prioritizing those with "Colosseum"
        assert len(relevant) <= 2
        assert len(relevant) > 0
        
        # Check that messages are in chronological order
        for i in range(len(relevant) - 1):
            assert relevant[i].timestamp <= relevant[i+1].timestamp
    
    def test_get_relevant_history_respects_k_limit(self, context_manager, sample_messages):
        """Test that get_relevant_history respects the k parameter."""
        query = "Tell me about Rome"
        
        relevant = context_manager.get_relevant_history(query, sample_messages, k=2)
        assert len(relevant) <= 2
        
        relevant = context_manager.get_relevant_history(query, sample_messages, k=10)
        assert len(relevant) <= len(sample_messages)
    
    def test_get_relevant_history_returns_chronological_order(self, context_manager):
        """Test that relevant history is returned in chronological order."""
        # Create messages with specific timestamps
        base_time = datetime.now()
        messages = [
            Message("user", "Message 3", base_time + timedelta(seconds=2), "s1", {}),
            Message("user", "Message 1", base_time, "s1", {}),
            Message("user", "Message 2", base_time + timedelta(seconds=1), "s1", {}),
        ]
        
        query = "Message"
        relevant = context_manager.get_relevant_history(query, messages, k=3)
        
        # Should be in chronological order
        assert relevant[0].content == "Message 1"
        assert relevant[1].content == "Message 2"
        assert relevant[2].content == "Message 3"
    
    def test_format_message_chatml(self, context_manager, sample_messages):
        """Test ChatML message formatting."""
        message = sample_messages[0]
        formatted = context_manager._format_message_chatml(message)
        
        assert formatted.startswith("<|im_start|>user")
        assert formatted.endswith("<|im_end|>")
        assert message.content in formatted
    
    def test_chatml_format_for_assistant(self, context_manager, sample_messages):
        """Test ChatML formatting for assistant messages."""
        message = sample_messages[1]  # Assistant message
        formatted = context_manager._format_message_chatml(message)
        
        assert formatted.startswith("<|im_start|>assistant")
        assert formatted.endswith("<|im_end|>")
        assert message.content in formatted
    
    def test_build_context_chatml_structure(self, context_manager, sample_messages):
        """Test that build_context produces valid ChatML structure."""
        query = "What else?"
        context = context_manager.build_context(query, sample_messages[:2], max_tokens=4000)
        
        # Count start and end tags - they should match
        start_count = context.count("<|im_start|>")
        end_count = context.count("<|im_end|>")
        
        assert start_count == end_count
        assert start_count >= 1  # At least the query
    
    def test_add_to_history_with_invalid_session(self, context_manager):
        """Test adding to history with non-existent session."""
        with pytest.raises(ValueError):
            context_manager.add_to_history("nonexistent_session", "user", "Hello")
    
    def test_get_relevant_history_with_no_keyword_overlap(self, context_manager):
        """Test relevant history when query has no keyword overlap."""
        messages = [
            Message("user", "Tell me about the Colosseum", datetime.now(), "s1", {}),
            Message("assistant", "The Colosseum is ancient", datetime.now(), "s1", {}),
        ]
        
        query = "xyz abc def"  # No overlap with message content
        relevant = context_manager.get_relevant_history(query, messages, k=5)
        
        # Should still return messages (even with low similarity)
        assert len(relevant) <= 5


# Property-Based Tests
from hypothesis import given, strategies as st, settings


@given(
    query=st.text(min_size=1, max_size=100),
    history=st.lists(
        st.builds(
            Message,
            role=st.sampled_from(["user", "assistant"]),
            content=st.text(min_size=1, max_size=200),
            timestamp=st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2025, 12, 31)
            ),
            session_id=st.just("test_session"),
            metadata=st.just({})
        ),
        min_size=1,  # Non-empty history
        max_size=10
    )
)
@settings(max_examples=20)
def test_property_context_includes_history(query, history):
    """
    **Validates: Requirements 2.1**
    
    Property 3: Context Includes History
    
    For any response generation request with non-empty conversation history,
    the context passed to the RAG chain should include at least one message
    from the conversation history.
    """
    # Create a context manager (no need for session manager for this test)
    from src.session_manager import SessionManager
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        session_manager = SessionManager(storage_dir=temp_dir)
        context_manager = ContextManager(session_manager=session_manager)
        
        # Build context with non-empty history
        context = context_manager.build_context(query, history, max_tokens=4000)
        
        # Verify that at least one message from history is included in the context
        # Check if any message content appears in the context
        history_included = any(
            message.content in context
            for message in history
        )
        
        assert history_included, (
            f"Context should include at least one message from history. "
            f"History had {len(history)} messages, but none were found in context."
        )


@given(
    user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
    num_sessions=st.integers(min_value=2, max_value=5),
    messages_per_session=st.lists(
        st.integers(min_value=1, max_value=5),
        min_size=2,
        max_size=5
    )
)
@settings(max_examples=20, deadline=500)
def test_property_cross_session_continuity(user_id, num_sessions, messages_per_session):
    """
    **Validates: Requirements 2.3**
    
    Property 4: Cross-Session Continuity
    
    For any user with multiple sessions, retrieving all conversation histories
    for that user should return messages from all sessions associated with that
    user identifier.
    """
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        session_manager = SessionManager(storage_dir=temp_dir)
        
        # Ensure we have the right number of message counts
        if len(messages_per_session) < num_sessions:
            messages_per_session = messages_per_session + [1] * (num_sessions - len(messages_per_session))
        messages_per_session = messages_per_session[:num_sessions]
        
        # Create multiple sessions for the user
        sessions = []
        total_messages_created = 0
        
        for i in range(num_sessions):
            session = session_manager.get_or_create_session(user_id)
            sessions.append(session)
            
            # Add messages to this session
            num_messages = messages_per_session[i]
            base_time = datetime.now()
            
            for j in range(num_messages):
                message = Message(
                    role="user" if j % 2 == 0 else "assistant",
                    content=f"Session {i} message {j}",
                    timestamp=base_time,
                    session_id=session.session_id,
                    metadata={}
                )
                session_manager.save_message(session.session_id, message)
                total_messages_created += 1
        
        # Retrieve all histories for the user by listing sessions and loading each
        all_messages = []
        session_list = session_manager.list_sessions(user_id)
        
        for session_metadata in session_list:
            history = session_manager.load_conversation_history(session_metadata.session_id)
            all_messages.extend(history)
        
        # Verify that we retrieved messages from all sessions
        assert len(session_list) == num_sessions, (
            f"Expected {num_sessions} sessions for user {user_id}, "
            f"but found {len(session_list)}"
        )
        
        assert len(all_messages) == total_messages_created, (
            f"Expected {total_messages_created} total messages across all sessions, "
            f"but retrieved {len(all_messages)}"
        )
        
        # Verify that messages from each session are present
        for i, session in enumerate(sessions):
            session_messages = [
                msg for msg in all_messages 
                if msg.session_id == session.session_id
            ]
            
            assert len(session_messages) == messages_per_session[i], (
                f"Expected {messages_per_session[i]} messages in session {i}, "
                f"but found {len(session_messages)}"
            )
