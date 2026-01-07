import sys
import logging
import shutil
import time

logger = logging.getLogger(__name__)

# ANSI codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"


def supports_color() -> bool:
    """Check if terminal supports color."""
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def c(text: str, *codes: str) -> str:
    """Apply color codes if supported."""
    if not supports_color():
        return text
    return f"{''.join(codes)}{text}{RESET}"


class CLIInterface:
    """Modern CLI interface with status bar and slash commands."""
    
    SLASH_COMMANDS = {
        "/help": "Show available commands",
        "/model": "Switch model (/model <name>)",
        "/reset": "Clear conversation history", 
        "/stats": "Show session statistics",
        "/sql": "Toggle SQL display",
        "/exit": "Exit the application",
    }
    
    def __init__(self, agent, show_sql: bool = False, model_name: str = "unknown", suggested_models: list = None):
        self.agent = agent
        self.show_sql = show_sql
        self.default_model = model_name  # Store original model from config
        self.model_name = self._short_model_name(model_name)
        self.suggested_models = suggested_models or []
        self.running = False
        self.term_width = shutil.get_terminal_size().columns
    
    def _short_model_name(self, name: str) -> str:
        """Shorten model name for display."""
        if "/" in name:
            name = name.split("/")[-1]
        if ":" in name:
            name = name.split(":")[0]
        return name[:25]

    def _status_bar(self) -> str:
        """Generate status bar with model and context info."""
        stats = self.agent.get_session_stats()
        ctx = stats["context_messages"]
        tokens = stats["total_tokens"]
        max_ctx = self.agent.max_messages
        
        # Context progress bar
        bar_width = 10
        filled = min(int((ctx / max_ctx) * bar_width), bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Color based on usage
        if ctx > max_ctx * 0.8:
            bar_color = YELLOW
        elif ctx > max_ctx * 0.5:
            bar_color = CYAN
        else:
            bar_color = GREEN
        
        model_str = c(f"⚡ {self.model_name}", DIM)
        ctx_str = c(f"ctx [{bar}] {ctx}/{max_ctx}", bar_color)
        tokens_str = c(f"~{tokens:,} tokens", DIM)
        sql_str = c("SQL:ON", GREEN) if self.show_sql else c("SQL:OFF", DIM)
        
        return f"{model_str}  {ctx_str}  {tokens_str}  {sql_str}"
    
    def _print_status(self):
        """Print the status bar."""
        print(f"\n{self._status_bar()}")
    
    def _input_prompt(self) -> str:
        """Get styled input prompt."""
        return c("› ", CYAN, BOLD)
    
    def display_welcome(self):
        """Display welcome message."""
        w = min(self.term_width, 70)
        line = "─" * w
        
        print(f"\n{c(line, DIM)}")
        print(c("  E-Commerce Data Analysis Agent", BOLD, CYAN))
        print(c(line, DIM))
        print(f"\n  Ask questions about customers, products, sales, and trends.\n")
        print(f"  {c('Commands:', BOLD)}")
        for cmd, desc in self.SLASH_COMMANDS.items():
            print(f"    {c(cmd, CYAN):12} {desc}")
        print()
        print(c(line, DIM))

    def start(self, initial_query: str = None):
        """Start the CLI chat loop."""
        self.running = True
        self.display_welcome()
        
        if initial_query:
            print(f"{self._input_prompt()}{initial_query}")
            self._process_query(initial_query)
        
        while self.running:
            try:
                self._print_status()
                user_input = input(self._input_prompt()).strip()
                
                if not user_input:
                    continue
                
                # Handle slash commands
                if user_input.startswith("/"):
                    self._handle_command(user_input.lower())
                    continue
                
                # Legacy commands (without slash)
                if user_input.lower() in {"exit", "quit", "bye", "q"}:
                    self._handle_command("/exit")
                    continue
                
                self._process_query(user_input)
                
            except KeyboardInterrupt:
                print(f"\n{c('Interrupted', YELLOW)}")
                self._handle_command("/exit")
            except EOFError:
                self._handle_command("/exit")
            except Exception as e:
                logger.error(f"CLI error: {e}")
                print(f"\n{c('Error:', YELLOW)} {e}\n")
    
    def _handle_command(self, cmd_input: str):
        """Handle slash commands."""
        parts = cmd_input.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else None
        
        if cmd == "/exit":
            print(f"\n{c('Goodbye!', DIM)}\n")
            self.running = False
            
        elif cmd == "/reset":
            self.agent.reset_conversation()
            print(f"\n{c('✓', GREEN)} Conversation cleared\n")
            
        elif cmd == "/sql":
            self.show_sql = not self.show_sql
            state = c("ON", GREEN) if self.show_sql else c("OFF", DIM)
            print(f"\n{c('✓', GREEN)} SQL display: {state}\n")
            
        elif cmd == "/model":
            self._handle_model_command(args)
            
        elif cmd == "/stats":
            self._display_stats()
            
        elif cmd == "/help":
            self._display_help()
            
        else:
            print(f"\n{c('Unknown command:', YELLOW)} {cmd}")
            print(f"Type {c('/help', CYAN)} for available commands\n")
    
    def _handle_model_command(self, model_arg: str = None):
        """Handle /model command."""
        if not model_arg:
            # Show current model and suggestions
            default_short = self._short_model_name(self.default_model)
            print(f"\n{c('Current model:', BOLD)} {c(self.model_name, CYAN)}")
            print(f"{c('Default model:', DIM)} {default_short}")
            if self.suggested_models:
                print(f"\n{c('Suggested models:', BOLD)}")
                for i, model in enumerate(self.suggested_models, 1):
                    print(f"  {c(str(i), DIM)}. {c(model, CYAN)}")
            print(f"\n{c('Usage:', DIM)} /model <name, number, or \"default\">")
            print(f"{c('Example:', DIM)} /model 1  or  /model default\n")
            return
        
        # Handle "default" to reset to original model
        if model_arg == "default":
            model_arg = self.default_model
        # Check if it's a number (shortcut)
        elif model_arg.isdigit() and self.suggested_models:
            idx = int(model_arg) - 1
            if 0 <= idx < len(self.suggested_models):
                model_arg = self.suggested_models[idx]
            else:
                print(f"\n{c('Invalid number:', YELLOW)} Choose 1-{len(self.suggested_models)}\n")
                return
        
        # Switch model
        try:
            new_model = self.agent.switch_model(model_arg)
            self.model_name = self._short_model_name(new_model)
            print(f"\n{c('✓', GREEN)} Switched to: {c(self.model_name, CYAN)}\n")
        except Exception as e:
            print(f"\n{c('Failed to switch model:', YELLOW)} {e}\n")

    def _process_query(self, query: str):
        """Process a user query."""
        print(f"\n{c('Thinking...', DIM)}", end="", flush=True)
        start = time.time()
        
        response, sql = self.agent.invoke(query, return_sql=True)
        elapsed = time.time() - start
        
        # Clear "Thinking..." and show time
        print(f"\r{c(f'({elapsed:.1f}s)', DIM)}          \n")
        
        # Show SQL if enabled
        if self.show_sql and sql:
            print(c("SQL:", BOLD))
            print(c("```sql", DIM))
            for line in sql.strip().split('\n'):
                print(f"  {c(line, CYAN)}")
            print(c("```", DIM))
            print()
        
        # Show response
        print(f"{response}\n")
        print(c("─" * min(self.term_width, 70), DIM))
    
    def _display_stats(self):
        """Display session statistics."""
        stats = self.agent.get_session_stats()
        total_tokens = stats['total_tokens']
        total_time = stats['total_time']
        ctx_msgs = stats['context_messages']
        
        print(f"\n{c('Session Statistics', BOLD)}")
        print(c("─" * 30, DIM))
        print(f"  Queries:     {c(str(stats['total_queries']), CYAN)}")
        print(f"  Tokens:      {c(f'~{total_tokens:,}', CYAN)}")
        print(f"  LLM Calls:   {c(str(stats['total_llm_calls']), CYAN)}")
        print(f"  Total Time:  {c(f'{total_time:.1f}s', CYAN)}")
        print(f"  Context:     {c(f'{ctx_msgs} messages', CYAN)}")
        print()
    
    def _display_help(self):
        """Display help for slash commands."""
        print(f"\n{c('Available Commands', BOLD)}")
        print(c("─" * 30, DIM))
        for cmd, desc in self.SLASH_COMMANDS.items():
            print(f"  {c(cmd, CYAN):12} {desc}")
        print()
