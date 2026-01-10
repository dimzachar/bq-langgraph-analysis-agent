"""Unit tests for Query Executor node."""

import pytest
from unittest.mock import MagicMock
import pandas as pd

from src.nodes.executor import QueryExecutor
from src.state import create_initial_state


class TestQueryExecutor:
    """Unit tests for QueryExecutor class."""
    
    @pytest.fixture
    def mock_bq_client(self):
        """Create a mock BigQuery client."""
        client = MagicMock()
        client.execute_query.return_value = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        return client
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        llm = MagicMock()
        llm.invoke_with_retry.return_value = "SELECT * FROM users"
        return llm
    
    @pytest.fixture
    def executor(self, mock_bq_client, mock_llm):
        """Create executor with mocks."""
        return QueryExecutor(mock_bq_client, mock_llm, max_retries=2)
    
    def test_execute_successful_query(self, executor, mock_bq_client):
        """Test successful query execution."""
        state = create_initial_state("Get data")
        state["sql_query"] = "SELECT * FROM users"
        
        result = executor.execute(state)
        
        assert result["query_results"] is not None
        assert result["query_results"]["row_count"] == 2
        assert result["error"] is None
    
    def test_execute_no_sql_query(self, executor):
        """Test execution with no SQL query."""
        state = create_initial_state("Hello")
        state["sql_query"] = None
        
        result = executor.execute(state)
        
        assert result.get("query_results") is None
    
    def test_execute_with_retry_on_failure(self, executor, mock_bq_client, mock_llm):
        """Test retry logic on query failure."""
        mock_bq_client.execute_query.side_effect = [
            Exception("Syntax error"),
            pd.DataFrame({"col1": [1]})
        ]
        mock_llm.invoke_with_retry.return_value = "SELECT * FROM users LIMIT 10"
        
        state = create_initial_state("Get data")
        state["sql_query"] = "SELECT * FROM users"
        
        result = executor.execute(state)
        
        # Should succeed after retry
        assert result["query_results"] is not None or result["error"] is not None
    
    def test_execute_max_retries_exceeded(self, executor, mock_bq_client):
        """Test that max retries are respected."""
        mock_bq_client.execute_query.side_effect = Exception("Persistent error")
        
        state = create_initial_state("Get data")
        state["sql_query"] = "SELECT * FROM invalid"
        
        result = executor.execute(state)
        
        assert result["error"] is not None
        assert "failed" in result["error"].lower()
