"""
Logging configuration for the Rome Places Chatbot.

This module provides centralized logging configuration with appropriate
levels, formatters, and handlers for the application.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# Log levels
LOG_LEVEL_ERROR = logging.ERROR
LOG_LEVEL_WARNING = logging.WARNING
LOG_LEVEL_INFO = logging.INFO
LOG_LEVEL_DEBUG = logging.DEBUG


class SessionContextFilter(logging.Filter):
    """
    Logging filter that adds session ID to log records.
    
    This filter allows session-specific logging by adding a session_id
    field to each log record.
    """
    
    def __init__(self):
        super().__init__()
        self.session_id = None
    
    def set_session_id(self, session_id: str) -> None:
        """Set the current session ID for logging."""
        self.session_id = session_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add session_id to the log record."""
        if not hasattr(record, 'session_id'):
            record.session_id = self.session_id or "no-session"
        return True


# Global session context filter instance
_session_filter = SessionContextFilter()


def setup_logging(
    log_level: int = LOG_LEVEL_INFO,
    log_file: Optional[str] = None,
    log_to_console: bool = True
) -> None:
    """
    Set up logging configuration for the application.
    
    Configures logging with:
    - Appropriate log levels (ERROR, WARNING, INFO, DEBUG)
    - Timestamp, error type, and session ID in log messages
    - Console and/or file output
    - Stack traces for exceptions
    
    Args:
        log_level: Minimum log level to capture (default: INFO)
        log_file: Optional path to log file. If None, logs only to console.
        log_to_console: Whether to log to console (default: True)
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatter with timestamp, level, session ID, and message
    # Use a custom formatter that handles missing session_id gracefully
    class SafeFormatter(logging.Formatter):
        def format(self, record):
            if not hasattr(record, 'session_id'):
                record.session_id = "no-session"
            return super().format(record)
    
    formatter = SafeFormatter(
        fmt='%(asctime)s - %(levelname)s - [%(session_id)s] - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add session context filter
    root_logger.addFilter(_session_filter)
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log startup message
    root_logger.info("Logging configured - Level: %s, File: %s, Console: %s",
                     logging.getLevelName(log_level), log_file or "None", log_to_console)


def set_session_id(session_id: str) -> None:
    """
    Set the current session ID for logging context.
    
    This session ID will be included in all subsequent log messages
    until changed or cleared.
    
    Args:
        session_id: The session identifier to include in logs
    """
    _session_filter.set_session_id(session_id)


def clear_session_id() -> None:
    """Clear the current session ID from logging context."""
    _session_filter.set_session_id(None)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Name of the module (typically __name__)
    
    Returns:
        Logger instance configured with the application settings
    """
    return logging.getLogger(name)


# User-friendly error messages for common error types
ERROR_MESSAGES = {
    "storage_unavailable": "Unable to load conversation history. Starting fresh.",
    "storage_write_failed": "Unable to save conversation. Your messages may not be persisted.",
    "corrupted_data": "Previous conversation data corrupted. Starting new session.",
    "api_timeout": "I'm having trouble connecting to my knowledge base. Please try again in a moment.",
    "api_rate_limit": "Too many requests. Please wait a moment and try again.",
    "api_error": "I'm experiencing technical difficulties. Please try again later.",
    "geocoding_failed": "I can't show that location on the map right now, but I can still tell you about it.",
    "geocoding_unavailable": "Map service temporarily unavailable. Text responses are still available.",
    "vector_store_unavailable": "Knowledge base temporarily unavailable. Responses may be limited.",
    "place_extraction_failed": "Having trouble identifying places in the text.",
    "unknown_error": "An unexpected error occurred. Please try again."
}


def get_user_friendly_error(error_type: str) -> str:
    """
    Get a user-friendly error message for a given error type.
    
    Args:
        error_type: The type of error (key in ERROR_MESSAGES)
    
    Returns:
        User-friendly error message
    """
    return ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown_error"])


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: str,
    session_id: Optional[str] = None
) -> None:
    """
    Log an error with full context including stack trace.
    
    Args:
        logger: Logger instance to use
        error: The exception that occurred
        context: Description of what was being done when error occurred
        session_id: Optional session ID for context
    """
    if session_id:
        set_session_id(session_id)
    
    logger.error(
        f"{context} - Error: {type(error).__name__}: {str(error)}",
        exc_info=True,
        extra={"error_type": type(error).__name__}
    )


def log_warning_with_context(
    logger: logging.Logger,
    message: str,
    session_id: Optional[str] = None
) -> None:
    """
    Log a warning for degraded functionality.
    
    Args:
        logger: Logger instance to use
        message: Warning message
        session_id: Optional session ID for context
    """
    if session_id:
        set_session_id(session_id)
    
    logger.warning(message)
