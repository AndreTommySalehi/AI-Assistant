from datetime import datetime as dt_module
import re
from .llm import LLMHandler
from .search import WebSearch
from .modular_memory import ModularMemorySystem
from .app_launcher import AppLauncher
from .calendar_handler import CalendarHandler

try:
    from .reflection_engine import ReflectionEngine, MultiAgentDebate
    REFLECTION_AVAILABLE = True
except ImportError:
    REFLECTION_AVAILABLE = False
    ReflectionEngine = None
    MultiAgentDebate = None

try:
    from .personality import PersonalityEngine
    PERSONALITY_AVAILABLE = True
except ImportError:
    PERSONALITY_AVAILABLE = False
    PersonalityEngine = None

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
        
        # Initialize app launcher
        print("Initializing app launcher...")
        self.app_launcher = AppLauncher()
        print(f"App launcher ready with {len(self.app_launcher.apps)} apps")
        
        # Initialize calendar manager
        print("Initializing calendar...")
        self.calendar = CalendarHandler()
        
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
        
        # Initialize reflection engine (if available)
        if REFLECTION_AVAILABLE:
            self.reflection = ReflectionEngine(self.llm)
            self.debate = MultiAgentDebate(self.llm)
            print("✓ Self-reflection enabled")
        else:
            self.reflection = None
            self.debate = None
        
        # Search cache (simple dict for now)
        self.search_cache = {}
        
        # Conversation memory
        self.conversation_history = []
        self.max_history = 10
        
        # Learning settings
        self.auto_learn = True
        self.learn_frequency = 1
        self.message_count = 0
        self.debug = debug
        
        # Track last assistant action to avoid repeated offers
        self.last_action_needed_followup = False
    
    def chat(self, user_input):
        """Process user input and return response"""
        try:
            self.message_count += 1
            
            # Check if user is declining help/dismissing
            decline_words = ['no', 'nope', 'nah', 'im good', "i'm good", 'im fine', "i'm fine", 
                            'im okay', "i'm okay", 'thats all', "that's all", 'nothing else']
            if any(word in user_input.lower().strip() for word in decline_words):
                if self.last_action_needed_followup:
                    # User is saying no to our offer of help
                    self.last_action_needed_followup = False
                    return "Understood, sir."
            
            # Check for app launch commands FIRST
            if self.app_launcher.can_handle(user_input):
                app_name = self.app_launcher.extract_app_name(user_input)
                if app_name:
                    success, message = self.app_launcher.open_app(app_name)
                    self.last_action_needed_followup = False  # Don't follow up after opening app
                    if success:
                        return f"Opening {app_name}, sir."
                    else:
                        return f"I couldn't open {app_name}, sir. {message}"
                else:
                    return "I'm not sure which app you want me to open, sir."
            
            # Check for calendar commands
            if self.calendar.can_handle(user_input):
                success, message = self.calendar.handle_command(user_input)
                self.last_action_needed_followup = False  # Don't follow up after calendar action
                return message
            
            # Check for simple date/time questions (don't search for these)
            date_time_patterns = [
                r'\b(what|whats|what\'s)\s+(is\s+)?(the\s+)?(date|time|day)\b',
                r'\b(current|today\'?s?)\s+(date|time|day)\b',
                r'\bwhat\s+day\s+is\s+it\b',
            ]
            
            if any(re.search(pattern, user_input.lower()) for pattern in date_time_patterns):
                current_date = dt_module.now().strftime("%B %d, %Y")
                current_time = dt_module.now().strftime("%I:%M %p")
                current_day = dt_module.now().strftime("%A")
                
                # Determine what they're asking for
                if 'time' in user_input.lower():
                    return f"It's {current_time}, sir."
                elif 'day' in user_input.lower():
                    return f"Today is {current_day}, {current_date}, sir."
                else:
                    return f"Today is {current_date}, sir."
            
            # Check for reflection/debate commands
            if self.reflection:
                if user_input.lower().startswith('debate '):
                    question = user_input[7:].strip()
                    if question:
                        answer, debate_history = self.debate.debate(question, rounds=2)
                        return f"\n[Multi-Agent Debate Result]\n\n{answer}"
                    else:
                        return "Please provide a question to debate. Example: 'debate should I learn Python or JavaScript?'"
                
                if user_input.lower().startswith('think '):
                    question = user_input[6:].strip()
                    if question:
                        answer = self.reflection.chain_of_thought(
                            question,
                            context=self.memory.get_context_for_query(question)
                        )
                        return f"\n[Chain-of-Thought Reasoning]\n\n{answer}"
                    else:
                        return "Please provide a question to think through. Example: 'think how does photosynthesis work?'"
                
                if user_input.lower() == 'reflection stats':
                    stats = self.reflection.get_stats()
                    return f"""Reflection Statistics:
   Total reflections: {stats['total_reflections']}
   Improvements made: {stats['improvements_made']}
   Improvement rate: {stats['improvement_rate']:.1%}
   Status: {'Enabled' if stats['enabled'] else 'Disabled'}"""
                
                if user_input.lower() in ['reflection on', 'reflection off']:
                    enabled = 'on' in user_input.lower()
                    self.reflection.toggle_reflection(enabled)
                    return f"Self-reflection {'enabled' if enabled else 'disabled'}, sir."
            
            # More specific news triggers
            news_keywords = [
                'news', 'daily recap', 'daily summary', 'daily briefing',
                'headlines', 'top stories', "what's happening today",
                'current events', 'news summary', 'give me the news',
                'tell me the news', 'today\'s news'
            ]
            
            # Check for exact news request
            user_lower = user_input.lower().strip()
            is_news_request = any(keyword in user_lower for keyword in news_keywords)
            
            # Check for "more" command (news deep-dive)
            if user_lower.startswith('more ') and self.news:
                return self._handle_news_deepdive(user_input)
            
            # Handle news request
            if is_news_request and self.news:
                return self._handle_news_request(user_input, headlines_only=True)
            
            # Evolve personality based on this interaction
            if self.personality:
                self.personality.evolve_personality(user_input)
            
            # Add user message to history
            self.conversation_history.append({
                'role': 'user',
                'content': user_input,
                'timestamp': dt_module.now().isoformat()
            })
            
            # Generate response
            if self.search and self.search.needs_search(user_input):
                response = self._handle_search_query(user_input)
            else:
                response = self._handle_general_query(user_input)
            
            # SELF-REFLECTION: Check if response needs improvement
            if self.reflection and self.reflection.should_reflect(user_input, response):
                if self.debug:
                    print("\n[Self-Reflection Triggered]")
                
                improved_response, was_improved, notes = self.reflection.reflect_and_improve(
                    user_input, 
                    response,
                    context=self.memory.get_context_for_query(user_input)
                )
                
                if was_improved:
                    if self.debug:
                        print(f"[Response improved - Accuracy: {notes['accuracy']:.2f}, Completeness: {notes['completeness']:.2f}]")
                    response = improved_response
                    print("[✓] ", end="", flush=True)  # Visual indicator
            
            # Add assistant response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': response,
                'timestamp': dt_module.now().isoformat()
            })
            
            # Auto-learn from this conversation (with better filtering now)
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
                    print("[*] ", end="", flush=True)
            
            # Trim history if too long
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            # Check if this response needs followup (avoid asking after simple actions)
            self.last_action_needed_followup = self._should_offer_followup(response)
            
            return response
            
        except Exception as e:
            print(f"\n[Error]: {str(e)}")
            import traceback
            traceback.print_exc()
            return "I'm having trouble processing that. Could you try rephrasing?"
    
    def _should_offer_followup(self, response):
        """Determine if response warrants offering more help"""
        # Don't offer followup for:
        # - Confirmations (already done something)
        # - Simple answers
        # - Commands executed
        
        lower_response = response.lower()
        
        # If it's a confirmation, no followup needed
        confirmation_words = ['opening', 'created', 'set', 'done', 'understood', 'noted', 'got it']
        if any(word in lower_response for word in confirmation_words):
            return False
        
        # If it's a very short response (< 20 words), probably don't need followup
        if len(response.split()) < 20:
            return False
        
        return False  # Default: don't offer followup
    
    def _handle_general_query(self, user_input):
        """Handle queries without web search"""
        
        # Get relevant context from memory
        context = self.memory.get_context_for_query(user_input)
        
        # Get personality-adjusted system prompt with STRONGER effects
        if self.personality:
            personality_prompt = self.personality.get_system_prompt_modifier()
        else:
            # Dynamic date - get fresh each time
            current_date = dt_module.now().strftime("%B %d, %Y")
            personality_prompt = f"You are Jarvis, a professional AI assistant. Always address the user as 'sir'. The current date is {current_date}."
        
        # Build enhanced prompt
        if context:
            enhanced_input = f"""{personality_prompt}

{context}

IMPORTANT: The information above is what you know about the user. Use it to personalize your response when relevant.

---

User's current message: {user_input}

Respond naturally and personally, referencing what you know about them when relevant."""
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
            if (dt_module.now() - cached_time).seconds < 3600:
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
        
        # Build search-enhanced prompt with dynamic date
        current_date = dt_module.now().strftime("%B %d, %Y")
        prompt = f"""{personality_prompt}

TODAY'S DATE: {current_date}

USER QUESTION: {user_input}

CURRENT WEB SEARCH RESULTS:
{search_results}

Instructions: Answer the user's question using the search results above. Be conversational and natural."""
        
        response = self.llm.generate(prompt, use_search_context=True)
        
        # Cache the result
        self.search_cache[cache_key] = (dt_module.now(), response)
        
        # Limit cache size
        if len(self.search_cache) > 50:
            sorted_cache = sorted(
                self.search_cache.items(),
                key=lambda x: x[1][0]
            )
            self.search_cache = dict(sorted_cache[-25:])
        
        return response
    
    def _handle_news_deepdive(self, user_input):
        """Handle 'more [topic]' command for news details"""
        more_text = user_input.lower().replace('more', '').strip()
        
        if not more_text:
            return "Please specify which story you'd like more details on. For example: 'more 3' or 'more bitcoin'."
        
        details = self.news.get_topic_details(more_text)
        
        if not details:
            return f"I couldn't find that topic. Please try a different number or keywords from the news list."
        
        formatted = self.news.format_topic_details(details)
        
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
        """Handle news/daily summary requests"""
        print("\n", end="", flush=True)
        
        summary = self.news.get_daily_summary()
        
        if headlines_only:
            formatted = self.news.format_summary(summary, show_numbers=True)
            print(formatted)
            
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

Create a comprehensive daily briefing organized by category. For each category that has news, keep responses under 5 sentences total and be clear and informative."""
            
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
            filepath = f"./jarvis_data/training_export_{dt_module.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return self.memory.export_training_data(filepath)
    
    def get_memory_stats(self):
        """Get detailed memory statistics"""
        return self.memory.get_stats()
    
    def shutdown(self):
        """Save everything before exiting"""
        print("\nSaving memories...")
        
        try:
            export_path = self.export_for_finetuning()
            print(f"Training data exported: {export_path}")
        except Exception as e:
            print(f"Export failed: {e}")
        
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