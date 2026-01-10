"""Unit tests for SQL Generator node."""

import pytest
from unittest.mock import MagicMock

from src.nodes.sql_generator import SQLGenerator
from src.state import create_initial_state


class TestSQLGenerator:
    """Unit tests for SQLGenerator class."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        llm = MagicMock()
        llm.invoke_with_retry.return_value = "SELECT * FROM users LIMIT 10"
        return llm
    
    @pytest.fixture
    def mock_schema_cache(self):
        """Create a mock schema cache."""
        cache = MagicMock()
        cache.get_schema_prompt.return_value = "Schema info"
        return cache
    
    @pytest.fixture
    def generator(self, mock_llm, mock_schema_cache):
        """Create generator with mocks."""
        return SQLGenerator(mock_llm, mock_schema_cache, "bigquery-public-data.thelook_ecommerce")
    
    def test_generate_sql_for_analysis(self, generator, mock_llm):
        """Test SQL generation for analysis query."""
        mock_llm.invoke_with_retry.return_value = "SELECT COUNT(*) FROM users"
        state = create_initial_state("Count users")
        state["query_type"] = "analysis"
        
        result = generator.generate(state)
        
        assert result["sql_query"] is not None
        assert "SELECT" in result["sql_query"].upper()
    
    def test_skip_sql_for_non_analysis(self, generator):
        """Test that SQL is not generated for non-analysis queries."""
        state = create_initial_state("Hello")
        state["query_type"] = "general"
        
        result = generator.generate(state)
        
        assert result.get("sql_query") is None
    
    def test_extract_sql_from_code_block(self, generator, mock_llm):
        """Test SQL extraction from markdown code block."""
        mock_llm.invoke_with_retry.return_value = "```sql\nSELECT * FROM users\n```"
        state = create_initial_state("Get users")
        state["query_type"] = "analysis"
        
        result = generator.generate(state)
        
        # SQL should be extracted and may have dataset prefix added
        assert result["sql_query"] is not None
        assert "SELECT" in result["sql_query"].upper()
        assert "users" in result["sql_query"].lower()
    
    def test_validate_tables_allowed(self, generator):
        """Test table validation for allowed tables."""
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        assert generator.validate_tables(sql) is True
    
    def test_validate_tables_rejected(self, generator):
        """Test table validation rejects unknown tables."""
        sql = "SELECT * FROM unknown_table"
        assert generator.validate_tables(sql) is False


class TestSQLInjectionProtection:
    """Tests for SQL injection protection."""

    @pytest.fixture
    def generator(self):
        """Create generator with mocks."""
        mock_llm = MagicMock()
        mock_schema_cache = MagicMock()
        return SQLGenerator(mock_llm, mock_schema_cache, "bigquery-public-data.thelook_ecommerce")

    # Dangerous keyword tests
    @pytest.mark.parametrize("sql,description", [
        ("INSERT INTO users VALUES (1, 'hacker')", "INSERT blocked"),
        ("UPDATE users SET name = 'hacked'", "UPDATE blocked"),
        ("DELETE FROM users WHERE id = 1", "DELETE blocked"),
        ("DROP TABLE users", "DROP blocked"),
        ("TRUNCATE TABLE users", "TRUNCATE blocked"),
        ("CREATE TABLE evil (id INT)", "CREATE blocked"),
        ("ALTER TABLE users ADD COLUMN evil TEXT", "ALTER blocked"),
        ("GRANT SELECT ON users TO hacker", "GRANT blocked"),
        ("MERGE INTO users USING evil ON true", "MERGE blocked"),
    ])
    def test_dangerous_keywords_blocked(self, generator, sql, description):
        """Test that dangerous SQL keywords are blocked."""
        assert generator.validate_tables(sql) is False, description

    # System table access tests
    @pytest.mark.parametrize("sql,description", [
        ("SELECT * FROM INFORMATION_SCHEMA.TABLES", "INFORMATION_SCHEMA blocked"),
        ("SELECT * FROM `region-us`.INFORMATION_SCHEMA.TABLES", "Qualified INFORMATION_SCHEMA blocked"),
        ("SELECT * FROM __TABLES__", "__TABLES__ blocked"),
    ])
    def test_system_tables_blocked(self, generator, sql, description):
        """Test that system table access is blocked."""
        assert generator.validate_tables(sql) is False, description

    # UNION injection tests
    @pytest.mark.parametrize("sql,description", [
        ("SELECT * FROM users UNION SELECT * FROM secret_table", "UNION with unauthorized table"),
        ("SELECT * FROM users UNION ALL SELECT * FROM evil", "UNION ALL with unauthorized table"),
    ])
    def test_union_injection_blocked(self, generator, sql, description):
        """Test that UNION-based injection is blocked."""
        assert generator.validate_tables(sql) is False, description

    # Subquery tests
    @pytest.mark.parametrize("sql,description", [
        ("SELECT * FROM users WHERE id IN (SELECT user_id FROM evil_table)", "Subquery with unauthorized table"),
    ])
    def test_subquery_injection_blocked(self, generator, sql, description):
        """Test that subqueries with unauthorized tables are blocked."""
        assert generator.validate_tables(sql) is False, description

    # CTE tests
    @pytest.mark.parametrize("sql,description", [
        ("WITH stolen AS (SELECT * FROM secret_table) SELECT * FROM users", "CTE with unauthorized table"),
    ])
    def test_cte_injection_blocked(self, generator, sql, description):
        """Test that CTEs with unauthorized tables are blocked."""
        assert generator.validate_tables(sql) is False, description

    # Valid queries should still pass
    @pytest.mark.parametrize("sql,description", [
        ("SELECT * FROM users", "Simple select"),
        ("SELECT * FROM users JOIN orders ON users.id = orders.user_id", "JOIN allowed tables"),
        ("SELECT * FROM users UNION SELECT * FROM orders", "UNION allowed tables"),
        ("WITH user_orders AS (SELECT * FROM orders) SELECT * FROM users", "CTE with allowed tables"),
        ("SELECT COUNT(*) FROM order_items GROUP BY product_id", "Aggregate query"),
    ])
    def test_valid_queries_allowed(self, generator, sql, description):
        """Test that valid queries with allowed tables pass."""
        assert generator.validate_tables(sql) is True, description

    # Complex CTE queries should pass when referencing CTE names
    @pytest.mark.parametrize("sql,description", [
        (
            "WITH customer_segments AS (SELECT * FROM users) SELECT * FROM customer_segments",
            "CTE reference in main query"
        ),
        (
            "WITH cte1 AS (SELECT * FROM users), cte2 AS (SELECT * FROM orders) SELECT * FROM cte1 JOIN cte2 ON cte1.id = cte2.user_id",
            "Multiple CTEs with cross-reference"
        ),
        (
            "WITH segments AS (SELECT * FROM users), products_cte AS (SELECT * FROM products) SELECT * FROM segments UNION ALL SELECT * FROM products_cte",
            "CTEs with UNION ALL"
        ),
    ])
    def test_cte_self_references_allowed(self, generator, sql, description):
        """Test that CTEs referencing their own names are allowed."""
        assert generator.validate_tables(sql) is True, description
