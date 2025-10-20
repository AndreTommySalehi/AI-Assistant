"""
Main Jarvis Assistant class
"""

from datetime import datetime
from .llm import LLMHandler
from .search import WebSearch


class JarvisAssistant:
    """Main assistant class that coordinates search and LLM"""
    
    def __init__(self, model_name=None):
        # Initialize LLM
        self.llm = LLMHandler(model_name)
        
        # Initialize web search
        try:
            self.search = WebSearch()
        except Exception as e:
            self.search = None
    
    def chat(self, user_input):
        """Process user input and return a response"""
        try:
            # Check if we need to search the web
            if self.search and self.search.needs_search(user_input):
                return self._handle_search_query(user_input)
            else:
                return self._handle_general_query(user_input)
            
        except Exception as e:
            return f"I encountered an error. Could you try rephrasing your question?"
    
    def _handle_search_query(self, user_input):
        """Handle queries that require web search"""
        search_results = self.search.search(user_input)
        
        # Handle search failures - silently fall back to model knowledge
        if "error" in search_results.lower() or "unavailable" in search_results.lower():
            return self.llm.generate(user_input)
        
        if "no search results" in search_results.lower():
            return self.llm.generate(user_input)
        
        # Create prompt with search results
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = f"""Current Date: {current_date}

User's Question: {user_input}

===== CURRENT WEB SEARCH RESULTS =====
{search_results}
===== END SEARCH RESULTS =====

INSTRUCTIONS:
1. Analyze ALL search results above carefully
2. Count how many sources support each answer
3. If 75%+ of sources agree (4+ out of 5-7 sources):
   - Give a CONFIDENT, DIRECT answer
   - State the facts naturally
   - DO NOT mention source counts or percentages
4. If sources are split (less than 75% agreement):
   - Start with: "Results are inconclusive, but here's what I found:"
   - Present the different answers clearly
   - Example: "Some sources say 75°F and sunny, while others report 72°F with clouds."
5. Extract specific data: temperatures, dates, numbers, names
6. Be conversational and natural - NO meta-commentary about sources

RESPONSE STYLE:
âœ" GOOD: "It's currently 75°F and sunny in Los Angeles."
âœ— BAD: "Based on Results 1, 2, 3..." or "(4/5 sources agree...)"

Keep it clean and natural!

Provide your answer now:"""
        
        return self.llm.generate(prompt, use_search_context=True)
    
    def _handle_general_query(self, user_input):
        """Handle general queries without search"""
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = f"Today's date is {current_date}. {user_input}"
        return self.llm.generate(prompt)