"""Property tests for conversation state persistence.

**Feature: data-analysis-agent, Property 9: Conversation State Persistence**
**Validates: Requirements 8.2**
"""

from hypothesis import given, strategies as st, settings
import pytest

from src.state import AgentState, create_initial_state


class TestConversationStatePersistence:
    """Property-based tests for state persistence."""
    
    @given(
        queries=st.lists(
            st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_messages_accumulate_across_interactions(self, queries: list):
        """
        **Feature: data-analysis-agent, Property 9: Conversation State Persistence**
        For any sequence of user interactions, the conversation history SHALL be preserved.
        **Validates: Requirements 8.2**
        """
        messages = []
        
        for query in queries:
            # Simulate adding user message
            messages.append({"role": "user", "content": query})
            # Simulate adding assistant response
            messages.append({"role": "assistant", "content": f"Response to: {query}"})
        
        # Create state with accumulated messages
        state = create_initial_state(queries[-1], messages)
        
        # Verify all messages are preserved
        assert len(state["messages"]) == len(queries) * 2
    
    @given(
        query=st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')))
    )
    @settings(max_examples=100)
    def test_current_query_preserved(self, query: str):
        """
        **Feature: data-analysis-agent, Property 9: Conversation State Persistence**
        For any user query, the current_query field SHALL preserve the exact query.
        **Validates: Requirements 8.2**
        """
        state = create_initial_state(query)
        assert state["current_query"] == query
    
    @given(
        initial_messages=st.lists(
            st.fixed_dictionaries({
                "role": st.sampled_from(["user", "assistant"]),
                "content": st.text(min_size=1, max_size=50)
            }),
            min_size=0,
            max_size=20
        )
    )
    @settings(max_examples=100)
    def test_existing_messages_preserved_on_new_query(self, initial_messages: list):
        """
        **Feature: data-analysis-agent, Property 9: Conversation State Persistence**
        For any existing conversation history, new queries SHALL preserve previous messages.
        **Validates: Requirements 8.2**
        """
        state = create_initial_state("new query", initial_messages)
        
        # All initial messages should be preserved
        assert len(state["messages"]) == len(initial_messages)
    
    @given(
        query_type=st.sampled_from(["schema", "analysis", "general", "clarification", None])
    )
    @settings(max_examples=100)
    def test_state_fields_initialized_correctly(self, query_type: str):
        """
        **Feature: data-analysis-agent, Property 9: Conversation State Persistence**
        For any initial state, all fields SHALL be properly initialized.
        **Validates: Requirements 8.2**
        """
        state = create_initial_state("test query")
        
        # Verify all fields exist and have correct initial values
        assert state["current_query"] == "test query"
        assert state["query_type"] is None
        assert state["execution_plan"] is None
        assert state["sql_query"] is None
        assert state["query_results"] is None
        assert state["analysis"] is None
        assert state["response"] is None
        assert state["error"] is None
        assert state["retry_count"] == 0
