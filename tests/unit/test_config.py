"""Unit tests for configuration module."""

import pytest
import os

from src.config import Config, load_config


class TestConfig:
    """Unit tests for Config class."""
    
    def test_default_provider_is_valid(self):
        """Test that default provider is a valid option."""
        config = Config()
        assert config.llm_provider in ["gemini", "openrouter"]
    
    def test_default_retry_settings(self):
        """Test default retry configuration values."""
        config = Config()
        assert config.max_query_retries == 2
        assert config.query_timeout == 60
    
    def test_get_model_name_gemini(self, monkeypatch):
        """Test get_model_name for Gemini provider."""
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_MODEL", "gemini-pro")
        config = Config()
        assert config.get_model_name() == "gemini-pro"
    
    def test_get_model_name_openrouter(self, monkeypatch):
        """Test get_model_name for OpenRouter provider."""
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_MODEL", "test-model")
        config = Config()
        assert config.get_model_name() == "test-model"
    
    def test_get_api_key_gemini(self, monkeypatch):
        """Test get_api_key for Gemini provider."""
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        config = Config()
        assert config.get_api_key() == "test-key"
    
    def test_get_api_key_openrouter(self, monkeypatch):
        """Test get_api_key for OpenRouter provider."""
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        config = Config()
        assert config.get_api_key() == "test-key"
    
    def test_get_api_key_missing_gemini_raises(self, monkeypatch):
        """Test that missing Gemini API key raises error."""
        # Clear all relevant env vars
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        
        # Create config without loading .env
        config = Config(_env_file=None)
        config.llm_provider = "gemini"
        config.google_api_key = None
        
        with pytest.raises(ValueError, match="GOOGLE_API_KEY is required"):
            config.get_api_key()
    
    def test_get_api_key_missing_openrouter_raises(self, monkeypatch):
        """Test that missing OpenRouter API key raises error."""
        # Clear all relevant env vars
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        
        # Create config without loading .env
        config = Config(_env_file=None)
        config.llm_provider = "openrouter"
        config.openrouter_api_key = None
        
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY is required"):
            config.get_api_key()
    
    def test_load_config(self):
        """Test load_config function."""
        config = load_config()
        assert isinstance(config, Config)
