import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Allowed tables in the thelook_ecommerce dataset
ALLOWED_TABLES = ["orders", "order_items", "products", "users"]

# Table relationships description
TABLE_RELATIONSHIPS = """
Table Relationships:
- users.id -> orders.user_id (One user can have many orders)
- users.id -> order_items.user_id (One user can have many order items)
- orders.order_id -> order_items.order_id (One order contains many order items)
- products.id -> order_items.product_id (One product can be in many order items)
"""


class SchemaCache:
    """Caches and provides schema information for BigQuery tables."""
    
    def __init__(self, bq_client):
        """Initialize schema cache.
        
        Args:
            bq_client: BigQueryRunner instance for fetching schemas
        """
        self.bq_client = bq_client
        self.schemas: Dict[str, List[Dict[str, Any]]] = {}
        self._loaded = False
    
    def load_all_schemas(self) -> None:
        """Load schemas for all allowed tables."""
        logger.info("Loading schemas for all tables...")
        
        for table_name in ALLOWED_TABLES:
            try:
                schema = self.bq_client.get_table_schema(table_name)
                self.schemas[table_name] = schema
                logger.info(f"Loaded schema for table: {table_name}")
            except Exception as e:
                logger.error(f"Failed to load schema for {table_name}: {e}")
                raise
        
        self._loaded = True
        logger.info("All schemas loaded successfully")
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column definitions
            
        Raises:
            ValueError: If table is not in allowed tables
            RuntimeError: If schemas haven't been loaded
        """
        if table_name not in ALLOWED_TABLES:
            raise ValueError(f"Table '{table_name}' is not allowed. Allowed tables: {ALLOWED_TABLES}")
        
        if not self._loaded:
            raise RuntimeError("Schemas not loaded. Call load_all_schemas() first.")
        
        return self.schemas.get(table_name, [])
    
    def get_schema_prompt(self) -> str:
        """Get formatted schema information for LLM prompts.
        
        Returns:
            Formatted string with all table schemas
        """
        if not self._loaded:
            raise RuntimeError("Schemas not loaded. Call load_all_schemas() first.")
        
        prompt_parts = ["Database Schema:\n"]
        
        for table_name in ALLOWED_TABLES:
            schema = self.schemas.get(table_name, [])
            prompt_parts.append(f"\nTable: {table_name}")
            prompt_parts.append("-" * 40)
            
            for col in schema:
                col_info = f"  - {col['name']} ({col['type']})"
                if col.get('description'):
                    col_info += f": {col['description']}"
                prompt_parts.append(col_info)
        
        prompt_parts.append(f"\n{TABLE_RELATIONSHIPS}")
        
        return "\n".join(prompt_parts)
    
    def get_table_relationships(self) -> str:
        """Get description of table relationships.
        
        Returns:
            String describing table relationships
        """
        return TABLE_RELATIONSHIPS
    
    def get_all_column_names(self, table_name: str) -> List[str]:
        """Get all column names for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names
        """
        schema = self.get_schema(table_name)
        return [col['name'] for col in schema]
    
    def is_valid_column(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            
        Returns:
            True if column exists, False otherwise
        """
        columns = self.get_all_column_names(table_name)
        return column_name in columns
