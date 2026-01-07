import logging
import re
from typing import Optional

from src.state import AgentState
from src.schema_cache import ALLOWED_TABLES
from src.verbose import print_header, print_step, print_sql, print_success, print_error

logger = logging.getLogger(__name__)

SQL_GENERATOR_PROMPT = """You are a SQL expert for Google BigQuery.

Database: bigquery-public-data.thelook_ecommerce

{schema_info}

IMPORTANT RULES:
1. Use ONLY these tables: orders, order_items, products, users
2. Always prefix tables with: bigquery-public-data.thelook_ecommerce
3. Include LIMIT clause (max 1000 rows) unless aggregating
4. Use proper BigQuery SQL syntax
5. Handle NULL values appropriately

User Query: {query}

Generate a single SQL query to answer this question.
Return ONLY the SQL query, no explanations.
"""


class SQLGenerator:
    """Generates BigQuery SQL from natural language."""
    
    def __init__(self, llm_client, schema_cache, dataset_id: str):
        """Initialize SQL generator.
        
        Args:
            llm_client: LLM client for SQL generation
            schema_cache: Schema cache for table information
            dataset_id: BigQuery dataset ID (from config)
        """
        self.llm = llm_client
        self.schema_cache = schema_cache
        self.dataset_id = dataset_id
    
    def generate(self, state: AgentState) -> dict:
        """Generate SQL query based on plan and schema.
        
        Args:
            state: Current agent state
            
        Returns:
            Partial state update with sql_query set
        """
        query = state["current_query"]
        query_type = state["query_type"]
        
        # Only generate SQL for analysis queries
        if query_type != "analysis":
            logger.info(f"Skipping SQL generation for {query_type} query")
            return {}
        
        logger.info("Generating SQL query")
        print_header("SQL Generator")
        print_step("Generating SQL from natural language...")
        
        try:
            schema_info = self.schema_cache.get_schema_prompt()
            prompt = SQL_GENERATOR_PROMPT.format(
                schema_info=schema_info,
                query=query
            )
            
            response = self.llm.invoke_with_retry(prompt)
            sql = self._extract_sql(response)
            
            # Validate SQL
            if sql:
                # Check for unauthorized table references
                if not self.validate_tables(sql):
                    print_error("SQL references unauthorized tables")
                    return {"error": "I can only query the e-commerce dataset tables."}
                
                sql = self._validate_and_fix_sql(sql)
                logger.info(f"Generated SQL: {sql[:100]}...")
                print_sql(sql)
                print_success("SQL generated successfully")
                return {"sql_query": sql}
            else:
                print_error("Failed to generate valid SQL")
                return {"error": "Failed to generate valid SQL"}
                
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            print_error(f"SQL generation failed: {str(e)[:50]}")
            return {"error": f"Failed to generate SQL: {str(e)}"}
    
    def _extract_sql(self, response: str) -> Optional[str]:
        """Extract SQL from LLM response.
        
        Args:
            response: LLM response string
            
        Returns:
            Extracted SQL query or None
        """
        # Try to extract SQL from code blocks
        sql_match = re.search(r'```(?:sql)?\s*(.*?)```', response, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        # If no code block, assume entire response is SQL
        sql = response.strip()
        if sql.upper().startswith(('SELECT', 'WITH')):
            return sql
        
        return None
    
    def _validate_and_fix_sql(self, sql: str) -> str:
        """Validate and fix common SQL issues.
        
        Args:
            sql: SQL query string
            
        Returns:
            Validated/fixed SQL query
        """
        # Ensure tables are properly prefixed
        for table in ALLOWED_TABLES:
            # Replace unqualified table references
            pattern = rf'\b(?<!\.){table}\b(?!\s*\.)'
            replacement = f"`{self.dataset_id}.{table}`"
            sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
        
        # Add LIMIT if not present and not an aggregate query
        if 'LIMIT' not in sql.upper():
            # Check if it's likely an aggregate query
            aggregate_keywords = ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN(', 'GROUP BY']
            is_aggregate = any(kw in sql.upper() for kw in aggregate_keywords)
            
            if not is_aggregate:
                sql = sql.rstrip(';') + ' LIMIT 100'
        
        return sql
    
    def validate_tables(self, sql: str) -> bool:
        """Check if SQL only references allowed tables.
        
        Args:
            sql: SQL query string
            
        Returns:
            True if only allowed tables are referenced
        """
        # Extract table references from SQL
        # This is a simplified check
        sql_upper = sql.upper()
        
        # Look for FROM and JOIN clauses
        # Handle fully qualified BigQuery tables: `project.dataset.table`
        table_pattern = r'(?:FROM|JOIN)\s+[`"]?(?:[\w-]+\.)*(\w+)[`"]?'
        matches = re.findall(table_pattern, sql, re.IGNORECASE)
        
        for table in matches:
            if table.lower() not in ALLOWED_TABLES:
                logger.warning(f"Invalid table reference: {table}")
                return False
        
        return True
