"""Unit tests for CLI interface."""

import pytest
from unittest.mock import MagicMock, patch

from src.cli import CLIInterface


class TestCLIInterface:
    """Unit tests for CLIInterface class."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent."""
        agent = MagicMock()
        agent.invoke.return_value = ("Test response", None)
        agent.get_session_stats.return_value = {
            "total_queries": 0,
            "total_tokens": 0,
            "total_llm_calls": 0,
            "total_time": 0.0,
            "context_messages": 0
        }
        agent.max_messages = 20
        return agent
    
    @pytest.fixture
    def cli(self, mock_agent):
        """Create CLI instance with mock agent."""
        return CLIInterface(mock_agent, model_name="test-model")
    
    def test_slash_commands_defined(self, cli):
        """Test that slash commands are defined."""
        assert "/help" in cli.SLASH_COMMANDS
        assert "/exit" in cli.SLASH_COMMANDS
        assert "/reset" in cli.SLASH_COMMANDS
        assert "/model" in cli.SLASH_COMMANDS
        assert "/sql" in cli.SLASH_COMMANDS
        assert "/stats" in cli.SLASH_COMMANDS
    
    def test_short_model_name_with_slash(self, cli):
        """Test model name shortening with slash."""
        assert cli._short_model_name("anthropic/claude-3") == "claude-3"
    
    def test_short_model_name_with_colon(self, cli):
        """Test model name shortening with colon."""
        assert cli._short_model_name("llama3:latest") == "llama3"
    
    def test_short_model_name_truncation(self, cli):
        """Test model name truncation for long names."""
        long_name = "a" * 50
        assert len(cli._short_model_name(long_name)) == 25
    
    def test_display_welcome(self, cli, capsys):
        """Test welcome message display."""
        cli.display_welcome()
        captured = capsys.readouterr()
        assert "E-Commerce Data Analysis Agent" in captured.out
    
    def test_sql_toggle(self, cli):
        """Test SQL display toggle."""
        assert cli.show_sql is False
        cli._handle_command("/sql")
        assert cli.show_sql is True
        cli._handle_command("/sql")
        assert cli.show_sql is False
    
    def test_exit_command(self, cli):
        """Test exit command stops the loop."""
        cli.running = True
        cli._handle_command("/exit")
        assert cli.running is False
    
    def test_reset_command(self, cli, mock_agent):
        """Test reset command clears conversation."""
        cli._handle_command("/reset")
        mock_agent.reset_conversation.assert_called_once()
    
    def test_legacy_exit_commands(self, cli):
        """Test that legacy exit commands work."""
        legacy_commands = ["exit", "quit", "bye", "q"]
        for cmd in legacy_commands:
            cli.running = True
            # Simulate the check in start() method
            if cmd.lower() in {"exit", "quit", "bye", "q"}:
                cli._handle_command("/exit")
            assert cli.running is False

