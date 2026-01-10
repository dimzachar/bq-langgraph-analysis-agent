"""Unit tests for Query Router node."""

import pytest
from unittest.mock import MagicMock

from src.nodes.router import QueryRouter
from src.state import create_initial_state


class TestQueryRouter:
    """Unit tests for QueryRouter class."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        llm = MagicMock()
        llm.invoke_with_retry.return_value = "analysis"
        return llm
    
    @pytest.fixture
    def router(self, mock_llm):
        """Create router with mock LLM."""
        return QueryRouter(mock_llm)
    
    def test_route_analysis_query(self, router, mock_llm):
        """Test routing an analysis query."""
        mock_llm.invoke_with_retry.return_value = "analysis"
        state = create_initial_state("Show me top products")
        
        result = router.route(state)
        
        assert result["query_type"] == "analysis"
    
    def test_route_schema_query(self, router, mock_llm):
        """Test routing a schema query."""
        mock_llm.invoke_with_retry.return_value = "schema"
        state = create_initial_state("What tables exist?")
        
        result = router.route(state)
        
        assert result["query_type"] == "schema"
    
    def test_route_general_query(self, router, mock_llm):
        """Test routing a general query."""
        mock_llm.invoke_with_retry.return_value = "general"
        state = create_initial_state("Hello")
        
        result = router.route(state)
        
        assert result["query_type"] == "general"
    
    def test_route_clarification_query(self, router, mock_llm):
        """Test routing a clarification query."""
        mock_llm.invoke_with_retry.return_value = "clarification"
        state = create_initial_state("Show me data")
        
        result = router.route(state)
        
        assert result["query_type"] == "clarification"
    
    def test_route_defaults_to_general_on_error(self, router, mock_llm):
        """Test that routing defaults to general on error."""
        mock_llm.invoke_with_retry.side_effect = Exception("LLM error")
        state = create_initial_state("Test query")
        
        result = router.route(state)
        
        assert result["query_type"] == "general"
        assert result["error"] is not None
