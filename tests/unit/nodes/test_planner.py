"""Unit tests for Query Planner node."""

import pytest
from unittest.mock import MagicMock

from src.nodes.planner import QueryPlanner
from src.state import create_initial_state


class TestQueryPlanner:
    """Unit tests for QueryPlanner class."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        llm = MagicMock()
        llm.invoke_with_retry.return_value = "1. Query users table\n2. Aggregate results"
        return llm
    
    @pytest.fixture
    def mock_schema_cache(self):
        """Create a mock schema cache."""
        cache = MagicMock()
        cache.get_schema_prompt.return_value = "Schema info"
        return cache
    
    @pytest.fixture
    def planner(self, mock_llm, mock_schema_cache):
        """Create planner with mocks."""
        return QueryPlanner(mock_llm, mock_schema_cache)
    
    def test_plan_analysis_query(self, planner):
        """Test planning for analysis query."""
        state = create_initial_state("Show top products")
        state["query_type"] = "analysis"
        
        result = planner.plan(state)
        
        assert result["execution_plan"] is not None
        assert len(result["execution_plan"]) > 0
    
    def test_plan_schema_query(self, planner):
        """Test planning for schema query."""
        state = create_initial_state("What tables?")
        state["query_type"] = "schema"
        
        result = planner.plan(state)
        
        assert result["execution_plan"] == ["Retrieve schema information", "Format schema for user"]
    
    def test_plan_general_query(self, planner):
        """Test planning for general query."""
        state = create_initial_state("Hello")
        state["query_type"] = "general"
        
        result = planner.plan(state)
        
        assert result["execution_plan"] == ["Generate direct response"]
    
    def test_plan_clarification_query(self, planner):
        """Test planning for clarification query."""
        state = create_initial_state("Show data")
        state["query_type"] = "clarification"
        
        result = planner.plan(state)
        
        assert result["execution_plan"] == ["Request clarification from user"]
