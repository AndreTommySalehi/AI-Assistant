"""
Main Jarvis Assistant class with conversation memory
"""

from datetime import datetime
import re
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
        
        # Conversation memory
        self.conversation_history = []
        self.max_history = 10  # Keep last 10 messages
    
    def chat(self, user_input):
        """Process user input and return a response"""
        try:
            # Add user message to history
            self.conversation_history.append({
                'role': 'user',
                'content': user_input
            })
            
            # Check if we need to search the web
            if self.search and self.search.needs_search(user_input):
                response = self._handle_search_query(user_input)
            else:
                response = self._handle_general_query(user_input)
            
            # Add assistant response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            # Trim history if too long
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            return response
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"\n[DEBUG ERROR]: {str(e)}")
            return f"I'm having trouble with that. Could you rephrase your question?"
    
    def _get_conversation_context(self, max_messages=4):
        """Get recent conversation history for context - only if relevant"""
        if not self.conversation_history or len(self.conversation_history) < 2:
            return ""
        
        # Only get last 2 exchanges (4 messages total)
        recent = self.conversation_history[-4:-1] if len(self.conversation_history) > 4 else self.conversation_history[:-1]
        
        if not recent:
            return ""
        
        context = "Recent context:\n"
        for msg in recent[-4:]:  # Max 4 messages
            role = "User" if msg['role'] == 'user' else "Assistant"
            context += f"{role}: {msg['content'][:100]}...\n"  # Truncate long messages
        
        return context + "\n"
    
    def _handle_search_query(self, user_input):
        """Handle queries that require web search"""
        search_results = self.search.search(user_input)
        
        # Handle search failures
        if "error" in search_results.lower() or "unavailable" in search_results.lower():
            return self.llm.generate_with_history(user_input, self.conversation_history)
        
        if "no search results" in search_results.lower() or "failed" in search_results.lower():
            return self.llm.generate_with_history(user_input, self.conversation_history)
        
        # Get conversation context
        context = self._get_conversation_context()
        
        # Send clean search results to LLM
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = f"""Today is {current_date}.

Question: {user_input}

Web search results:
{search_results}

Answer naturally and conversationally. Don't mention previous topics unless directly relevant."""
        
        return self.llm.generate(prompt, use_search_context=True)
    
    def _handle_general_query(self, user_input):
        """Handle general queries without search"""
        # Use conversation history
        return self.llm.generate_with_history(user_input, self.conversation_history)