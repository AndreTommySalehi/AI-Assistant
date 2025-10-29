"""
Jarvis Assistant - Modular architecture
Fixed: News triggers and two-step news system
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
except ImportError:
    PERSONALITY_AVAILABLE = False
    PersonalityEngine = None

# Try to import news aggregator
try:
    from .news_aggregator import NewsAggregator
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False
    NewsAggregator = None


class JarvisAssistant:

    def __init__(self, model_name=None, memory_config=None, debug=False, enable_ab_testing=True):
        # Initialize LLM first
        self.llm = LLMHandler(model_name, enable_ab_testing=enable_ab_testing)
        
        # Initialize web search
        try:
            self.search = WebSearch()
        except Exception:
            self.search = None
        
        # Initialize memory system
        self.memory = ModularMemorySystem(
            llm_handler=self.llm,
            config=memory_config or {}
        )
        
        # Initialize personality system (if available)
        if PERSONALITY_AVAILABLE:
            self.personality = PersonalityEngine()
        else:
            self.personality = None
        
        # Initialize news aggregator (if available)
        if NEWS_AVAILABLE:
            self.news = NewsAggregator()
        else:
            self.news = None
        
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
            
            # More specific news triggers
            news_keywords = [
                'news', 'daily recap', 'daily summary', 'daily briefing',
                'headlines', 'top stories', "what's happening today",
                'current events', 'news summary', 'give me the news',
                'tell me the news', 'today\'s news'
            ]
            
            # Check for exact news request (not just containing "today")
            user_lower = user_input.lower().strip()
            is_news_request = any(keyword in user_lower for keyword in news_keywords)
            
            # Check for "more" command (news deep-dive)
            if user_lower.startswith('more ') and self.news:
                return self._handle_news_deepdive(user_input)
            
            # Handle news request
            if is_news_request and self.news:
                return self._handle_news_request(user_input, headlines_only=True)
            
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
            personality_prompt = "You are Jarvis, a professional AI assistant. Always address the user as 'sir' or 'ma'am'. The current date is October 28, 2025."
        
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
    
    def _handle_news_deepdive(self, user_input):
        """Handle 'more [topic]' command for news details"""
        # Extract topic identifier (number or keywords)
        more_text = user_input.lower().replace('more', '').strip()
        
        if not more_text:
            return "Please specify which story you'd like more details on. For example: 'more 3' or 'more ChatGPT suicide'."
        
        # Get topic details
        details = self.news.get_topic_details(more_text)
        
        if not details:
            return f"I couldn't find that topic. Please try a different number or keywords from the news list."
        
        # Format and return details
        formatted = self.news.format_topic_details(details)
        
        # Get LLM to summarize the detailed articles
        if self.personality:
            personality_prompt = self.personality.get_system_prompt_modifier()
        else:
            personality_prompt = "You are JARVIS, an advanced AI assistant."
        
        articles_text = "\n\n".join([
            f"Article {i+1} ({art['source']}):\n{art['title']}\n{art['description']}"
            for i, art in enumerate(details['articles'])
        ])
        
        prompt = f"""{personality_prompt}

The user asked for more details about: "{details['headline']}"

Here are related articles:

{articles_text}

Provide a comprehensive summary (2-3 paragraphs) covering:
1. What happened
2. Why it matters
3. Key implications or context

Be conversational and informative."""
        
        llm_summary = self.llm.generate(prompt, use_search_context=False)
        
        return f"\n{formatted}\n\nSUMMARY:\n{llm_summary}"
    
    def _handle_news_request(self, user_input, headlines_only=True):
        """Handle news/daily summary requests - headlines only by default"""
        print("\n", end="", flush=True)
        
        # Fetch news
        summary = self.news.get_daily_summary()
        
        if headlines_only:
            # Just show the headlines list
            formatted = self.news.format_summary(summary, show_numbers=True)
            print(formatted)
            
            # Simple spoken response
            total_stories = sum(len(summary.get(cat, [])) for cat in ['general', 'tech', 'business', 'science'])
            
            if self.personality:
                personality_prompt = self.personality.get_system_prompt_modifier()
            else:
                personality_prompt = "You are JARVIS, an advanced AI assistant."
            
            prompt = f"""{personality_prompt}

Today's news summary is ready with {total_stories} stories across technology, business, general news, and science.

Respond briefly (1 sentence) saying the news is ready and they can ask for more details on any story using 'more [number]' or 'more [topic]'.

Keep it conversational and brief."""
            
            spoken_response = self.llm.generate(prompt, use_search_context=False)
            
            return spoken_response
        
        # Full detailed summary (only if specifically requested)
        else:
            formatted = self.news.format_summary(summary, show_numbers=True)
            print(formatted)
            
            news_text = self.news.get_summary_for_llm(summary)
            
            if self.personality:
                personality_prompt = self.personality.get_system_prompt_modifier()
            else:
                personality_prompt = "You are JARVIS, an advanced AI assistant."
            
            prompt = f"""{personality_prompt}

Here are today's top headlines:

{news_text}

Create a comprehensive daily briefing organized by category. For each category that has news:

[Keep the same detailed format as before...]

Critical formatting rules:
- Keep responses under 5 sentences total
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
        print(f"Auto-learning {status}")
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