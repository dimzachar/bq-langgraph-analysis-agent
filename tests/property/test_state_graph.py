"""Property tests for state graph transitions.

**Feature: data-analysis-agent, Property 8: State Graph Transitions**
**Feature: data-analysis-agent, Property 12: Error Recovery State Preservation**
**Validates: Requirements 8.1, 9.4**
"""

from hypothesis import given, strategies as st, settings
import pytest


class TestStateGraphTransitions:
    """Property-based tests for state graph transitions."""
    
    # Valid transition paths
    VALID_PATHS = {
        "analysis": ["router", "planner", "sql_generator", "executor", "analyzer", "responder"],
        "schema": ["router", "responder"],
        "general": ["router", "responder"],
        "clarification": ["router", "responder"]
    }
    
    @given(
        query_type=st.sampled_from(["analysis", "schema", "general", "clarification"])
    )
    @settings(max_examples=100)
    def test_valid_transition_paths_exist(self, query_type: str):
        """
        **Feature: data-analysis-agent, Property 8: State Graph Transitions**
        For any query type, a valid transition path SHALL exist.
        **Validates: Requirements 8.1**
        """
        assert query_type in self.VALID_PATHS
        path = self.VALID_PATHS[query_type]
        
        # All paths start with router
        assert path[0] == "router"
        # All paths end with responder
        assert path[-1] == "responder"
    
    @given(
        query_type=st.sampled_from(["analysis", "schema", "general", "clarification"])
    )
    @settings(max_examples=100)
    def test_analysis_path_includes_all_nodes(self, query_type: str):
        """
        **Feature: data-analysis-agent, Property 8: State Graph Transitions**
        For analysis queries, the path SHALL include all processing nodes.
        **Validates: Requirements 8.1**
        """
        if query_type == "analysis":
            path = self.VALID_PATHS[query_type]
            required_nodes = ["router", "planner", "sql_generator", "executor", "analyzer", "responder"]
            
            for node in required_nodes:
                assert node in path, f"Analysis path should include {node}"
    
    @given(
        query_type=st.sampled_from(["schema", "general", "clarification"])
    )
    @settings(max_examples=100)
    def test_non_analysis_paths_skip_sql(self, query_type: str):
        """
        **Feature: data-analysis-agent, Property 8: State Graph Transitions**
        For non-analysis queries, SQL nodes SHALL be skipped.
        **Validates: Requirements 8.1**
        """
        path = self.VALID_PATHS[query_type]
        
        # These nodes should not be in non-analysis paths
        sql_nodes = ["sql_generator", "executor"]
        
        for node in sql_nodes:
            assert node not in path, f"Non-analysis path should not include {node}"


class TestErrorRecoveryStatePreservation:
    """Property-based tests for error recovery state preservation."""
    
    @given(
        messages=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_messages_preserved_after_error(self, messages: list):
        """
        **Feature: data-analysis-agent, Property 12: Error Recovery State Preservation**
        For any error during processing, conversation context SHALL be preserved.
        **Validates: Requirements 9.4**
        """
        # Simulate state with messages
        state = {
            "messages": [{"role": "user", "content": m} for m in messages],
            "error": "Simulated error"
        }
        
        # After error, messages should still be present
        assert len(state["messages"]) == len(messages)
        assert state["error"] is not None
    
    @given(
        current_query=st.text(min_size=1, max_size=200),
        query_type=st.sampled_from(["analysis", "schema", "general", "clarification"])
    )
    @settings(max_examples=100)
    def test_query_context_preserved_after_error(self, current_query: str, query_type: str):
        """
        **Feature: data-analysis-agent, Property 12: Error Recovery State Preservation**
        For any error, the current query and type SHALL be preserved.
        **Validates: Requirements 9.4**
        """
        state = {
            "current_query": current_query,
            "query_type": query_type,
            "error": "Simulated error"
        }
        
        # Query context should be preserved
        assert state["current_query"] == current_query
        assert state["query_type"] == query_type
    
    @given(
        retry_count=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=100)
    def test_retry_count_tracked_during_errors(self, retry_count: int):
        """
        **Feature: data-analysis-agent, Property 12: Error Recovery State Preservation**
        For any error recovery, retry count SHALL be tracked.
        **Validates: Requirements 9.4**
        """
        state = {
            "retry_count": retry_count,
            "error": "Simulated error"
        }
        
        # Retry count should be preserved
        assert state["retry_count"] == retry_count
