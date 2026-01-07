# Data Analysis Agent

A CLI-based AI agent for analyzing e-commerce data from Google BigQuery's public dataset using LangGraph and LLMs.

## Features

- **Natural Language Queries**: Ask questions about e-commerce data
- **Dynamic SQL Generation**: Automatically constructs BigQuery SQL from your questions
- **Multiple Analysis Types**:
  - Customer segmentation and behavior
  - Product performance analysis
  - Sales trends and seasonality
  - Geographic patterns
  - Database schema exploration
- **Conversation Memory**: Maintains context across follow-up questions (max 100 messages, auto-trimmed)
- **Error Recovery**: Automatic SQL correction and retry on failures with exponential backoff
- **Dual LLM Support**: Google Gemini or OpenRouter (select provider)

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture documentation.


## Setup

### 1. Install Dependencies

Using `uv` (recommended):

```bash
# Install uv if not already installed
# See: https://docs.astral.sh/uv/getting-started/installation/

# Windows (PowerShell):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH , Restart terminal/ide after installation

# Create virtual environment and install dependencies
uv venv .venv
uv sync              # core dependencies only (to run the agent)
# OR
uv sync --extra dev  # includes test tools (pytest, coverage, hypothesis)

# Activate the virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

Or using pip:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -e ".[dev]"
```

### 2. Configure Google Cloud

See [docs/GOOGLE_CLOUD_SETUP.md](docs/GOOGLE_CLOUD_SETUP.md) for detailed setup instructions.

Quick start:
```bash
# Install gcloud CLI, then:
gcloud init
gcloud auth application-default login
```

### 3. Configure Environment Variables

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# LLM Provider: "gemini" or "openrouter"
LLM_PROVIDER=gemini

# Google Gemini (get key from https://aistudio.google.com/apikey)
GOOGLE_API_KEY=your_api_key_here

# GCP Project ID (required for BigQuery)
GOOGLE_CLOUD_PROJECT=your_project_id
```

### 4. Run the Agent

```bash
python -m src.main
```

## Usage Examples

### Basic Usage

```bash
# Interactive mode
python -m src.main

# With initial query
python -m src.main "What are the top 10 products by revenue?"

# Non-interactive (print and exit)
python -m src.main -p "What are the top 10 products?"
```

### Verbose & Debug Modes

```bash
# Show agent decision flow (recommended for understanding the pipeline)
python -m src.main --verbose "What are the top 10 products?"

# Full debug logging
python -m src.main --debug "What are the top 10 products?"

# Show generated SQL queries
python -m src.main --show-sql "What are the top 10 products?"
```

### CLI Commands

Use slash commands:

- `/help` - Show available commands
- `/model <name>` - Switch LLM model at runtime
- `/reset` - Clear conversation history
- `/stats` - Show session statistics (tokens, queries, time)
- `/sql` - Toggle SQL query display
- `/exit` - Exit the application

### Example Run

See [example.md](example.md) for a full session transcript.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run property tests only
pytest tests/property/

# Run specific test file
pytest tests/property/test_cli.py -v
```

## Project Structure

```
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── cli.py            # CLI interface
│   ├── config.py         # Configuration
│   ├── agent.py          # LangGraph agent
│   ├── state.py          # Agent state
│   ├── schema_cache.py   # Schema caching (loads all table schemas at startup in parallel, provides formatted schema context to LLM nodes)
│   ├── llm_client.py     # LLM wrapper
│   ├── bq_client.py      # BigQuery client
│   └── nodes/
│       ├── router.py     # Query classification
│       ├── planner.py    # Execution planning
│       ├── sql_generator.py
│       ├── executor.py   # Query execution
│       ├── analyzer.py   # Result analysis
│       └── responder.py  # Response generation
├── tests/
│   ├── unit/
│   ├── property/
│   └── integration/
├── pyproject.toml
├── .env.example
└── README.md
```

## Technnology Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Agent Framework | LangGraph v1 | Explicit graph-based control flow. Simpler deterministic paths per query type instead of hybrid workflow + loop architecture. Easier to debug/test, and testing showed it handles most queries well. |
| LLM | Gemini and Openrouter providers | Free tier, 1M token context (fits full schema + history), same GCP ecosystem as BigQuery. OpenRouter supported too. |
| Data Warehouse | BigQuery | the `thelook_ecommerce` dataset lives there. |
| Package Manager | uv | Fast dependency resolution, reproducible builds via `uv.lock`. |


## Security

The agent only talks to the e-commerce dataset and won't try to run anything dangerous. It checks every SQL query before execution, if someone tries to sneak in a `DROP TABLE` or access tables outside the allowed list (`orders`, `order_items`, `products`, `users`), it gets blocked. Prompt injection attempts were ignored when tested.

## Error Handling & Reliability

- SQL Retry with Fix: When SQL fails, the Executor asks the LLM to fix the query based on the actual error message, then retries (up to 2 attempts).

- Exponential Backoff: LLM calls use exponential backoff for rate limit handling (starts at 1s, doubles up to 30s max, 3 retries).

- Model Fallback: If the primary LLM fails (rate limits, errors), automatically falls back to a secondary model.

## Hallucination Prevention

The agent uses several strategies to prevent LLM hallucination in responses:

- Actual Data Injection: The Responder node passes the exact query results to the LLM, not just summaries. This ensures the LLM has access to real values.

- Explicit Instructions: The prompt includes "Use the EXACT values from the data above. Do not make up or approximate numbers."

- Post-validation: The Responder checks numbers in the generated response against actual query results and logs warnings if potential hallucinations are detected.


## Future Possible Improvements

- `init_chat_model`: Simplify LLM setup in `llm_client.py` with one function instead of separate provider classes
- `InMemorySaver` checkpointer: could add short-term memory (RAM, resets on restart) for thread IDs and checkpointing. Long term (persistence across restarts, session stored) not needed-adds more complexity for this case
- Self-reflection: Add a node that validates response accuracy
- Merge/combine nodes to reduce LLM calls and make it faster
- Add streaming responses to 'feel' faster
- For production scenarios requiring higher reliability, a two-layer hybrid architecture (workflow + agent loop) could improve handling of edge cases: on-demand schema discovery via tool calls (vs pre-loaded schema in prompts), flexible iteration without fixed retry limits, better multi-step query chaining where step 2 depends on step 1's result, orchestrator with parallel worker dispatch for multi-insight reports
