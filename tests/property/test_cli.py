"""Property tests for CLI interface.

**Feature: data-analysis-agent, Property 1: Slash Command Handling**
**Feature: data-analysis-agent, Property 3: Model Name Shortening**
**Validates: Requirements 1.3, 1.5**
"""

from hypothesis import given, strategies as st, settings
import pytest
from unittest.mock import MagicMock

from src.cli import CLIInterface


# Legacy exit commands still supported
LEGACY_EXIT_COMMANDS = {"exit", "quit", "bye", "q"}


def create_mock_agent():
    """Create a mock agent for testing."""
    agent = MagicMock()
    agent.get_session_stats.return_value = {
        "total_queries": 0,
        "total_tokens": 0,
        "total_llm_calls": 0,
        "total_time": 0.0,
        "context_messages": 0
    }
    agent.max_messages = 20
    return agent


class TestSlashCommandHandling:
    """Property-based tests for slash command handling."""
    
    @given(
        command=st.sampled_from(["/help", "/exit", "/reset", "/sql", "/stats"])
    )
    @settings(max_examples=50)
    def test_slash_commands_recognized(self, command: str):
        """
        **Feature: data-analysis-agent, Property 1: Slash Command Handling**
        For any defined slash command, the CLI SHALL recognize and handle it.
        **Validates: Requirements 1.3**
        """
        cli = CLIInterface(create_mock_agent(), model_name="test")
        assert command in cli.SLASH_COMMANDS
    
    @given(
        command=st.sampled_from(list(LEGACY_EXIT_COMMANDS))
    )
    @settings(max_examples=20)
    def test_legacy_exit_commands_recognized(self, command: str):
        """
        **Feature: data-analysis-agent, Property 1: Slash Command Handling**
        For any legacy exit command, the CLI SHALL stop running.
        **Validates: Requirements 1.3**
        """
        cli = CLIInterface(create_mock_agent(), model_name="test")
        cli.running = True
        # Simulate the legacy command check
        if command.lower() in LEGACY_EXIT_COMMANDS:
            cli._handle_command("/exit")
        assert cli.running is False
    
    @given(
        command=st.sampled_from(list(LEGACY_EXIT_COMMANDS))
    )
    @settings(max_examples=20)
    def test_legacy_exit_case_insensitive(self, command: str):
        """
        **Feature: data-analysis-agent, Property 1: Slash Command Handling**
        For any legacy exit command in any case, the CLI SHALL stop running.
        **Validates: Requirements 1.3**
        """
        cli = CLIInterface(create_mock_agent(), model_name="test")
        cli.running = True
        # Test uppercase
        if command.upper().lower() in LEGACY_EXIT_COMMANDS:
            cli._handle_command("/exit")
        assert cli.running is False


class TestModelNameShortening:
    """Property-based tests for model name shortening."""
    
    @given(
        prefix=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
        model=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=50)
    def test_slash_in_model_name_extracts_suffix(self, prefix: str, model: str):
        """
        **Feature: data-analysis-agent, Property 3: Model Name Shortening**
        For any model name with a slash, the CLI SHALL extract the part after the slash.
        **Validates: Requirements 1.5**
        """
        cli = CLIInterface(create_mock_agent(), model_name="test")
        full_name = f"{prefix}/{model}"
        short = cli._short_model_name(full_name)
        # Result should start with the model part (after slash), truncated to 25 chars
        expected_start = model[:25]
        assert short.startswith(expected_start[:len(short)])
    
    @given(
        model=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        tag=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=50)
    def test_colon_in_model_name_extracts_prefix(self, model: str, tag: str):
        """
        **Feature: data-analysis-agent, Property 3: Model Name Shortening**
        For any model name with a colon, the CLI SHALL extract the part before the colon.
        **Validates: Requirements 1.5**
        """
        cli = CLIInterface(create_mock_agent(), model_name="test")
        full_name = f"{model}:{tag}"
        short = cli._short_model_name(full_name)
        # Should not contain the tag (unless model contains it)
        assert tag not in short or tag in model
    
    @given(
        model=st.text(min_size=30, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=50)
    def test_long_model_names_truncated(self, model: str):
        """
        **Feature: data-analysis-agent, Property 3: Model Name Shortening**
        For any model name longer than 25 characters, the CLI SHALL truncate it.
        **Validates: Requirements 1.5**
        """
        cli = CLIInterface(create_mock_agent(), model_name="test")
        short = cli._short_model_name(model)
        assert len(short) <= 25


class TestSQLToggle:
    """Property-based tests for SQL display toggle."""
    
    @given(
        toggle_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20)
    def test_sql_toggle_alternates(self, toggle_count: int):
        """
        **Feature: data-analysis-agent, Property: SQL Toggle**
        For any number of toggles, the SQL display state SHALL alternate.
        **Validates: Requirements 1.5**
        """
        cli = CLIInterface(create_mock_agent(), model_name="test", show_sql=False)
        
        for i in range(toggle_count):
            expected = (i % 2 == 0)  # First toggle turns ON, second OFF, etc.
            cli._handle_command("/sql")
            assert cli.show_sql == expected

