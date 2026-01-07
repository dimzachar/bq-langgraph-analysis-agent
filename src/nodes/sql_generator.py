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

Execution Plan:
{execution_plan}

Follow the execution plan above to generate a single SQL query.
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
            execution_plan = state.get("execution_plan", [])
            plan_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(execution_plan)) if execution_plan else "No specific plan - generate appropriate SQL"
            
            prompt = SQL_GENERATOR_PROMPT.format(
                schema_info=schema_info,
                query=query,
                execution_plan=plan_text
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
        """Check if SQL only references allowed tables and has no dangerous operations.
        
        Args:
            sql: SQL query string
            
        Returns:
            True if only allowed tables are referenced and no dangerous operations
        """
        sql_upper = sql.upper()
        
        # 
        # Block dangerous operations
        # Note: These would likely fail anyway due to BigQuery IAM
        # permissions (read-only access) and the fact that we're
        # querying a public dataset. Added as a safety net in case
        # permissions change or the agent is used with other datasets.
        # 

        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE',
            'CREATE', 'ALTER', 'GRANT', 'REVOKE', 'EXECUTE', 'MERGE'
        ]
        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', sql_upper):
                logger.warning(f"Dangerous keyword detected: {keyword}")
                return False
        
        # 
        # Block system table access to prevent discovering other tables/datasets in the project
        # 
        if 'INFORMATION_SCHEMA' in sql_upper or '__TABLES__' in sql_upper:
            logger.warning("System table access blocked")
            return False
        
        # Extract CTE names first (these are valid references within the query)
        cte_pattern = r'\bWITH\s+(\w+)\s+AS\s*\('
        cte_names = set(m.lower() for m in re.findall(cte_pattern, sql, re.IGNORECASE))
        
        # Also find chained CTEs: , cte_name AS (
        chained_cte_pattern = r',\s*(\w+)\s+AS\s*\('
        cte_names.update(m.lower() for m in re.findall(chained_cte_pattern, sql, re.IGNORECASE))
        
        logger.debug(f"Found CTE names: {cte_names}")
        
        # Extract table references from SQL patterns
        # This catches bypass attempts via UNION and subqueries
        table_patterns = [
            r'(?:FROM|JOIN)\s+[`"]?(?:[\w-]+\.)*(\w+)[`"]?',  # FROM/JOIN clauses
            r'UNION\s+(?:ALL\s+)?SELECT\s+.*?FROM\s+[`"]?(?:[\w-]+\.)*(\w+)[`"]?',  # UNION injection
        ]
        
        all_tables = set()
        for pattern in table_patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE | re.DOTALL)
            all_tables.update(t.lower() for t in matches if t)
        
        # Remove CTE names from table references (they're valid internal references)
        external_tables = all_tables - cte_names
        
        logger.debug(f"Extracted tables from SQL: {all_tables}")
        logger.debug(f"External tables (excluding CTEs): {external_tables}")
        
        for table in external_tables:
            if table not in ALLOWED_TABLES:
                logger.warning(f"Invalid table reference: {table}. Allowed: {ALLOWED_TABLES}")
                return False
        
        return True
