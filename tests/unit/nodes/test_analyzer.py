"""Unit tests for Result Analyzer node."""

import pytest
from unittest.mock import MagicMock

from src.nodes.analyzer import ResultAnalyzer
from src.state import create_initial_state


class TestResultAnalyzer:
    """Unit tests for ResultAnalyzer class."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        llm = MagicMock()
        llm.invoke_with_retry.return_value = "Analysis: The data shows interesting patterns."
        return llm
    
    @pytest.fixture
    def analyzer(self, mock_llm):
        """Create analyzer with mock LLM."""
        return ResultAnalyzer(mock_llm)
    
    def test_analyze_with_results(self, analyzer):
        """Test analysis with query results."""
        state = create_initial_state("Analyze sales")
        state["query_results"] = {
            "data": [{"category": "A", "revenue": 100}],
            "row_count": 1,
            "columns": ["category", "revenue"]
        }
        
        result = analyzer.analyze(state)
        
        assert result["analysis"] is not None
        assert "Analysis" in result["analysis"]
    
    def test_analyze_without_results(self, analyzer):
        """Test analysis without query results."""
        state = create_initial_state("Analyze")
        state["query_results"] = None
        
        result = analyzer.analyze(state)
        
        assert result.get("analysis") is None
    
    def test_analyze_empty_results(self, analyzer):
        """Test analysis with empty results."""
        state = create_initial_state("Analyze")
        state["query_results"] = {
            "data": [],
            "row_count": 0,
            "columns": []
        }
        
        result = analyzer.analyze(state)
        
        # Should still attempt analysis
        assert result.get("analysis") is not None or result.get("error") is None
    
    def test_format_results_limits_rows(self, analyzer):
        """Test that result formatting limits rows."""
        results = {
            "data": [{"id": i} for i in range(100)],
            "row_count": 100,
            "columns": ["id"]
        }
        
        formatted = analyzer._format_results(results, max_rows=20)
        
        assert "more rows" in formatted
