import logging
from typing import Optional

from src.state import AgentState
from src.verbose import (
    print_header, print_step, print_success, print_error, 
    print_retry, print_results_summary, print_sql
)

logger = logging.getLogger(__name__)

SQL_FIX_PROMPT = """The following SQL query failed with this error:

SQL: {sql}
Error: {error}

Please fix the SQL query. Return ONLY the corrected SQL, no explanations.
"""


class QueryExecutor:
    """Executes SQL queries against BigQuery."""
    
    def __init__(self, bq_client, llm_client, max_retries: int = 2):
        """Initialize executor.
        
        Args:
            bq_client: BigQuery client for query execution
            llm_client: LLM client for SQL correction
            max_retries: Maximum retry attempts for failed queries
        """
        self.bq_client = bq_client
        self.llm = llm_client
        self.max_retries = max_retries
    
    def execute(self, state: AgentState) -> dict:
        """Execute SQL and store results in state.
        
        Args:
            state: Current agent state
            
        Returns:
            Partial state update with query_results or error
        """
        sql = state.get("sql_query")
        
        if not sql:
            logger.info("No SQL query to execute")
            return {}
        
        logger.info("Executing SQL query")
        print_header("Executor")
        print_step("Executing query against BigQuery...")
        
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                df = self.bq_client.execute_query(sql)
                
                logger.info(f"Query executed successfully, {len(df)} rows returned")
                print_results_summary(len(df), list(df.columns))
                return {
                    "query_results": {
                        "data": df.to_dict(orient="records"),
                        "row_count": len(df),
                        "columns": list(df.columns)
                    },
                    "error": None
                }
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Query failed (attempt {retry_count + 1}): {error_msg}")
                
                if retry_count < self.max_retries:
                    print_retry(retry_count + 1, self.max_retries, "SQL error, attempting fix...")
                    fixed_sql = self._attempt_fix(sql, error_msg)
                    if fixed_sql and fixed_sql != sql:
                        print_step("LLM suggested SQL fix")
                        print_sql(fixed_sql)
                        sql = fixed_sql
                        retry_count += 1
                        continue
                
                # Max retries reached or couldn't fix
                print_error(f"Query failed after {retry_count + 1} attempts")
                return {
                    "sql_query": sql,
                    "error": f"Query failed after {retry_count + 1} attempts: {error_msg}",
                    "retry_count": retry_count
                }
        
        return {}
    
    def _attempt_fix(self, sql: str, error: str) -> Optional[str]:
        """Attempt to fix SQL using LLM.
        
        Args:
            sql: Failed SQL query
            error: Error message
            
        Returns:
            Fixed SQL or None
        """
        try:
            prompt = SQL_FIX_PROMPT.format(sql=sql, error=error)
            response = self.llm.invoke_with_retry(prompt)
            
            # Extract SQL from response
            fixed_sql = response.strip()
            if fixed_sql.startswith('```'):
                # Remove code blocks
                lines = fixed_sql.split('\n')
                fixed_sql = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
            
            return fixed_sql.strip()
            
        except Exception as e:
            logger.error(f"Failed to fix SQL: {e}")
            return None
