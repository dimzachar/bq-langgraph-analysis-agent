import logging
from typing import List, Literal

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from src.state import AgentState, create_initial_state
from src.nodes.router import QueryRouter
from src.nodes.planner import QueryPlanner
from src.nodes.sql_generator import SQLGenerator
from src.nodes.executor import QueryExecutor
from src.nodes.analyzer import ResultAnalyzer
from src.nodes.responder import ResponseGenerator

logger = logging.getLogger(__name__)


class DataAnalysisAgent:
    """Main agent orchestrating the analysis workflow."""
    
    def __init__(self, llm_client, bq_client, schema_cache, max_retries: int = 2):
        """Initialize the data analysis agent.
        
        Args:
            llm_client: LLM client for all nodes
            bq_client: BigQuery client for query execution
            schema_cache: Schema cache for table information
            max_retries: Maximum retries for failed queries
        """
        self.llm = llm_client
        self.bq_client = bq_client
        self.schema_cache = schema_cache
        
        # Initialize nodes
        self.router = QueryRouter(llm_client)
        self.planner = QueryPlanner(llm_client, schema_cache)
        self.sql_generator = SQLGenerator(llm_client, schema_cache, bq_client.dataset_id)
        self.executor = QueryExecutor(
            bq_client, 
            llm_client, 
            max_retries,
            sql_validator=self.sql_generator.validate_tables
        )
        self.analyzer = ResultAnalyzer(llm_client)
        self.responder = ResponseGenerator(llm_client, schema_cache)
        
        # Build the graph
        self.graph = self._build_graph()
        
        # Conversation history
        self.messages: List = []
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph.
        
        Returns:
            Compiled state graph
        """
        # Create graph with AgentState
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("router", self._route)
        workflow.add_node("planner", self._plan)
        workflow.add_node("sql_generator", self._generate_sql)
        workflow.add_node("executor", self._execute)
        workflow.add_node("analyzer", self._analyze)
        workflow.add_node("responder", self._respond)
        
        # Set entry point
        workflow.set_entry_point("router")
        
        # Add edges
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "analysis": "planner",
                "schema": "responder",
                "general": "responder",
                "clarification": "responder"
            }
        )
        
        workflow.add_edge("planner", "sql_generator")
        workflow.add_edge("sql_generator", "executor")
        workflow.add_edge("executor", "analyzer")
        workflow.add_edge("analyzer", "responder")
        workflow.add_edge("responder", END)
        
        return workflow.compile()
    
    def _route(self, state: AgentState) -> AgentState:
        """Router node wrapper."""
        return self.router.route(state)
    
    def _plan(self, state: AgentState) -> AgentState:
        """Planner node wrapper."""
        return self.planner.plan(state)
    
    def _generate_sql(self, state: AgentState) -> AgentState:
        """SQL generator node wrapper."""
        return self.sql_generator.generate(state)
    
    def _execute(self, state: AgentState) -> AgentState:
        """Executor node wrapper."""
        return self.executor.execute(state)
    
    def _analyze(self, state: AgentState) -> AgentState:
        """Analyzer node wrapper."""
        return self.analyzer.analyze(state)
    
    def _respond(self, state: AgentState) -> AgentState:
        """Responder node wrapper."""
        return self.responder.respond(state)
    
    def _route_decision(self, state: AgentState) -> Literal["analysis", "schema", "general", "clarification"]:
        """Determine next node based on query type.
        
        Args:
            state: Current agent state
            
        Returns:
            Next node name
        """
        query_type = state.get("query_type", "general")
        return query_type
    
    def invoke(self, user_query: str, return_sql: bool = False):
        """Process a user query and return response.
        
        Args:
            user_query: The user's query
            return_sql: If True, return tuple of (response, sql_query)
            
        Returns:
            Agent's response string, or tuple (response, sql) if return_sql=True
        """
        logger.info(f"Processing query: {user_query[:50]}...")
        
        # Add user message to history
        self.messages.append(HumanMessage(content=user_query))
        
        # Create initial state
        state = create_initial_state(user_query, self.messages.copy())
        
        try:
            # Run the graph
            final_state = self.graph.invoke(state)
            
            # Get response and SQL
            response = final_state.get("response", "I couldn't generate a response.")
            sql_query = final_state.get("sql_query")
            
            # Add assistant message to history
            self.messages.append(AIMessage(content=response))
            
            if return_sql:
                return response, sql_query
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            error_response = "I encountered an error processing your request. Please try again."
            self.messages.append(AIMessage(content=error_response))
            if return_sql:
                return error_response, None
            return error_response
    
    def reset_conversation(self):
        """Reset conversation history."""
        self.messages = []
        logger.info("Conversation history reset")
