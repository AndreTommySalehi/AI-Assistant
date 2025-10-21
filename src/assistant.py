"""
Jarvis Assistant - Modular architecture
Easy to upgrade components without breaking things!
"""

from datetime import datetime
import re
from .llm import LLMHandler
from .search import WebSearch
from .modular_memory import ModularMemorySystem

# Try to import personality - optional
try:
    from .personality import PersonalityEngine
    PERSONALITY_AVAILABLE = True
    print("  - Personality system: enabled")
except ImportError as e:
    PERSONALITY_AVAILABLE = False
    PersonalityEngine = None
    print(f"  - Personality system: disabled (personality.py not found)")

# Try to import news aggregator
try:
    from .news_aggregator import NewsAggregator
    NEWS_AVAILABLE = True
    print("  - News aggregator: enabled")
except ImportError as e:
    NEWS_AVAILABLE = False
    NewsAggregator = None
    print(f"  - News aggregator: disabled")


class JarvisAssistant:
    """Main assistant with modular, upgradeable memory"""
    
    def __init__(self, model_name=None, memory_config=None, debug=False):
        # Initialize LLM first
        self.llm = LLMHandler(model_name)
        
        # Initialize web search
        try:
            self.search = WebSearch()
        except Exception as e:
            self.search = None
            print("⚠️ Search unavailable")
        
        # Initialize MODULAR memory system
        self.memory = ModularMemorySystem(
            llm_handler=self.llm,
            config=memory_config or {}
        )
        
        # Initialize PERSONALITY system (if available)
        if PERSONALITY_AVAILABLE:
            self.personality = PersonalityEngine()
        else:
            self.personality = None
            print("  Note: Personality system disabled (create src/personality.py to enable)")
        
        # Initialize NEWS aggregator (if available)
        if NEWS_AVAILABLE:
            self.news = NewsAggregator()
        else:
            self.news = None
            print("  Note: News aggregator disabled")
        
        # Search cache (simple dict for now)
        self.search_cache = {}
        
        # Conversation memory
        self.conversation_history = []
        self.max_history = 10
        
        # Learning settings
        self.auto_learn = True  # Can be toggled
        self.learn_frequency = 1  # Learn every N messages (1 = every message)
        self.message_count = 0
        self.debug = debug  # Debug mode
    
    def chat(self, user_input):
        """Process user input and return response"""
        try:
            self.message_count += 1
            
            # Check for news request
            news_keywords = ['news', 'today', 'daily recap', 'what happened', "what's happening", 
                           'news summary', 'daily summary', 'current events']
            if any(keyword in user_input.lower() for keyword in news_keywords) and self.news:
                return self._handle_news_request(user_input)
            
            # Evolve personality based on this interaction (if available)
            if self.personality:
                self.personality.evolve_personality(user_input)
            
            # Add user message to history
            self.conversation_history.append({
                'role': 'user',
                'content': user_input,
                'timestamp': datetime.now().isoformat()
            })
            
            # Generate response
            if self.search and self.search.needs_search(user_input):
                response = self._handle_search_query(user_input)
            else:
                response = self._handle_general_query(user_input)
            
            # NOTE: Personality adjustments are now handled in the system prompt
            # No need for post-processing the response anymore!
            
            # Add assistant response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now().isoformat()
            })
            
            # Auto-learn from this conversation
            if self.auto_learn and (self.message_count % self.learn_frequency == 0):
                if self.debug:
                    print(f"\n[DEBUG] Attempting to learn from: '{user_input[:50]}...'")
                
                learned_count = self.memory.learn_from_conversation(
                    user_input, 
                    response
                )
                
                if self.debug:
                    print(f"[DEBUG] Learned {learned_count} facts")
                
                if learned_count > 0:
                    # Visual feedback - just a simple indicator
                    print("[*] ", end="", flush=True)
            
            # Trim history if too long
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            return response
            
        except Exception as e:
            print(f"\n[Error]: {str(e)}")
            import traceback
            traceback.print_exc()
            return "I'm having trouble processing that. Could you try rephrasing?"
    
    def _handle_general_query(self, user_input):
        """Handle queries without web search"""
        
        # Get relevant context from memory
        context = self.memory.get_context_for_query(user_input)
        
        # Get personality-adjusted system prompt (if available)
        if self.personality:
            personality_prompt = self.personality.get_system_prompt_modifier()
        else:
            personality_prompt = "You are Jarvis, a professional AI assistant. Always address the user as 'sir' or 'ma'am'. The current date is October 20, 2025."
        
        # Build enhanced prompt
        if context:
            enhanced_input = f"{personality_prompt}\n\n{context}\n\n---\n\nUser's current message: {user_input}\n\nRespond naturally, referencing what you know about them when relevant."
        else:
            enhanced_input = f"{personality_prompt}\n\nUser: {user_input}"
        
        return self.llm.generate_with_history(enhanced_input, self.conversation_history)
    
    def _handle_search_query(self, user_input):
        """Handle queries requiring web search"""
        
        # Check cache first
        cache_key = user_input.lower().strip()
        if cache_key in self.search_cache:
            cached_time, cached_result = self.search_cache[cache_key]
            # Cache valid for 1 hour
            if (datetime.now() - cached_time).seconds < 3600:
                print("(cached) ", end="", flush=True)
                return cached_result
        
        # Perform search
        search_results = self.search.search(user_input)
        
        # Handle failures
        if any(word in search_results.lower() for word in ['error', 'unavailable', 'failed']):
            return self.llm.generate_with_history(user_input, self.conversation_history)
        
        # Get personality prompt for search responses too
        if self.personality:
            personality_prompt = self.personality.get_system_prompt_modifier()
        else:
            personality_prompt = "You are JARVIS, an advanced AI assistant."
        
        # Build search-enhanced prompt
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = f"""{personality_prompt}

TODAY'S DATE: {current_date}

USER QUESTION: {user_input}

CURRENT WEB SEARCH RESULTS:
{search_results}

Instructions: Answer the user's question using the search results above. Be conversational and natural."""
        
        response = self.llm.generate(prompt, use_search_context=True)
        
        # Cache the result
        self.search_cache[cache_key] = (datetime.now(), response)
        
        # Limit cache size
        if len(self.search_cache) > 50:
            # Remove oldest entries
            sorted_cache = sorted(
                self.search_cache.items(),
                key=lambda x: x[1][0]
            )
            self.search_cache = dict(sorted_cache[-25:])
        
        return response
    
    def _handle_news_request(self, user_input):
        """Handle news/daily summary requests"""
        print("\n", end="", flush=True)
        
        # Fetch news
        summary = self.news.get_daily_summary()
        
        # Format for display
        formatted = self.news.format_summary(summary)
        print(formatted)
        
        # Also get LLM summary
        news_text = self.news.get_summary_for_llm(summary)
        
        # Get personality prompt
        if self.personality:
            personality_prompt = self.personality.get_system_prompt_modifier()
        else:
            personality_prompt = "You are JARVIS, an advanced AI assistant."
        
        # Ask LLM to summarize with structure
        prompt = f"""{personality_prompt}

Here are today's top headlines from reputable news sources:

{news_text}

User asked: "{user_input}"

Create a comprehensive daily briefing organized by category. For EACH category that has news:

Format EXACTLY like this:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💻 TECHNOLOGY

  • First major tech story here
    Brief explanation of what happened and why it matters.
    
  • Second tech story headline
    Context and impact in 1-2 sentences.
    
  • Third tech story if available
    What you need to know about it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 BUSINESS & MARKETS

  • Stock market story
    What happened in the markets and why.
    
  • Major business development
    Impact on economy or industry.
    
  • Other business news
    Key takeaways.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌍 GENERAL NEWS

  • Major world event
    What happened and significance.
    
  • Important national story
    Context and implications.
    
  • Other significant news
    Key points to know.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔬 SCIENCE

  • Scientific breakthrough
    Explained in simple terms with impact.
    
  • Research findings
    What was discovered and why it matters.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL FORMATTING RULES:
- Use the exact divider lines shown above (━━━━━)
- Add blank line after each bullet point
- Indent bullets with 2 spaces
- Keep explanation under bullet, not on same line
- Skip categories with no news
- Be clear and informative"""
        
        llm_summary = self.llm.generate(prompt, use_search_context=False)
        
        return f"\n{llm_summary}"
    
    def toggle_learning(self, enabled=None):
        """Turn auto-learning on/off"""
        if enabled is None:
            self.auto_learn = not self.auto_learn
        else:
            self.auto_learn = enabled
        
        status = "enabled" if self.auto_learn else "disabled"
        print(f"🧠 Auto-learning {status}")
        return self.auto_learn
    
    def export_for_finetuning(self, filepath=None):
        """Export training data for future fine-tuning"""
        if filepath is None:
            filepath = f"./jarvis_data/training_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return self.memory.export_training_data(filepath)
    
    def get_memory_stats(self):
        """Get detailed memory statistics"""
        return self.memory.get_stats()
    
    def shutdown(self):
        """Save everything before exiting"""
        print("\nSaving memories...")
        
        # Export training data automatically
        try:
            export_path = self.export_for_finetuning()
            print(f"Training data exported: {export_path}")
        except Exception as e:
            print(f"Export failed: {e}")
        
        # Show stats
        stats = self.get_memory_stats()
        print(f"\nSession Summary:")
        print(f"   Total facts remembered: {stats['total_facts']}")
        print(f"   Learned this session: {stats['learned_this_session']}")
        
        if stats['by_category']:
            print(f"\nBy Category:")
            for cat, count in stats['by_category'].items():
                print(f"   {cat}: {count}")
        
        if stats['by_learning_engine']:
            print(f"\nBy Learning Method:")
            for engine, count in stats['by_learning_engine'].items():
                print(f"   {engine}: {count}")
        
        print("\nGoodbye!")