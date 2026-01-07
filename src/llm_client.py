import time
import logging
from typing import Optional, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.language_models.base import BaseLanguageModel

from src.metrics import estimate_tokens

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
        self.model_name = model_name
        self.api_key = api_key
        self.openrouter_base_url = openrouter_base_url
        self.fallback_model_name = fallback_model
        
        # Metrics tracking
        self.last_prompt_tokens = 0
        self.last_response_tokens = 0
        self.call_count = 0
        
        # Create primary model
        self._init_model()
    
    def _init_model(self):
        """Initialize or reinitialize the model."""
        primary_model = self._create_model(
            provider=self.provider,
            model_name=self.model_name,
            api_key=self.api_key,
            openrouter_base_url=self.openrouter_base_url
        )
        
        # Add fallback if configured (only for OpenRouter currently)
        if self.fallback_model_name and self.provider == "openrouter":
            fallback = self._create_model(
                provider="openrouter",
                model_name=self.fallback_model_name,
                api_key=self.api_key,
                openrouter_base_url=self.openrouter_base_url
            )
            self.model = primary_model.with_fallbacks([fallback])
            logger.info(f"Initialized LLM with fallback: {self.model_name} -> {self.fallback_model_name}")
        else:
            self.model = primary_model
            logger.info(f"Initialized LLM client with provider: {self.provider}, model: {self.model_name}")
    
    def switch_model(self, model_name: str) -> str:
        """Switch to a different model.
        
        Args:
            model_name: New model name to use.
            
        Returns:
            The new model name
        """
        old_model = self.model_name
        self.model_name = model_name
        
        try:
            self._init_model()
            self.reset_metrics()
            logger.info(f"Switched model: {old_model} -> {model_name}")
            return model_name
        except Exception as e:
            # Rollback on failure
            self.model_name = old_model
            self._init_model()
            raise ValueError(f"Failed to switch to {model_name}: {e}")
    
    def get_model_name(self) -> str:
        """Get current model name."""
        return self.model_name or "unknown"
    
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
        self.call_count += 1
        self.last_prompt_tokens = estimate_tokens(prompt)
        
        response = self.model.invoke([HumanMessage(content=prompt)])
        content = response.content
        
        self.last_response_tokens = estimate_tokens(content)
        return content
    
    def get_last_call_tokens(self) -> Tuple[int, int]:
        """Get token counts from last call.
        
        Returns:
            Tuple of (prompt_tokens, response_tokens)
        """
        return self.last_prompt_tokens, self.last_response_tokens
    
    def reset_metrics(self):
        """Reset call metrics."""
        self.call_count = 0
        self.last_prompt_tokens = 0
        self.last_response_tokens = 0
    
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
