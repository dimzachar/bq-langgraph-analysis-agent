# Data Analysis Agent

A CLI-based conversational AI agent for analyzing e-commerce data from Google BigQuery's public dataset using LangGraph and Google Gemini.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Interface                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LangGraph Agent                              │
│  ┌─────────┐  ┌─────────┐  ┌───────────┐  ┌──────────┐         │
│  │ Router  │→ │ Planner │→ │SQL Gen    │→ │ Executor │         │
│  └─────────┘  └─────────┘  └───────────┘  └──────────┘         │
│       │                                         │               │
│       │            ┌──────────┐  ┌───────────┐  │               │
│       └──────────→ │ Analyzer │→ │ Responder │←─┘               │
│                    └──────────┘  └───────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌───────────┐   ┌─────────────┐
        │   LLM    │   │ BigQuery  │   │Schema Cache │
        │(Gemini)  │   │  Client   │   │             │
        └──────────┘   └───────────┘   └─────────────┘
```

## Features

- **Natural Language Queries**: Ask questions about e-commerce data in plain English
- **Dynamic SQL Generation**: Automatically constructs BigQuery SQL from your questions
- **Multiple Analysis Types**:
  - Customer segmentation and behavior
  - Product performance analysis
  - Sales trends and seasonality
  - Geographic patterns
  - Database schema exploration
- **Error Recovery**: Automatic SQL correction and retry on failures
- **Dual LLM Support**: Google Gemini (default) or OpenRouter

## Setup

### 1. Install Dependencies

Using `uv` (recommended):

```bash
# Install uv if not already installed
# See: https://docs.astral.sh/uv/getting-started/installation/

# Create virtual environment and install dependencies
uv venv .venv
uv sync --extra dev  # installs all deps including test tools

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

# Full debug logging (HTTP requests, etc. - for troubleshooting)
python -m src.main --debug "What are the top 10 products?"

# Show generated SQL queries
python -m src.main --show-sql "What are the top 10 products?"
```

**Verbose output example:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ROUTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Classifying: "What are the top 10 products?"
→ Decision: analysis
  Will generate SQL and analyze data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SQL GENERATOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Generating SQL from natural language...
SQL Query:
  SELECT p.name, COUNT(*) as order_count
  FROM `bigquery-public-data.thelook_ecommerce.order_items` oi
  JOIN `bigquery-public-data.thelook_ecommerce.products` p
  ON oi.product_id = p.id
  GROUP BY p.name
  ORDER BY order_count DESC
  LIMIT 10
✓ SQL generated successfully
```

### Query Examples

```
You: What are the top 5 product categories by revenue?

Agent: Based on the analysis, here are the top 5 product categories by revenue:
1. Outerwear & Coats - $2.3M
2. Jeans - $1.8M
...

You: Show me customer distribution by country

You: What tables are in the database?
```

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
│   ├── schema_cache.py   # Schema caching
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

## Technology Stack

- **Agent Framework**: LangGraph v1
- **LLM**: Google Gemini 1.5 Flash (or OpenRouter)
- **Data Warehouse**: Google BigQuery
- **Testing**: Hypothesis (property-based) + pytest
- **Configuration**: pydantic-settings + python-dotenv

## Security

The agent only talks to the e-commerce dataset and won't try to run anything dangerous. It checks every SQL query before execution, if someone tries to sneak in a `DROP TABLE` or access tables outside the allowed list (`orders`, `order_items`, `products`, `users`), it gets blocked. Prompt injection attempts are ignored.

## Hallucination Prevention

The agent uses several strategies to prevent LLM hallucination in responses:

- Actual Data Injection: The Responder node passes the exact query results to the LLM, not just summaries. This ensures the LLM has access to real values.

- Explicit Instructions: The prompt includes "Use the EXACT values from the data above. Do not make up or approximate numbers."

- SQL Retry with Fix: When SQL fails, the Executor asks the LLM to fix the query based on the actual error message, then retries (up to 2 attempts).

- Model Fallback: If the primary LLM fails (rate limits, errors), automatically falls back to a secondary model.


## Future Possible Improvements

- `init_chat_model`: Simplify LLM setup in `llm_client.py` with one function instead of separate provider classes
- `Runtime` context: Let users switch models mid-session without restarting the CLI
- `InMemorySaver` checkpointer: could add short-term memory (RAM, resets on restart) for thread IDs and checkpointing. Long term (persistence across restarts, session stored) not needed-adds more complexity for this case
- Self-reflection: Add a node that validates response accuracy