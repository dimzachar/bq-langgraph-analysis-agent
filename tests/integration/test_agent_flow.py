"""Integration tests for agent flow."""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from src.agent import DataAnalysisAgent
from src.state import create_initial_state


class TestAgentFlow:
    """Integration tests for end-to-end agent flow."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        llm = MagicMock()
        # Default responses for different prompts
        def mock_invoke(prompt):
            if "classify" in prompt.lower() or "router" in prompt.lower():
                return "analysis"
            elif "plan" in prompt.lower():
                return "1. Query data\n2. Analyze results"
            elif "sql" in prompt.lower():
                return "SELECT COUNT(*) FROM users"
            elif "analyze" in prompt.lower():
                return "The data shows 100 users."
            else:
                return "Here is your response."
        
        llm.invoke_with_retry.side_effect = mock_invoke
        return llm
    
    @pytest.fixture
    def mock_bq_client(self):
        """Create a mock BigQuery client."""
        client = MagicMock()
        client.execute_query.return_value = pd.DataFrame({"count": [100]})
        return client
    
    @pytest.fixture
    def mock_schema_cache(self):
        """Create a mock schema cache."""
        cache = MagicMock()
        cache.get_schema_prompt.return_value = "Table: users\n- id: INTEGER\n- name: STRING"
        cache.get_schema.return_value = [{"name": "id", "type": "INTEGER"}]
        return cache
    
    @pytest.fixture
    def agent(self, mock_llm, mock_bq_client, mock_schema_cache):
        """Create agent with mocks."""
        return DataAnalysisAgent(mock_llm, mock_bq_client, mock_schema_cache)
    
    def test_full_analysis_flow(self, agent, mock_llm):
        """Test complete analysis query flow."""
        response = agent.invoke("How many users are there?")
        
        assert response is not None
        assert len(response) > 0
        # LLM should have been called multiple times (router, planner, etc.)
        assert mock_llm.invoke_with_retry.call_count > 0
    
    def test_schema_query_flow(self, agent, mock_llm):
        """Test schema query flow."""
        # Override to return schema type
        mock_llm.invoke_with_retry.side_effect = lambda p: "schema" if "classify" in p.lower() else "Here are the tables."
        
        response = agent.invoke("What tables exist?")
        
        assert response is not None
    
    def test_conversation_history_maintained(self, agent):
        """Test that conversation history is maintained."""
        agent.invoke("First query")
        agent.invoke("Second query")
        
        assert len(agent.messages) == 4  # 2 user + 2 assistant
    
    def test_reset_conversation(self, agent):
        """Test conversation reset."""
        agent.invoke("Query")
        agent.reset_conversation()
        
        assert len(agent.messages) == 0
    
    def test_error_recovery(self, agent, mock_bq_client):
        """Test agent recovers from errors."""
        mock_bq_client.execute_query.side_effect = Exception("Query failed")
        
        response = agent.invoke("Query that fails")
        
        # Should still get a response (error message)
        assert response is not None
        
        # Agent should still be operational
        mock_bq_client.execute_query.side_effect = None
        mock_bq_client.execute_query.return_value = pd.DataFrame({"col": [1]})
        
        response2 = agent.invoke("Another query")
        assert response2 is not None
