import sys
from typing import Optional

# ANSI color codes for terminal output
COLORS = {
    "header": "\033[1;36m",  # Bold cyan
    "success": "\033[32m",   # Green
    "warning": "\033[33m",   # Yellow
    "error": "\033[31m",     # Red
    "info": "\033[34m",      # Blue
    "reset": "\033[0m",      # Reset
    "bold": "\033[1m",       # Bold
    "dim": "\033[2m",        # Dim
}

# Global verbose flag
_verbose_enabled = False


def set_verbose(enabled: bool):
    """Enable or disable verbose output globally."""
    global _verbose_enabled
    _verbose_enabled = enabled


def is_verbose() -> bool:
    """Check if verbose mode is enabled."""
    return _verbose_enabled


def _supports_color() -> bool:
    """Check if terminal supports color."""
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def _colorize(text: str, color: str) -> str:
    """Apply color to text if supported."""
    if _supports_color() and color in COLORS:
        return f"{COLORS[color]}{text}{COLORS['reset']}"
    return text


def print_header(node_name: str):
    """Print a node header."""
    if not _verbose_enabled:
        return
    line = "━" * 50
    print(f"\n{_colorize(line, 'header')}")
    print(f"{_colorize(f'  {node_name.upper()}', 'header')}")
    print(f"{_colorize(line, 'header')}")


def print_decision(decision: str, details: Optional[str] = None):
    """Print a routing/classification decision."""
    if not _verbose_enabled:
        return
    print(f"{_colorize('→', 'info')} Decision: {_colorize(decision, 'bold')}")
    if details:
        print(f"  {_colorize(details, 'dim')}")


def print_step(message: str):
    """Print a processing step."""
    if not _verbose_enabled:
        return
    print(f"{_colorize('•', 'info')} {message}")


def print_success(message: str):
    """Print a success message."""
    if not _verbose_enabled:
        return
    print(f"{_colorize('✓', 'success')} {message}")


def print_warning(message: str):
    """Print a warning message."""
    if not _verbose_enabled:
        return
    print(f"{_colorize('⚠', 'warning')} {message}")


def print_error(message: str):
    """Print an error message."""
    if not _verbose_enabled:
        return
    print(f"{_colorize('✗', 'error')} {message}")


def print_sql(sql: str):
    """Print SQL query in a formatted box."""
    if not _verbose_enabled:
        return
    print(f"\n{_colorize('SQL Query:', 'bold')}")
    print(f"{_colorize('```sql', 'dim')}")
    # Indent SQL for readability
    for line in sql.strip().split('\n'):
        print(f"  {line}")
    print(f"{_colorize('```', 'dim')}")


def print_results_summary(row_count: int, columns: list):
    """Print a summary of query results."""
    if not _verbose_enabled:
        return
    print(f"{_colorize('✓', 'success')} Results: {row_count} rows, {len(columns)} columns")
    if columns:
        cols_preview = ", ".join(columns[:5])
        if len(columns) > 5:
            cols_preview += f" (+{len(columns) - 5} more)"
        print(f"  {_colorize('Columns:', 'dim')} {cols_preview}")


def print_retry(attempt: int, max_attempts: int, reason: str):
    """Print retry information."""
    if not _verbose_enabled:
        return
    print(f"{_colorize('↻', 'warning')} Retry {attempt}/{max_attempts}: {reason}")


def print_fallback(from_model: str, to_model: str):
    """Print model fallback information."""
    if not _verbose_enabled:
        return
    print(f"{_colorize('↪', 'warning')} Fallback: {from_model} → {to_model}")
