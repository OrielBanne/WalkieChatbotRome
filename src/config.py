"""
Configuration module for the Rome Places Chatbot.

This module loads environment variables, defines constants, and validates
required configuration settings for the application.
"""

import os
from pathlib import Path
from typing import Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


# ============================================================================
# OpenAI Configuration
# ============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_sm")


# ============================================================================
# Application Configuration
# ============================================================================

APP_TITLE = os.getenv("APP_TITLE", "Rome Places Chatbot")
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "4000"))
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))


# ============================================================================
# Geographic Configuration
# ============================================================================

# Rome city center coordinates (Piazza Venezia)
ROME_CENTER_LAT = float(os.getenv("ROME_CENTER_LAT", "41.9028"))
ROME_CENTER_LON = float(os.getenv("ROME_CENTER_LON", "12.4964"))
ROME_CENTER: Tuple[float, float] = (ROME_CENTER_LAT, ROME_CENTER_LON)

# Rome bounding box for geocoding bias: (min_lat, min_lon) to (max_lat, max_lon)
ROME_BBOX = ((41.8, 12.4), (41.95, 12.6))

# Default map zoom level
DEFAULT_MAP_ZOOM = 13


# ============================================================================
# Geocoding Configuration
# ============================================================================

GEOCODING_USER_AGENT = os.getenv("GEOCODING_USER_AGENT", "rome_places_chatbot")
GEOCODING_MAX_RETRIES = 3
GEOCODING_TIMEOUT = 10  # seconds


# ============================================================================
# File Paths
# ============================================================================

# Session storage directory
SESSION_STORAGE_PATH = Path(os.getenv("SESSION_STORAGE_PATH", "./sessions"))

# Vector store directory
VECTOR_STORE_PATH = Path(os.getenv("VECTOR_STORE_PATH", "./data/vector_store"))

# Data directory for ingested content
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))


# ============================================================================
# Text Chunking Configuration
# ============================================================================

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))


# ============================================================================
# Session Management
# ============================================================================

SESSION_RETENTION_DAYS = int(os.getenv("SESSION_RETENTION_DAYS", "90"))


# ============================================================================
# RAG Configuration
# ============================================================================

# Number of document chunks to retrieve for RAG
RAG_RETRIEVAL_K = int(os.getenv("RAG_RETRIEVAL_K", "5"))

# Maximum retries for API calls
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))

# API timeout in seconds
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))


# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# ============================================================================
# Configuration Validation
# ============================================================================

def validate_configuration() -> None:
    """
    Validate that all required configuration is present and valid.
    
    Raises:
        ConfigurationError: If required configuration is missing or invalid
    """
    errors = []
    
    # Check required environment variables
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY environment variable is required")
    
    # Validate numeric configurations
    if MAX_CONTEXT_TOKENS <= 0:
        errors.append(f"MAX_CONTEXT_TOKENS must be positive, got {MAX_CONTEXT_TOKENS}")
    
    if RETRIEVAL_TOP_K <= 0:
        errors.append(f"RETRIEVAL_TOP_K must be positive, got {RETRIEVAL_TOP_K}")
    
    if CHUNK_SIZE <= 0:
        errors.append(f"CHUNK_SIZE must be positive, got {CHUNK_SIZE}")
    
    if CHUNK_OVERLAP < 0:
        errors.append(f"CHUNK_OVERLAP cannot be negative, got {CHUNK_OVERLAP}")
    
    if CHUNK_OVERLAP >= CHUNK_SIZE:
        errors.append(f"CHUNK_OVERLAP ({CHUNK_OVERLAP}) must be less than CHUNK_SIZE ({CHUNK_SIZE})")
    
    if SESSION_RETENTION_DAYS <= 0:
        errors.append(f"SESSION_RETENTION_DAYS must be positive, got {SESSION_RETENTION_DAYS}")
    
    # Validate geographic coordinates
    if not (-90 <= ROME_CENTER_LAT <= 90):
        errors.append(f"ROME_CENTER_LAT must be between -90 and 90, got {ROME_CENTER_LAT}")
    
    if not (-180 <= ROME_CENTER_LON <= 180):
        errors.append(f"ROME_CENTER_LON must be between -180 and 180, got {ROME_CENTER_LON}")
    
    # Raise error if any validation failed
    if errors:
        error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        raise ConfigurationError(error_message)


def ensure_directories() -> None:
    """
    Ensure that all required directories exist.
    
    Creates directories if they don't exist.
    """
    directories = [
        SESSION_STORAGE_PATH,
        VECTOR_STORE_PATH,
        DATA_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_config_summary() -> str:
    """
    Get a summary of the current configuration.
    
    Returns:
        Formatted string with configuration details (excluding sensitive data)
    """
    lines = [
        "=" * 60,
        "Rome Places Chatbot Configuration",
        "=" * 60,
        "",
        "Application:",
        f"  Title: {APP_TITLE}",
        f"  Max Context Tokens: {MAX_CONTEXT_TOKENS}",
        f"  Retrieval Top K: {RETRIEVAL_TOP_K}",
        "",
        "Models:",
        f"  LLM: {LLM_MODEL}",
        f"  Embedding: {EMBEDDING_MODEL}",
        f"  spaCy: {SPACY_MODEL}",
        "",
        "Geographic:",
        f"  Rome Center: {ROME_CENTER}",
        f"  Rome Bounding Box: {ROME_BBOX}",
        f"  Default Map Zoom: {DEFAULT_MAP_ZOOM}",
        "",
        "File Paths:",
        f"  Session Storage: {SESSION_STORAGE_PATH}",
        f"  Vector Store: {VECTOR_STORE_PATH}",
        f"  Data Directory: {DATA_DIR}",
        "",
        "Text Chunking:",
        f"  Chunk Size: {CHUNK_SIZE}",
        f"  Chunk Overlap: {CHUNK_OVERLAP}",
        "",
        "Session Management:",
        f"  Retention Days: {SESSION_RETENTION_DAYS}",
        "",
        "RAG:",
        f"  Retrieval K: {RAG_RETRIEVAL_K}",
        f"  API Max Retries: {API_MAX_RETRIES}",
        f"  API Timeout: {API_TIMEOUT}s",
        "",
        "Logging:",
        f"  Log Level: {LOG_LEVEL}",
        "",
        "=" * 60
    ]
    
    return "\n".join(lines)


# Validate configuration on module import
try:
    validate_configuration()
    ensure_directories()
except ConfigurationError as e:
    # Don't raise during import, let the application handle it
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Configuration validation failed: {e}")
