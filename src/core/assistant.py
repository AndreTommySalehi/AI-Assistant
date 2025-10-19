"""
Main Jarvis Assistant class
"""

from datetime import datetime
from .llm import LLMHandler
from .search import WebSearch


class JarvisAssistant:
    """Main assistant class that coordinates search and LLM"""
    
    def __init__(self, model_name=None):
        print("Initializing Jarvis Assistant...")
        
        # Initialize LLM
        self.llm = LLMHandler(model_name)
        
        # Initialize web search
        try:
            self.search = WebSearch()
        except Exception as e:
            print(f"Warning: Search functionality unavailable - {e}")
            self.search = None
        
        print("Jarvis Assistant ready\n")
    
    def chat(self, user_input):
        """Process user input and return a response"""
        try:
            # Check if we need to search the web
            if self.search and self.search.needs_search(user_input):
                return self._handle_search_query(user_input)
            else:
                return self._handle_general_query(user_input)
            
        except Exception as e:
            return f"Error: {str(e)}\n\nPlease try rephrasing your question."
    
    def _handle_search_query(self, user_input):
        """Handle queries that require web search"""
        print("Searching the web for current information...")
        
        search_results = self.search.search(user_input)
        
        # Handle search failures
        if "error" in search_results.lower() or "unavailable" in search_results.lower():
            print("Search issue detected, using model knowledge")
            return self.llm.generate(user_input)
        
        if "no search results" in search_results.lower():
            print("No results found, using model knowledge")
            return self.llm.generate(user_input)
        
        # Create prompt with search results
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = f"""Current Date: {current_date}

User's Question: {user_input}

===== CURRENT WEB SEARCH RESULTS =====
{search_results}
===== END SEARCH RESULTS =====

INSTRUCTIONS:
You MUST answer the user's question using the search results above. These are CURRENT, REAL results from the web.

- Extract specific information (temperatures, dates, names, facts) from the results
- Synthesize a clear, direct answer
- Mention which result number you're referencing
- DO NOT refuse to answer - the information is provided above

Provide your answer now:"""
        
        print("Processing search results...")
        return self.llm.generate(prompt, use_search_context=True)
    
    def _handle_general_query(self, user_input):
        """Handle general queries without search"""
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = f"Today's date is {current_date}. {user_input}"
        return self.llm.generate(prompt)