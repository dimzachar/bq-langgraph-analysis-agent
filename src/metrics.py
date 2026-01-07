"""Metrics tracking for agent execution."""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueryMetrics:
    """Metrics for a single query execution."""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Token estimates (chars / 4 as rough approximation)
    prompt_tokens: int = 0
    response_tokens: int = 0
    
    # Execution details
    llm_calls: int = 0
    bq_execution_time: Optional[float] = None
    rows_returned: int = 0
    
    @property
    def total_time(self) -> float:
        """Total execution time in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def total_tokens(self) -> int:
        """Estimated total tokens used."""
        return self.prompt_tokens + self.response_tokens
    
    def finish(self):
        """Mark query as complete."""
        self.end_time = time.time()


@dataclass 
class SessionMetrics:
    """Cumulative metrics for an agent session."""
    total_queries: int = 0
    total_tokens: int = 0
    total_llm_calls: int = 0
    total_time: float = 0.0
    context_messages: int = 0
    
    # Limits for warnings
    max_context_messages: int = 50
    token_warning_threshold: int = 100000
    
    def update(self, query_metrics: QueryMetrics, message_count: int):
        """Update session metrics after a query."""
        self.total_queries += 1
        self.total_tokens += query_metrics.total_tokens
        self.total_llm_calls += query_metrics.llm_calls
        self.total_time += query_metrics.total_time
        self.context_messages = message_count
    
    @property
    def context_warning(self) -> bool:
        """Check if context is getting large."""
        return self.context_messages > self.max_context_messages
    
    @property
    def token_warning(self) -> bool:
        """Check if token usage is high."""
        return self.total_tokens > self.token_warning_threshold


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars / 4)."""
    return len(text) // 4
