import sys
import logging

logger = logging.getLogger(__name__)

# Exit commands (case-insensitive)
EXIT_COMMANDS = {"exit", "quit", "bye", "q"}

WELCOME_MESSAGE = """
╔══════════════════════════════════════════════════════════════════╗
║           E-Commerce Data Analysis Agent                         ║
╠══════════════════════════════════════════════════════════════════╣
║  I can help you analyze e-commerce data from BigQuery.           ║
║                                                                  ║
║  You can ask me about:                                           ║
║  • Customer segmentation and behavior                            ║
║  • Product performance and recommendations                       ║
║  • Sales trends and seasonality                                  ║
║  • Geographic sales patterns                                     ║
║  • Database structure and schemas                                ║
║                                                                  ║
║  Type 'exit', 'quit', 'bye', or 'q' to end the session.         ║
╚══════════════════════════════════════════════════════════════════╝
"""

FAREWELL_MESSAGE = """
Thank you for using the Data Analysis Agent. Goodbye!
"""


class CLIInterface:
    """Handles user input/output through command line."""
    
    def __init__(self, agent, show_sql: bool = False):
        """Initialize CLI interface.
        
        Args:
            agent: DataAnalysisAgent instance
            show_sql: Whether to display SQL queries in output
        """
        self.agent = agent
        self.show_sql = show_sql
        self.running = False
    
    def start(self, initial_query: str = None) -> None:
        """Start the CLI chat loop.
        
        Args:
            initial_query: Optional query to run immediately on start
        """
        self.running = True
        self.display_welcome()
        
        # Process initial query if provided
        if initial_query:
            print(f"You: {initial_query}\n")
            self._process_query(initial_query)
        
        while self.running:
            try:
                user_input = self.get_user_input()
                
                if not user_input:
                    continue
                
                if self.is_exit_command(user_input):
                    self.display_farewell()
                    break
                
                if self.is_empty_input(user_input):
                    print("\nPlease enter a valid query.\n")
                    continue
                
                self._process_query(user_input)
                
            except KeyboardInterrupt:
                print("\n")
                self.display_farewell()
                break
            except Exception as e:
                logger.error(f"Error in CLI loop: {e}")
                self.display_error(str(e))
    
    def _process_query(self, user_input: str) -> None:
        """Process a single query and display response.
        
        Args:
            user_input: User's query string
        """
        print("\nThinking...\n")
        response, sql = self.agent.invoke(user_input, return_sql=True)
        
        if self.show_sql and sql:
            self.display_sql(sql)
        
        self.display_response(response)
    
    def display_welcome(self) -> None:
        """Display welcome message and instructions."""
        print(WELCOME_MESSAGE)
    
    def display_farewell(self) -> None:
        """Display farewell message."""
        print(FAREWELL_MESSAGE)
        self.running = False
    
    def get_user_input(self) -> str:
        """Get input from user.
        
        Returns:
            User input string
        """
        try:
            return input("You: ").strip()
        except EOFError:
            return "exit"
    
    def display_sql(self, sql: str) -> None:
        """Display SQL query.
        
        Args:
            sql: SQL query string
        """
        print(f"📊 SQL Query:\n```sql\n{sql}\n```\n")
    
    def display_response(self, response: str) -> None:
        """Display agent response to user.
        
        Args:
            response: Agent's response string
        """
        print(f"Agent: {response}\n")
        print("-" * 60)
    
    def display_error(self, error: str) -> None:
        """Display error message to user.
        
        Args:
            error: Error message
        """
        print(f"\n[Error] Something went wrong. Please try again.\n")
        logger.error(f"Displayed error to user: {error}")
    
    @staticmethod
    def is_exit_command(user_input: str) -> bool:
        """Check if user wants to exit.
        
        Args:
            user_input: User's input string
            
        Returns:
            True if exit command, False otherwise
        """
        return user_input.lower().strip() in EXIT_COMMANDS
    
    @staticmethod
    def is_empty_input(user_input: str) -> bool:
        """Check if input is empty or whitespace only.
        
        Args:
            user_input: User's input string
            
        Returns:
            True if empty/whitespace, False otherwise
        """
        return not user_input or not user_input.strip()
