import time
import logging
from typing import Optional, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.language_models.base import BaseLanguageModel

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for LLM providers (Google Gemini or OpenRouter) with fallback support."""
    
    def __init__(
        self,
        provider: str = "gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        openrouter_base_url: str = "https://openrouter.ai/api/v1",
        fallback_model: Optional[str] = None
    ):
        """Initialize LLM client with specified provider and optional fallback.
        
        Args:
            provider: LLM provider ("gemini" or "openrouter")
            model_name: Model name to use
            api_key: API key for the provider
            openrouter_base_url: Base URL for OpenRouter API
            fallback_model: Optional fallback model name (for OpenRouter)
        """
        self.provider = provider
        self.fallback_model_name = fallback_model
        
        # Create primary model
        primary_model = self._create_model(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            openrouter_base_url=openrouter_base_url
        )
        
        # Add fallback if configured (only for OpenRouter currently)
        if fallback_model and provider == "openrouter":
            fallback = self._create_model(
                provider="openrouter",
                model_name=fallback_model,
                api_key=api_key,
                openrouter_base_url=openrouter_base_url
            )
            # Use LangChain's built-in fallback mechanism
            self.model = primary_model.with_fallbacks([fallback])
            logger.info(f"Initialized LLM with fallback: {model_name} -> {fallback_model}")
        else:
            self.model = primary_model
            logger.info(f"Initialized LLM client with provider: {provider}, model: {model_name}")
    
    def _create_model(
        self,
        provider: str,
        model_name: Optional[str],
        api_key: Optional[str],
        openrouter_base_url: str
    ) -> BaseLanguageModel:
        """Create a LangChain model instance.
        
        Args:
            provider: LLM provider ("gemini" or "openrouter")
            model_name: Model name to use
            api_key: API key for the provider
            openrouter_base_url: Base URL for OpenRouter API
            
        Returns:
            A LangChain chat model instance
        """
        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=model_name or "gemini-1.5-flash",
                google_api_key=api_key
            )
        elif provider == "openrouter":
            return ChatOpenAI(
                model=model_name or "google/gemini-2.0-flash-exp:free",
                openai_api_key=api_key,
                openai_api_base=openrouter_base_url
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def invoke(self, prompt: str) -> str:
        """Send prompt to LLM and get response.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM's response as a string
        """
        response = self.model.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def invoke_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_backoff: float = 30.0
    ) -> str:
        """Invoke LLM with exponential backoff for rate limits.
        
        Args:
            prompt: The prompt to send to the LLM
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff time in seconds
            backoff_multiplier: Multiplier for exponential backoff
            max_backoff: Maximum backoff time in seconds
            
        Returns:
            The LLM's response as a string
            
        Raises:
            Exception: If all retries are exhausted
        """
        backoff = initial_backoff
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.invoke(prompt)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if "rate" in error_str or "429" in error_str or "quota" in error_str:
                    if attempt < max_retries:
                        logger.warning(f"Rate limit hit, retrying in {backoff}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(backoff)
                        backoff = min(backoff * backoff_multiplier, max_backoff)
                        continue
                
                # For non-rate-limit errors, raise immediately
                raise
        
        raise last_exception
