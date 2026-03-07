"""
Unit tests for the configuration module.
"""

import os
import pytest
from unittest.mock import patch
from pathlib import Path

from src.config import (
    validate_configuration,
    ensure_directories,
    get_config_summary,
    ConfigurationError,
    ROME_CENTER,
    ROME_BBOX,
    MAX_CONTEXT_TOKENS,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)


class TestConfigurationValidation:
    """Tests for configuration validation."""
    
    def test_validate_configuration_success(self):
        """Test that validation passes with valid configuration."""
        # Should not raise any exception
        with patch("src.config.OPENAI_API_KEY", "test_key"):
            validate_configuration()
    
    def test_validate_configuration_missing_api_key(self):
        """Test that validation fails when OpenAI API key is missing."""
        with patch("src.config.OPENAI_API_KEY", None):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_configuration()
            
            assert "OPENAI_API_KEY" in str(exc_info.value)
    
    def test_validate_configuration_invalid_max_context_tokens(self):
        """Test that validation fails with invalid MAX_CONTEXT_TOKENS."""
        with patch("src.config.OPENAI_API_KEY", "test_key"), \
             patch("src.config.MAX_CONTEXT_TOKENS", -100):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_configuration()
            
            assert "MAX_CONTEXT_TOKENS must be positive" in str(exc_info.value)
    
    def test_validate_configuration_invalid_chunk_overlap(self):
        """Test that validation fails when chunk overlap >= chunk size."""
        with patch("src.config.OPENAI_API_KEY", "test_key"), \
             patch("src.config.CHUNK_SIZE", 100), \
             patch("src.config.CHUNK_OVERLAP", 150):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_configuration()
            
            assert "CHUNK_OVERLAP" in str(exc_info.value)
            assert "must be less than CHUNK_SIZE" in str(exc_info.value)
    
    def test_validate_configuration_invalid_coordinates(self):
        """Test that validation fails with invalid geographic coordinates."""
        with patch("src.config.OPENAI_API_KEY", "test_key"), \
             patch("src.config.ROME_CENTER_LAT", 200):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_configuration()
            
            assert "ROME_CENTER_LAT" in str(exc_info.value)


class TestDirectoryManagement:
    """Tests for directory management."""
    
    def test_ensure_directories_creates_missing_dirs(self, tmp_path):
        """Test that ensure_directories creates missing directories."""
        # Create temporary paths
        session_path = tmp_path / "sessions"
        vector_path = tmp_path / "vector_store"
        data_path = tmp_path / "data"
        
        # Patch the configuration paths
        with patch("src.config.SESSION_STORAGE_PATH", session_path), \
             patch("src.config.VECTOR_STORE_PATH", vector_path), \
             patch("src.config.DATA_DIR", data_path):
            
            # Ensure directories don't exist yet
            assert not session_path.exists()
            assert not vector_path.exists()
            assert not data_path.exists()
            
            # Call ensure_directories
            ensure_directories()
            
            # Verify directories were created
            assert session_path.exists()
            assert vector_path.exists()
            assert data_path.exists()
    
    def test_ensure_directories_handles_existing_dirs(self, tmp_path):
        """Test that ensure_directories handles existing directories gracefully."""
        # Create directories first
        session_path = tmp_path / "sessions"
        session_path.mkdir(parents=True)
        
        with patch("src.config.SESSION_STORAGE_PATH", session_path), \
             patch("src.config.VECTOR_STORE_PATH", tmp_path / "vector"), \
             patch("src.config.DATA_DIR", tmp_path / "data"):
            
            # Should not raise an error
            ensure_directories()
            
            # Directory should still exist
            assert session_path.exists()


class TestConfigurationConstants:
    """Tests for configuration constants."""
    
    def test_rome_center_is_tuple(self):
        """Test that ROME_CENTER is a tuple of two floats."""
        assert isinstance(ROME_CENTER, tuple)
        assert len(ROME_CENTER) == 2
        assert isinstance(ROME_CENTER[0], float)
        assert isinstance(ROME_CENTER[1], float)
    
    def test_rome_bbox_structure(self):
        """Test that ROME_BBOX has correct structure."""
        assert isinstance(ROME_BBOX, tuple)
        assert len(ROME_BBOX) == 2
        
        # Each element should be a tuple of (lat, lon)
        assert len(ROME_BBOX[0]) == 2
        assert len(ROME_BBOX[1]) == 2
    
    def test_max_context_tokens_positive(self):
        """Test that MAX_CONTEXT_TOKENS is positive."""
        assert MAX_CONTEXT_TOKENS > 0
    
    def test_chunk_configuration_valid(self):
        """Test that chunk configuration is valid."""
        assert CHUNK_SIZE > 0
        assert CHUNK_OVERLAP >= 0
        assert CHUNK_OVERLAP < CHUNK_SIZE


class TestConfigurationSummary:
    """Tests for configuration summary."""
    
    def test_get_config_summary_returns_string(self):
        """Test that get_config_summary returns a formatted string."""
        summary = get_config_summary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
    
    def test_get_config_summary_contains_key_info(self):
        """Test that summary contains key configuration information."""
        summary = get_config_summary()
        
        # Check for key sections
        assert "Rome Places Chatbot Configuration" in summary
        assert "Application:" in summary
        assert "Models:" in summary
        assert "Geographic:" in summary
        assert "File Paths:" in summary
        assert "Text Chunking:" in summary
        assert "Session Management:" in summary
        assert "RAG:" in summary
        assert "Logging:" in summary
    
    def test_get_config_summary_no_sensitive_data(self):
        """Test that summary doesn't expose sensitive data like API keys."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret_key_12345"}):
            summary = get_config_summary()
            
            # API key should not be in the summary
            assert "secret_key_12345" not in summary
            assert "OPENAI_API_KEY" not in summary


class TestEnvironmentVariableLoading:
    """Tests for environment variable loading."""
    
    def test_default_values_used_when_env_vars_missing(self):
        """Test that default values are used when environment variables are not set."""
        # Import with minimal environment
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to get fresh values
            import importlib
            import src.config as config_module
            importlib.reload(config_module)
            
            # Check defaults are used
            assert config_module.APP_TITLE == "Rome Places Chatbot"
            assert config_module.MAX_CONTEXT_TOKENS == 4000
            assert config_module.EMBEDDING_MODEL == "text-embedding-ada-002"
    
    def test_custom_values_override_defaults(self):
        """Test that custom environment variables override defaults."""
        with patch.dict(os.environ, {
            "APP_TITLE": "Custom Chatbot",
            "MAX_CONTEXT_TOKENS": "8000",
            "EMBEDDING_MODEL": "custom-embedding-model"
        }):
            # Re-import to get fresh values
            import importlib
            import src.config as config_module
            importlib.reload(config_module)
            
            # Check custom values are used
            assert config_module.APP_TITLE == "Custom Chatbot"
            assert config_module.MAX_CONTEXT_TOKENS == 8000
            assert config_module.EMBEDDING_MODEL == "custom-embedding-model"
