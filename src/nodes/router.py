import logging
from typing import Literal

from src.state import AgentState
from src.verbose import print_header, print_decision, print_step

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """You are a query classifier for an e-commerce data analysis system.

Classify the following user query into one of these categories:
- "schema": Questions about database structure, tables, columns, or relationships
- "analysis": Questions requiring SQL queries and data analysis (sales, customers, products, trends)
- "general": General questions, greetings, or questions not related to data
- "clarification": Ambiguous queries that need more information

User Query: {query}

Respond with ONLY one word: schema, analysis, general, or clarification
"""


class QueryRouter:
    """Routes queries to appropriate processing paths."""
    
    def __init__(self, llm_client):
        """Initialize router with LLM client.
        
        Args:
            llm_client: LLM client for classification
        """
        self.llm = llm_client
    
    def route(self, state: AgentState) -> dict:
        """Classify query and determine routing.
        
        Args:
            state: Current agent state
            
        Returns:
            Partial state update with query_type set
        """
        query = state["current_query"]
        logger.info(f"Routing query: {query[:50]}...")
        
        print_header("Router")
        print_step(f"Classifying: \"{query[:60]}{'...' if len(query) > 60 else ''}\"")
        
        try:
            prompt = ROUTER_PROMPT.format(query=query)
            response = self.llm.invoke_with_retry(prompt)
            
            # Parse response to get query type
            query_type = self._parse_query_type(response.strip().lower())
            
            logger.info(f"Query classified as: {query_type}")
            print_decision(query_type, self._get_route_description(query_type))
            return {"query_type": query_type}
            
        except Exception as e:
            logger.error(f"Error routing query: {e}")
            return {"error": f"Failed to classify query: {str(e)}", "query_type": "general"}
    
    def _get_route_description(self, query_type: str) -> str:
        """Get human-readable description for route."""
        descriptions = {
            "schema": "Will explain database structure",
            "analysis": "Will generate SQL and analyze data",
            "general": "Will respond directly without data query",
            "clarification": "Will ask for more details"
        }
        return descriptions.get(query_type, "")
    
    def _parse_query_type(self, response: str) -> Literal["schema", "analysis", "general", "clarification"]:
        """Parse LLM response to extract query type.
        
        Args:
            response: LLM response string
            
        Returns:
            Validated query type
        """
        valid_types = ["schema", "analysis", "general", "clarification"]
        
        # Check if response contains a valid type
        for qtype in valid_types:
            if qtype in response:
                return qtype
        
        # Default to general if unclear
        return "general"
