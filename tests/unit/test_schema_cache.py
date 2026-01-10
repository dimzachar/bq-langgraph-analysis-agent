"""Unit tests for schema cache.

Tests schema loading, retrieval, and prompt formatting.
**Validates: Requirements 3.1, 3.2**
"""

import pytest
from unittest.mock import MagicMock

from src.schema_cache import SchemaCache, ALLOWED_TABLES


class TestSchemaCache:
    """Unit tests for SchemaCache class."""
    
    @pytest.fixture
    def mock_bq_client(self):
        """Create a mock BigQuery client."""
        client = MagicMock()
        client.get_table_schema.return_value = [
            {"name": "id", "type": "INTEGER", "mode": "REQUIRED", "description": "Primary key"},
            {"name": "name", "type": "STRING", "mode": "NULLABLE", "description": "Name field"},
        ]
        return client
    
    @pytest.fixture
    def schema_cache(self, mock_bq_client):
        """Create a SchemaCache instance with mock client."""
        return SchemaCache(mock_bq_client)
    
    def test_load_all_schemas(self, schema_cache, mock_bq_client):
        """Test that all schemas are loaded for allowed tables."""
        schema_cache.load_all_schemas()
        
        assert mock_bq_client.get_table_schema.call_count == len(ALLOWED_TABLES)
        for table in ALLOWED_TABLES:
            mock_bq_client.get_table_schema.assert_any_call(table)
    
    def test_get_schema_after_load(self, schema_cache):
        """Test schema retrieval after loading."""
        schema_cache.load_all_schemas()
        
        schema = schema_cache.get_schema("users")
        assert len(schema) == 2
        assert schema[0]["name"] == "id"
    
    def test_get_schema_before_load_raises(self, schema_cache):
        """Test that getting schema before loading raises error."""
        with pytest.raises(RuntimeError, match="Schemas not loaded"):
            schema_cache.get_schema("users")
    
    def test_get_schema_invalid_table_raises(self, schema_cache):
        """Test that invalid table name raises error."""
        schema_cache.load_all_schemas()
        
        with pytest.raises(ValueError, match="not allowed"):
            schema_cache.get_schema("invalid_table")
    
    def test_get_schema_prompt_format(self, schema_cache):
        """Test schema prompt formatting."""
        schema_cache.load_all_schemas()
        
        prompt = schema_cache.get_schema_prompt()
        
        assert "Database Schema:" in prompt
        assert "Table: users" in prompt
        assert "Table: orders" in prompt
        assert "Table Relationships:" in prompt
    
    def test_get_all_column_names(self, schema_cache):
        """Test getting all column names for a table."""
        schema_cache.load_all_schemas()
        
        columns = schema_cache.get_all_column_names("users")
        
        assert "id" in columns
        assert "name" in columns
    
    def test_is_valid_column(self, schema_cache):
        """Test column validation."""
        schema_cache.load_all_schemas()
        
        assert schema_cache.is_valid_column("users", "id") is True
        assert schema_cache.is_valid_column("users", "nonexistent") is False
    
    def test_get_table_relationships(self, schema_cache):
        """Test getting table relationships."""
        relationships = schema_cache.get_table_relationships()
        
        assert "users.id" in relationships
        assert "orders.user_id" in relationships
