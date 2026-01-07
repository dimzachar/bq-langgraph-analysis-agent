import logging
from typing import Dict, Any, List

from src.state import AgentState
from src.verbose import print_header, print_step, print_success

logger = logging.getLogger(__name__)

ANALYZER_PROMPT = """You are a data analyst for an e-commerce business.

User Question: {query}

Executed SQL Query:
```sql
{sql_query}
```

Query Results ({row_count} rows):
{results_preview}

Analyze these results and provide:
1. Key findings and insights
2. Notable patterns or trends
3. Actionable recommendations

IMPORTANT: Base your analysis ONLY on the actual SQL query and results shown above.
If the user asked about tables/data that weren't queried, note what was actually analyzed.
Be specific and reference the actual data values.
Keep your analysis concise but insightful.
"""


class ResultAnalyzer:
    """Analyzes query results and extracts insights."""
    
    def __init__(self, llm_client):
        """Initialize analyzer.
        
        Args:
            llm_client: LLM client for analysis
        """
        self.llm = llm_client
    
    def analyze(self, state: AgentState) -> dict:
        """Analyze results and generate insights.
        
        Args:
            state: Current agent state
            
        Returns:
            Partial state update with analysis
        """
        results = state.get("query_results")
        query = state["current_query"]
        sql_query = state.get("sql_query", "No SQL available")
        
        if not results:
            logger.info("No results to analyze")
            return {}
        
        logger.info("Analyzing query results")
        print_header("Analyzer")
        row_count = results.get("row_count", 0)
        print_step(f"Analyzing {row_count} rows of data...")
        
        try:
            # Format results for LLM
            results_preview = self._format_results(results)
            
            prompt = ANALYZER_PROMPT.format(
                query=query,
                sql_query=sql_query,
                row_count=results.get("row_count", 0),
                results_preview=results_preview
            )
            
            analysis = self.llm.invoke_with_retry(prompt)
            logger.info("Analysis completed")
            print_success("Analysis complete - insights generated")
            return {"analysis": analysis}
            
        except Exception as e:
            logger.error(f"Error analyzing results: {e}")
            return {"error": f"Failed to analyze results: {str(e)}"}
    
    def _format_results(self, results: Dict[str, Any], max_rows: int = 20) -> str:
        """Format results for LLM prompt.
        
        Args:
            results: Query results dict
            max_rows: Maximum rows to include
            
        Returns:
            Formatted string representation
        """
        data = results.get("data", [])
        columns = results.get("columns", [])
        
        if not data:
            return "No data returned"
        
        # Limit rows for prompt
        preview_data = data[:max_rows]
        
        # Format as table-like structure
        lines = []
        
        # Header
        if columns:
            lines.append(" | ".join(str(col) for col in columns))
            lines.append("-" * 50)
        
        # Data rows
        for row in preview_data:
            if isinstance(row, dict):
                values = [str(row.get(col, ""))[:30] for col in columns]
            else:
                values = [str(v)[:30] for v in row]
            lines.append(" | ".join(values))
        
        if len(data) > max_rows:
            lines.append(f"... and {len(data) - max_rows} more rows")
        
        return "\n".join(lines)
