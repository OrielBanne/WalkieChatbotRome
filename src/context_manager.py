"""
Context Manager for the Rome Places Chatbot.

This module provides conversation context building and management functionality,
including token-aware history formatting, semantic similarity-based history
selection, and ChatML formatting for OpenAI API integration.
"""

from typing import List
from datetime import datetime

from src.models import Message
from src.session_manager import SessionManager
from src.config import MAX_CONTEXT_TOKENS


class ContextManager:
    """
    Manages conversation context and history integration for the chatbot.
    
    The ContextManager handles:
    - Building context strings with token management (sliding window)
    - Adding messages to conversation history
    - Selecting relevant historical messages using semantic similarity
    - Formatting history in ChatML format for OpenAI API
    """
    
    def __init__(self, session_manager: SessionManager):
        """
        Initialize the ContextManager.
        
        Args:
            session_manager: SessionManager instance for persistence
        """
        self.session_manager = session_manager
    
    def build_context(self, query: str, history: List[Message], max_tokens: int = None) -> str:
        """
        Build a context string from query and conversation history with token management.
        
        Uses a sliding window approach to include as much relevant history as possible
        while staying within the token limit. Formats the result in ChatML format
        for OpenAI API compatibility.
        
        Args:
            query: The current user query
            history: List of previous messages in chronological order
            max_tokens: Maximum number of tokens to include (uses config default if None)
            
        Returns:
            Formatted context string in ChatML format
        """
        if max_tokens is None:
            max_tokens = MAX_CONTEXT_TOKENS
        
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        def estimate_tokens(text: str) -> int:
            return len(text) // 4
        
        # Start with the current query
        query_tokens = estimate_tokens(query)
        remaining_tokens = max_tokens - query_tokens
        
        # Build context from most recent messages, working backwards
        context_messages = []
        
        for message in reversed(history):
            message_text = self._format_message_chatml(message)
            message_tokens = estimate_tokens(message_text)
            
            if message_tokens <= remaining_tokens:
                context_messages.insert(0, message)
                remaining_tokens -= message_tokens
            else:
                # Stop if we can't fit more messages
                break
        
        # Format the context in ChatML format
        context_parts = []
        
        for message in context_messages:
            context_parts.append(self._format_message_chatml(message))
        
        # Add the current query
        context_parts.append(f"<|im_start|>user\n{query}<|im_end|>")
        
        return "\n".join(context_parts)
    
    def add_to_history(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            session_id: The session identifier
            role: The message role ("user" or "assistant")
            content: The message content
        """
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            session_id=session_id,
            metadata={}
        )
        
        self.session_manager.save_message(session_id, message)
    
    def get_relevant_history(self, query: str, history: List[Message], k: int = 5) -> List[Message]:
        """
        Get the k most relevant historical messages for a query.
        
        Uses semantic similarity to select messages that are most relevant
        to the current query. For now, implements a simple keyword-based
        similarity as a baseline (can be enhanced with embeddings later).
        
        Args:
            query: The current user query
            history: List of all historical messages
            k: Number of relevant messages to return
            
        Returns:
            List of up to k most relevant messages in chronological order
        """
        if not history:
            return []
        
        # Simple keyword-based similarity scoring
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Score each message by keyword overlap
        scored_messages = []
        for message in history:
            content_lower = message.content.lower()
            content_words = set(content_lower.split())
            
            # Calculate Jaccard similarity
            intersection = query_words & content_words
            union = query_words | content_words
            
            if union:
                similarity = len(intersection) / len(union)
            else:
                similarity = 0.0
            
            scored_messages.append((similarity, message))
        
        # Sort by similarity (descending) and take top k
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        relevant_messages = [msg for score, msg in scored_messages[:k]]
        
        # Return in chronological order
        relevant_messages.sort(key=lambda m: m.timestamp)
        
        return relevant_messages
    
    def _format_message_chatml(self, message: Message) -> str:
        """
        Format a message in ChatML format for OpenAI API.
        
        Args:
            message: The message to format
            
        Returns:
            Formatted message string
        """
        return f"<|im_start|>{message.role}\n{message.content}<|im_end|>"
