from typing import TypedDict, List, Optional, Annotated, Any
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State maintained across agent execution.
    
    This state is passed between nodes in the LangGraph state graph.
    """
    # Conversation history with message accumulation
    messages: Annotated[List, add_messages]
    
    # Current user query being processed
    current_query: str
    
    # Classified query type: "schema", "analysis", "general", "clarification"
    query_type: Optional[str]
    
    # Execution plan steps
    execution_plan: Optional[List[str]]
    
    # Generated SQL query
    sql_query: Optional[str]
    
    # Results from BigQuery execution
    query_results: Optional[Any]
    
    # Analysis/insights from results
    analysis: Optional[str]
    
    # Final response to user
    response: Optional[str]
    
    # Error message if any
    error: Optional[str]
    
    # Number of retries for failed queries
    retry_count: int


def create_initial_state(user_query: str, messages: List = None) -> AgentState:
    """Create initial state for a new query.
    
    Args:
        user_query: The user's query
        messages: Optional existing conversation history
        
    Returns:
        Initial AgentState
    """
    return AgentState(
        messages=messages or [],
        current_query=user_query,
        query_type=None,
        execution_plan=None,
        sql_query=None,
        query_results=None,
        analysis=None,
        response=None,
        error=None,
        retry_count=0
    )
