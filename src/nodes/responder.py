import logging
import re
from typing import Set

from src.state import AgentState
from src.verbose import print_header, print_step, print_success, print_warning

logger = logging.getLogger(__name__)

RESPONSE_PROMPT = """You are a helpful data analysis assistant.

User Question: {query}
Query Type: {query_type}

{context}

Generate a clear, helpful response for the user.
If there's analysis, summarize the key insights.
If there's an error, explain it in user-friendly terms.
Be conversational but professional.
"""

SCHEMA_RESPONSE_PROMPT = """You are a helpful database assistant.

User Question: {query}

Database Schema:
{schema_info}

Provide a clear explanation of the database structure based on the user's question.
"""


class ResponseGenerator:
    """Generates natural language responses."""
    
    def __init__(self, llm_client, schema_cache=None):
        """Initialize responder.
        
        Args:
            llm_client: LLM client for response generation
            schema_cache: Optional schema cache for schema queries
        """
        self.llm = llm_client
        self.schema_cache = schema_cache
    
    def respond(self, state: AgentState) -> dict:
        """Generate final response for user.
        
        Args:
            state: Current agent state
            
        Returns:
            Partial state update with response
        """
        query = state["current_query"]
        query_type = state.get("query_type", "general")
        
        logger.info(f"Generating response for {query_type} query")
        print_header("Responder")
        print_step(f"Generating {query_type} response...")
        
        try:
            if query_type == "schema" and self.schema_cache:
                response = self._generate_schema_response(query)
            elif state.get("error"):
                print_step("Handling error gracefully...")
                response = self._generate_error_response(state)
            elif state.get("analysis"):
                response = self._generate_analysis_response(state)
            elif query_type == "clarification":
                response = self._generate_clarification_response(query)
            else:
                response = self._generate_general_response(state)
            
            logger.info("Response generated")
            print_success("Response ready")
            return {"response": response}
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {"response": "I apologize, but I encountered an issue generating a response. Please try rephrasing your question."}
    
    def _generate_schema_response(self, query: str) -> str:
        """Generate response for schema queries."""
        schema_info = self.schema_cache.get_schema_prompt()
        
        prompt = SCHEMA_RESPONSE_PROMPT.format(
            query=query,
            schema_info=schema_info
        )
        
        return self.llm.invoke_with_retry(prompt)
    
    def _generate_analysis_response(self, state: AgentState) -> str:
        """Generate response for analysis queries."""
        context = f"Analysis:\n{state['analysis']}"
        
        # Include actual data so LLM doesn't hallucinate values
        actual_numbers: Set[str] = set()
        if state.get("query_results"):
            results = state["query_results"]
            row_count = results.get("row_count", 0)
            columns = results.get("columns", [])
            data = results.get("data", [])
            
            context += f"\n\nActual Data ({row_count} rows):\n"
            context += " | ".join(columns) + "\n"
            context += "-" * 50 + "\n"
            
            # Include all rows (limited to 20 for prompt size)
            for row in data[:20]:
                values = [str(row.get(col, ""))[:40] for col in columns]
                context += " | ".join(values) + "\n"
                # Collect actual numbers for validation
                for val in row.values():
                    if isinstance(val, (int, float)):
                        actual_numbers.add(str(int(val)))  # Store as int string
                        if isinstance(val, float):
                            actual_numbers.add(f"{val:.2f}")  # Also store formatted
            
            if row_count > 20:
                context += f"... and {row_count - 20} more rows\n"
            
            context += "\nIMPORTANT: Use the EXACT values from the data above. Do not make up or approximate numbers."
        
        prompt = RESPONSE_PROMPT.format(
            query=state["current_query"],
            query_type=state["query_type"],
            context=context
        )
        
        response = self.llm.invoke_with_retry(prompt)
        
        # Validate response numbers against actual data
        if actual_numbers:
            self._validate_response_numbers(response, actual_numbers)
        
        return response
    
    def _validate_response_numbers(self, response: str, actual_numbers: Set[str]) -> None:
        """Check if numbers in response match actual data. Logs warning if mismatch found.
        
        Args:
            response: Generated response text
            actual_numbers: Set of numbers from actual query results
        """
        # Extract numbers from response (integers and decimals)
        response_numbers = set(re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', response))
        
        # Normalize numbers (remove commas)
        normalized_response = {n.replace(',', '') for n in response_numbers}
        
        # Filter out small numbers that are likely list indices or common values
        significant_numbers = {n for n in normalized_response 
                             if len(n) > 1 or int(float(n)) > 10}
        
        # Check for numbers not in actual data
        suspicious = significant_numbers - actual_numbers
        
        # Filter out numbers that might be derived (percentages, rankings)
        truly_suspicious = {n for n in suspicious 
                          if not any(n.startswith(a[:3]) for a in actual_numbers)}
        
        if truly_suspicious and len(truly_suspicious) > 3:
            logger.warning(f"Possible hallucinated numbers in response: {truly_suspicious}")
            print_warning(f"Some numbers may not match source data")
    
    def _generate_error_response(self, state: AgentState) -> str:
        """Generate user-friendly error response with suggestions."""
        error = state.get("error", "Unknown error")
        query = state.get("current_query", "")
        sql = state.get("sql_query")
        
        # Create user-friendly message based on error type
        if "timeout" in error.lower():
            return "The query took too long to execute. Try asking for a smaller date range or fewer columns."
        elif "syntax" in error.lower():
            return "I had trouble constructing the query. Could you rephrase your question?"
        elif "permission" in error.lower() or "access" in error.lower():
            return "There seems to be an access issue with the database. Please check your credentials."
        elif "Query failed after" in error:
            # SQL execution failed after retries - provide helpful suggestions
            suggestions = self._get_query_suggestions(query, error)
            return (
                "I wasn't able to execute the query successfully. "
                f"{suggestions}\n\n"
                "You could try:\n"
                "• Simplifying your question\n"
                "• Asking about a specific table (orders, products, users, order_items)\n"
                "• Being more specific about the time period or metrics you want"
            )
        else:
            return "I encountered an issue while processing your request. Please try rephrasing your question or ask something else."
    
    def _get_query_suggestions(self, query: str, error: str) -> str:
        """Get context-specific suggestions based on the failed query."""
        query_lower = query.lower()
        
        if "join" in error.lower() or "column" in error.lower():
            return "The query involved complex table relationships that couldn't be resolved."
        elif any(word in query_lower for word in ["trend", "over time", "monthly", "daily"]):
            return "Time-based analysis can be tricky. Try specifying exact date ranges."
        elif any(word in query_lower for word in ["top", "best", "most"]):
            return "Ranking queries work best with specific metrics like revenue, quantity, or count."
        else:
            return "The data structure didn't match what was expected."
    
    def _generate_clarification_response(self, query: str) -> str:
        """Generate clarification request."""
        return f"I'd like to help, but I need a bit more information. Could you please clarify what specific data or analysis you're looking for? For example, you could ask about:\n- Customer segments and behavior\n- Product performance\n- Sales trends\n- Geographic patterns"
    
    def _generate_general_response(self, state: AgentState) -> str:
        """Generate response for general queries."""
        prompt = RESPONSE_PROMPT.format(
            query=state["current_query"],
            query_type=state.get("query_type", "general"),
            context="This is a general question not requiring data analysis."
        )
        
        return self.llm.invoke_with_retry(prompt)
