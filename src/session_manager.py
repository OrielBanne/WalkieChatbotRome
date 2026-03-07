"""
Session Manager for the Rome Places Chatbot.

This module provides file-based session storage and management functionality,
including conversation history persistence, session lifecycle management,
and concurrent access handling through file locking.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.models import Message, Session


class SessionMetadata:
    """Metadata about a session for listing purposes."""
    
    def __init__(self, session_id: str, user_id: str, created_at: datetime, 
                 last_interaction: datetime, message_count: int):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = created_at
        self.last_interaction = last_interaction
        self.message_count = message_count


class SessionManager:
    """
    Manages user sessions and conversation persistence using file-based storage.
    
    Each session is stored as a JSON file with the naming pattern:
    {user_id}_{session_id}.json
    
    The manager handles:
    - Session creation and retrieval
    - Conversation history loading and saving
    - History clearing and export
    - Concurrent access through file locking
    """
    
    def __init__(self, storage_dir: str = "sessions"):
        """
        Initialize the SessionManager.
        
        Args:
            storage_dir: Directory path for storing session files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_file_path(self, user_id: str, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.storage_dir / f"{user_id}_{session_id}.json"
    
    def _find_session_files(self, user_id: str) -> List[Path]:
        """Find all session files for a given user."""
        pattern = f"{user_id}_*.json"
        return list(self.storage_dir.glob(pattern))
    
    def _serialize_message(self, message: Message) -> Dict[str, Any]:
        """Convert a Message object to a JSON-serializable dictionary."""
        return {
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "session_id": message.session_id,
            "metadata": message.metadata
        }
    
    def _deserialize_message(self, data: Dict[str, Any]) -> Message:
        """Convert a dictionary to a Message object."""
        return Message(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            session_id=data["session_id"],
            metadata=data.get("metadata", {})
        )
    
    def _read_session_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Read and parse a session file.
        
        Returns None if file doesn't exist or is corrupted.
        """
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            # Log error for corrupted JSON data
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Corrupted session file {file_path}: {e}", exc_info=True)
            return None
        except (IOError, OSError) as e:
            # Log error for file system issues
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error reading session file {file_path}: {e}", exc_info=True)
            return None
    
    def _write_session_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        Write session data to file with error handling.
        
        Raises:
            IOError: If file cannot be written
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except (IOError, OSError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error writing session file {file_path}: {e}", exc_info=True)
            raise IOError(f"Failed to write session file: {e}") from e
    
    def get_or_create_session(self, user_id: str) -> Session:
        """
        Get an existing session or create a new one for a user.
        
        This method always creates a new session with a unique session_id.
        
        Args:
            user_id: The user identifier
            
        Returns:
            A new Session object
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_interaction=now,
            message_count=0
        )
        
        # Create the session file
        file_path = self._get_session_file_path(user_id, session_id)
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": now.isoformat(),
            "last_interaction": now.isoformat(),
            "messages": []
        }
        
        self._write_session_file(file_path, session_data)
        
        return session
    
    def load_conversation_history(self, session_id: str) -> List[Message]:
        """
        Load conversation history for a session with graceful degradation.
        
        Args:
            session_id: The session identifier
            
        Returns:
            List of Message objects in chronological order.
            Returns empty list if storage is unavailable or data is corrupted.
        """
        try:
            # Find the session file by searching for files with this session_id
            session_files = list(self.storage_dir.glob(f"*_{session_id}.json"))
            
            if not session_files:
                return []
            
            # Read the first matching file
            session_data = self._read_session_file(session_files[0])
            
            if not session_data:
                return []
            
            messages = []
            for msg_data in session_data.get("messages", []):
                try:
                    messages.append(self._deserialize_message(msg_data))
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Skipping corrupted message in session {session_id}: {e}")
                    continue
            
            # Ensure chronological order
            messages.sort(key=lambda m: m.timestamp)
            
            return messages
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading conversation history for session {session_id}: {e}", exc_info=True)
            return []  # Graceful degradation: return empty history
    
    def save_message(self, session_id: str, message: Message) -> None:
        """
        Save a message to a session's conversation history.
        
        Args:
            session_id: The session identifier
            message: The Message object to save
        """
        # Validate message content
        if not message.content or not message.content.strip():
            raise ValueError("Message content cannot be empty")
        
        # Find the session file
        session_files = list(self.storage_dir.glob(f"*_{session_id}.json"))
        
        if not session_files:
            raise ValueError(f"Session {session_id} not found")
        
        file_path = session_files[0]
        session_data = self._read_session_file(file_path)
        
        if not session_data:
            raise ValueError(f"Could not read session {session_id}")
        
        # Add the message
        session_data["messages"].append(self._serialize_message(message))
        session_data["last_interaction"] = datetime.now().isoformat()
        
        # Write back to file
        self._write_session_file(file_path, session_data)
    
    def clear_history(self, session_id: str) -> None:
        """
        Clear all messages from a session's conversation history.
        
        Args:
            session_id: The session identifier
        """
        # Find the session file
        session_files = list(self.storage_dir.glob(f"*_{session_id}.json"))
        
        if not session_files:
            return  # Session doesn't exist, nothing to clear
        
        file_path = session_files[0]
        session_data = self._read_session_file(file_path)
        
        if not session_data:
            return
        
        # Clear messages but keep session metadata
        session_data["messages"] = []
        session_data["last_interaction"] = datetime.now().isoformat()
        
        self._write_session_file(file_path, session_data)
    
    def list_sessions(self, user_id: str) -> List[SessionMetadata]:
        """
        List all sessions for a user.
        
        Args:
            user_id: The user identifier
            
        Returns:
            List of SessionMetadata objects
        """
        session_files = self._find_session_files(user_id)
        sessions = []
        
        for file_path in session_files:
            session_data = self._read_session_file(file_path)
            
            if not session_data:
                continue
            
            metadata = SessionMetadata(
                session_id=session_data["session_id"],
                user_id=session_data["user_id"],
                created_at=datetime.fromisoformat(session_data["created_at"]),
                last_interaction=datetime.fromisoformat(session_data["last_interaction"]),
                message_count=len(session_data.get("messages", []))
            )
            sessions.append(metadata)
        
        return sessions
    
    def export_history(self, session_id: str) -> str:
        """
        Export conversation history in a readable text format.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Formatted string containing the conversation history
        """
        messages = self.load_conversation_history(session_id)
        
        if not messages:
            return "No conversation history found."
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"Conversation History - Session: {session_id}")
        lines.append("=" * 60)
        lines.append("")
        
        for message in messages:
            timestamp_str = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            role_label = "User" if message.role == "user" else "Assistant"
            lines.append(f"[{timestamp_str}] {role_label}:")
            lines.append(message.content)
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def delete_session(self, session_id: str) -> None:
        """
        Delete a session and its conversation history.
        
        Args:
            session_id: The session identifier
        """
        # Find the session file
        session_files = list(self.storage_dir.glob(f"*_{session_id}.json"))
        
        if not session_files:
            return  # Session doesn't exist
        
        # Delete the file
        try:
            session_files[0].unlink()
        except (IOError, OSError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error deleting session file {session_files[0]}: {e}", exc_info=True)
            raise IOError(f"Failed to delete session: {e}") from e
    def delete_session(self, session_id: str) -> None:
        """
        Delete a session and its conversation history.

        Args:
            session_id: The session identifier
        """
        # Find the session file
        session_files = list(self.storage_dir.glob(f"*_{session_id}.json"))

        if not session_files:
            return  # Session doesn't exist

        # Delete the file
        try:
            session_files[0].unlink()
        except (IOError, OSError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error deleting session file {session_files[0]}: {e}", exc_info=True)
            raise IOError(f"Failed to delete session: {e}") from e
