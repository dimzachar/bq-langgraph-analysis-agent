"""Property tests for configuration loading.

**Feature: data-analysis-agent, Property: Config loads from environment variables**
**Validates: Requirements 10.1**
"""

import os
from hypothesis import given, strategies as st, settings, HealthCheck
import pytest

from src.config import Config


class TestConfigProperties:
    """Property-based tests for configuration."""
    
    @given(
        provider=st.sampled_from(["gemini", "openrouter"]),
        api_key=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N'))),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_config_loads_provider_from_env(self, provider: str, api_key: str, monkeypatch):
        """
        **Feature: data-analysis-agent, Property: Config loads from environment variables**
        For any valid provider setting, the config SHALL load the correct provider.
        **Validates: Requirements 10.1**
        """
        monkeypatch.setenv("LLM_PROVIDER", provider)
        if provider == "gemini":
            monkeypatch.setenv("GOOGLE_API_KEY", api_key)
        else:
            monkeypatch.setenv("OPENROUTER_API_KEY", api_key)
        
        config = Config()
        assert config.llm_provider == provider
    
    @given(
        model_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P')))
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_config_loads_model_name_from_env(self, model_name: str, monkeypatch):
        """
        **Feature: data-analysis-agent, Property: Config loads model name from environment**
        For any valid model name, the config SHALL load it correctly.
        **Validates: Requirements 10.1**
        """
        monkeypatch.setenv("GEMINI_MODEL", model_name)
        config = Config()
        assert config.gemini_model == model_name
    
    @given(
        retries=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_config_loads_retry_settings(self, retries: int, monkeypatch):
        """
        **Feature: data-analysis-agent, Property: Config loads retry settings from environment**
        For any valid retry count, the config SHALL load it correctly.
        **Validates: Requirements 10.1**
        """
        monkeypatch.setenv("MAX_QUERY_RETRIES", str(retries))
        config = Config()
        assert config.max_query_retries == retries
