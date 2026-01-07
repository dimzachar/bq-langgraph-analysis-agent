import sys
import argparse
import logging
import warnings
from dotenv import load_dotenv

# Suppress harmless warnings
warnings.filterwarnings("ignore", message="No project ID could be determined")
warnings.filterwarnings("ignore", message="BigQuery Storage module not found")

from src.config import load_config
from src.llm_client import LLMClient
from src.bq_client import BigQueryRunner
from src.schema_cache import SchemaCache
from src.agent import DataAnalysisAgent
from src.cli import CLIInterface
from src.verbose import set_verbose

VERSION = "1.0.0"

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog='ecommerce-agent',
        description='AI-powered e-commerce data analysis agent',
        epilog='Example: %(prog)s "What are the top products?"'
    )
    
    # Positional argument for initial query
    parser.add_argument('query', nargs='?', help='Initial query (required for print mode)')
    
    # Mode flags
    parser.add_argument('-p', '--print', action='store_true', dest='print_mode',
                       help='Non-interactive mode: run query and exit')
    
    # Output options
    parser.add_argument('--show-sql', action='store_true',
                       help='Display SQL queries in output')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show agent decisions and flow')
    parser.add_argument('--debug', action='store_true',
                       help='Enable full debug logging (very verbose)')
    
    # Version
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    
    args = parser.parse_args()
    
    # Validation
    if args.print_mode and not args.query:
        parser.error("query required in print mode (-p)")
    
    return args


def setup_logging(debug: bool = False):
    """Configure logging based on debug flag.
    
    Args:
        debug: If True, enable DEBUG level logging to stdout
    """
    # Set level based on debug flag
    level = logging.DEBUG if debug else logging.INFO
    
    # Always log to file
    handlers = [logging.FileHandler('agent.log')]
    
    # Add stdout handler only in debug mode
    if debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Suppress noisy third-party loggers unless in debug mode
    if not debug:
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('openai').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('google').setLevel(logging.WARNING)


def initialize_agent(config):
    """Initialize all components and return agent."""
    # Initialize LLM client with optional fallback
    llm_client = LLMClient(
        provider=config.llm_provider,
        model_name=config.get_model_name(),
        api_key=config.get_api_key(),
        openrouter_base_url=config.openrouter_base_url,
        fallback_model=config.fallback_model
    )
    logger.info("LLM client initialized")
    if config.fallback_model:
        logger.info(f"Fallback model configured: {config.fallback_model}")
    
    # Initialize BigQuery client
    bq_client = BigQueryRunner(
        project_id=config.google_cloud_project,
        dataset_id=config.bigquery_dataset
    )
    logger.info("BigQuery client initialized")
    
    # Validate BigQuery connectivity
    print("Validating BigQuery connection...")
    bq_client.validate_connection()
    print("BigQuery connection validated successfully!")
    
    # Initialize schema cache
    schema_cache = SchemaCache(bq_client)
    print("Loading database schemas...")
    schema_cache.load_all_schemas()
    print("Schemas loaded successfully!")
    
    # Initialize agent
    agent = DataAnalysisAgent(
        llm_client=llm_client,
        bq_client=bq_client,
        schema_cache=schema_cache,
        max_retries=config.max_query_retries
    )
    logger.info("Agent initialized")
    
    return agent


def run_print_mode(agent, query: str, show_sql: bool = False):
    """Run single query and exit (non-interactive mode)."""
    response, sql = agent.invoke(query, return_sql=True)
    
    if show_sql and sql:
        print(f"\n📊 SQL Query:\n```sql\n{sql}\n```\n")
    
    print(response)


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()
    
    # Parse arguments
    args = parse_args()
    
    # Setup logging and verbose mode
    setup_logging(debug=args.debug)
    set_verbose(args.verbose)
    
    print("Initializing Data Analysis Agent...")
    
    try:
        # Load configuration
        config = load_config()
        logger.info(f"Configuration loaded. Provider: {config.llm_provider}")
        
        # Initialize agent
        agent = initialize_agent(config)
        
        if args.print_mode:
            # Non-interactive mode
            run_print_mode(agent, args.query, show_sql=args.show_sql)
        else:
            # Interactive mode
            cli = CLIInterface(agent, show_sql=args.show_sql)
            if args.query:
                # Start with initial query
                cli.start(initial_query=args.query)
            else:
                cli.start()
        
    except ValueError as e:
        print(f"\nConfiguration Error: {e}")
        print("\nPlease ensure you have set up your environment variables correctly.")
        print("Copy .env.example to .env and fill in your API keys.")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        print(f"\nError: {e}")
        print("\nPlease check your configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
