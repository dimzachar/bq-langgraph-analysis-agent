"""Unit tests for Response Generator node."""

import pytest
from unittest.mock import MagicMock

from src.nodes.responder import ResponseGenerator
from src.state import create_initial_state


class TestResponseGenerator:
    """Unit tests for ResponseGenerator class."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        llm = MagicMock()
        llm.invoke_with_retry.return_value = "Here is your response."
        return llm
    
    @pytest.fixture
    def mock_schema_cache(self):
        """Create a mock schema cache."""
        cache = MagicMock()
        cache.get_schema_prompt.return_value = "Schema info"
        return cache
    
    @pytest.fixture
    def responder(self, mock_llm, mock_schema_cache):
        """Create responder with mocks."""
        return ResponseGenerator(mock_llm, mock_schema_cache)
    
    def test_respond_to_analysis(self, responder):
        """Test response generation for analysis query."""
        state = create_initial_state("Show sales")
        state["query_type"] = "analysis"
        state["analysis"] = "Sales are up 10%"
        
        result = responder.respond(state)
        
        assert result["response"] is not None
    
    def test_respond_to_schema(self, responder):
        """Test response generation for schema query."""
        state = create_initial_state("What tables?")
        state["query_type"] = "schema"
        
        result = responder.respond(state)
        
        assert result["response"] is not None
    
    def test_respond_to_error(self, responder):
        """Test response generation for error state."""
        state = create_initial_state("Query")
        state["query_type"] = "analysis"
        state["error"] = "Query timeout"
        
        result = responder.respond(state)
        
        assert result["response"] is not None
        # Should be user-friendly
        assert "timeout" not in result["response"].lower() or "took too long" in result["response"].lower()
    
    def test_respond_to_clarification(self, responder):
        """Test response generation for clarification."""
        state = create_initial_state("Show data")
        state["query_type"] = "clarification"
        
        result = responder.respond(state)
        
        assert result["response"] is not None
        assert "clarify" in result["response"].lower() or "information" in result["response"].lower()
    
    def test_respond_to_general(self, responder):
        """Test response generation for general query."""
        state = create_initial_state("Hello")
        state["query_type"] = "general"
        
        result = responder.respond(state)
        
        assert result["response"] is not None
