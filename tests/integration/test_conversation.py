"""Integration tests for conversation handling."""

import pytest
from unittest.mock import MagicMock
import pandas as pd

from src.agent import DataAnalysisAgent


class TestConversation:
    """Integration tests for conversation state and history."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        llm = MagicMock()
        llm.invoke_with_retry.return_value = "Response"
        return llm
    
    @pytest.fixture
    def mock_bq_client(self):
        """Create a mock BigQuery client."""
        client = MagicMock()
        client.execute_query.return_value = pd.DataFrame({"col": [1]})
        return client
    
    @pytest.fixture
    def mock_schema_cache(self):
        """Create a mock schema cache."""
        cache = MagicMock()
        cache.get_schema_prompt.return_value = "Schema"
        return cache
    
    @pytest.fixture
    def agent(self, mock_llm, mock_bq_client, mock_schema_cache):
        """Create agent with mocks."""
        return DataAnalysisAgent(mock_llm, mock_bq_client, mock_schema_cache)
    
    def test_messages_accumulate(self, agent):
        """Test that messages accumulate across interactions."""
        agent.invoke("Query 1")
        assert len(agent.messages) == 2
        
        agent.invoke("Query 2")
        assert len(agent.messages) == 4
        
        agent.invoke("Query 3")
        assert len(agent.messages) == 6
    
    def test_message_roles_alternate(self, agent):
        """Test that message roles alternate user/assistant."""
        agent.invoke("Query")
        
        assert agent.messages[0].type == "human"
        assert agent.messages[1].type == "ai"
    
    def test_conversation_context_preserved(self, agent):
        """Test that conversation context is preserved."""
        agent.invoke("First question")
        first_message = agent.messages[0].content
        
        agent.invoke("Follow up")
        
        # First message should still be there
        assert agent.messages[0].content == first_message
    
    def test_reset_clears_history(self, agent):
        """Test that reset clears conversation history."""
        agent.invoke("Query 1")
        agent.invoke("Query 2")
        
        agent.reset_conversation()
        
        assert len(agent.messages) == 0
    
    def test_multiple_sessions(self, agent):
        """Test multiple conversation sessions."""
        # First session
        agent.invoke("Session 1 query")
        assert len(agent.messages) == 2
        
        agent.reset_conversation()
        
        # Second session
        agent.invoke("Session 2 query")
        assert len(agent.messages) == 2
    
    def test_error_adds_message(self, agent, mock_bq_client):
        """Test that errors still add messages to history."""
        mock_bq_client.execute_query.side_effect = Exception("Error")
        
        agent.invoke("Failing query")
        
        # Should still have user and assistant messages
        assert len(agent.messages) == 2
