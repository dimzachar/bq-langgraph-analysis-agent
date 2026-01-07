import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    # LLM Provider settings
    llm_provider: Literal["gemini", "openrouter"] = "gemini"
    
    # Google Gemini settings
    google_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    
    # OpenRouter settings
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "google/gemini-2.0-flash-exp:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Fallback model settings (optional - used when primary model fails)
    fallback_model: Optional[str] = None
    
    # BigQuery settings
    google_cloud_project: Optional[str] = None
    bigquery_dataset: str = "bigquery-public-data.thelook_ecommerce"
    
    # Agent settings
    max_query_retries: int = 2
    query_timeout: int = 60
    
    # Suggested models for /model command (comma-separated, provider-specific)
    suggested_models_gemini: str = "gemini-2.5-pro,gemini-2.5-flash,gemini-2.0-flash,gemini-2.5-flash-lite"
    suggested_models_openrouter: str = "google/gemini-2.5-flash"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }
    
    def get_api_key(self) -> str:
        """Get the API key for the configured LLM provider."""
        if self.llm_provider == "gemini":
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY is required for Gemini provider")
            return self.google_api_key
        elif self.llm_provider == "openrouter":
            if not self.openrouter_api_key:
                raise ValueError("OPENROUTER_API_KEY is required for OpenRouter provider")
            return self.openrouter_api_key
        raise ValueError(f"Unknown provider: {self.llm_provider}")
    
    def get_model_name(self) -> str:
        """Get the model name for the configured LLM provider."""
        if self.llm_provider == "gemini":
            return self.gemini_model
        elif self.llm_provider == "openrouter":
            return self.openrouter_model
        raise ValueError(f"Unknown provider: {self.llm_provider}")
    
    def get_suggested_models(self) -> list:
        """Get list of suggested models for the current provider."""
        if self.llm_provider == "gemini":
            models_str = self.suggested_models_gemini
        else:
            models_str = self.suggested_models_openrouter
        return [m.strip() for m in models_str.split(",") if m.strip()]


def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config()
