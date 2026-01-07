import logging
from typing import List

from src.state import AgentState
from src.verbose import print_header, print_step, print_success

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """You are a query planner for an e-commerce data analysis system.

Available tables:
{schema_info}

User Query: {query}
Query Type: {query_type}

Create a brief execution plan. List the steps needed to answer this query.
For analysis queries, identify which tables and columns are needed.

Respond with a numbered list of steps (max 5 steps).
"""


class QueryPlanner:
    """Plans the execution strategy for analysis queries."""
    
    def __init__(self, llm_client, schema_cache):
        """Initialize planner with LLM client and schema cache.
        
        Args:
            llm_client: LLM client for planning
            schema_cache: Schema cache for table information
        """
        self.llm = llm_client
        self.schema_cache = schema_cache
    
    def plan(self, state: AgentState) -> dict:
        """Create execution plan based on query type.
        
        Args:
            state: Current agent state
            
        Returns:
            Partial state update with execution_plan set
        """
        query = state["current_query"]
        query_type = state["query_type"]
        
        logger.info(f"Planning execution for {query_type} query")
        print_header("Planner")
        print_step(f"Creating execution plan for {query_type} query")
        
        # For general queries, no complex planning needed
        if query_type == "general":
            print_success("Plan: Direct response (no data query needed)")
            return {"execution_plan": ["Generate direct response"]}
        
        # For schema queries, plan is straightforward
        if query_type == "schema":
            print_success("Plan: Retrieve and explain schema")
            return {"execution_plan": ["Retrieve schema information", "Format schema for user"]}
        
        # For clarification, ask for more details
        if query_type == "clarification":
            print_success("Plan: Request clarification")
            return {"execution_plan": ["Request clarification from user"]}
        
        # For analysis queries, use LLM to create detailed plan
        try:
            schema_info = self.schema_cache.get_schema_prompt()
            prompt = PLANNER_PROMPT.format(
                schema_info=schema_info,
                query=query,
                query_type=query_type
            )
            
            response = self.llm.invoke_with_retry(prompt)
            plan = self._parse_plan(response)
            
            logger.info(f"Created plan with {len(plan)} steps")
            print_success(f"Plan created with {len(plan)} steps")
            for i, step in enumerate(plan[:3], 1):  # Show first 3 steps
                print_step(f"  {i}. {step[:50]}{'...' if len(step) > 50 else ''}")
            if len(plan) > 3:
                print_step(f"  ... and {len(plan) - 3} more steps")
            
            return {"execution_plan": plan}
            
        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            return {"error": f"Failed to create execution plan: {str(e)}", "execution_plan": ["Execute query directly"]}
    
    def _parse_plan(self, response: str) -> List[str]:
        """Parse LLM response to extract plan steps.
        
        Args:
            response: LLM response string
            
        Returns:
            List of plan steps
        """
        lines = response.strip().split('\n')
        plan = []
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering and bullets
                step = line.lstrip('0123456789.-) ').strip()
                if step:
                    plan.append(step)
        
        return plan if plan else ["Execute query"]
