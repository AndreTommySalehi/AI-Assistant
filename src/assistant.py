"""
Jarvis Assistant - Modular architecture
Easy to upgrade components without breaking things!
"""

from datetime import datetime
import re
from .llm import LLMHandler
from .search import WebSearch
from .modular_memory import ModularMemorySystem
from .personality import PersonalityEngine, PersonalityResponse


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
        
        # Build enhanced prompt
        if context:
            enhanced_input = f"{context}\n\n---\n\nUser's current message: {user_input}\n\nRespond naturally, referencing what you know about them when relevant."
        else:
            enhanced_input = user_input
        
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
        
        # Build search-enhanced prompt
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = f"""TODAY'S DATE: {current_date}

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


# ============================================================================
# UPGRADE GUIDE (Future You Will Thank Present You!)
# ============================================================================

"""
HOW TO UPGRADE COMPONENTS:

1. STORAGE UPGRADE (JSON → Database):
   
   # In modular_memory.py, create new backend:
   class PostgreSQLMemoryBackend(MemoryBackend):
       def __init__(self, connection_string):
           self.conn = psycopg2.connect(connection_string)
       # ... implement interface
   
   # In this file, just change:
   memory_config = {'storage': 'postgresql', 'connection': 'postgres://...'}
   assistant = JarvisAssistant(memory_config=memory_config)


2. LEARNING UPGRADE (Add custom model):
   
   # In modular_memory.py:
   class CustomNERLearning(LearningEngine):
       def __init__(self):
           self.model = load_ner_model()
       # ... implement interface
   
   # System automatically uses it alongside existing engines!


3. CONTEXT RETRIEVAL UPGRADE (Add graph database):
   
   # In modular_memory.py:
   class Neo4jContextRetriever(ContextRetriever):
       # Build knowledge graph
   
   # Swap in config:
   memory_config = {'retriever': 'neo4j'}


4. FINE-TUNING INTEGRATION:
   
   # You already have training data being exported!
   # When ready:
   training_data = load_json('training_export_*.json')
   fine_tune_model(base_model='qwen2.5:14b', data=training_data)
   
   # Then use fine-tuned model:
   assistant = JarvisAssistant(model_name='jarvis-finetuned')


Everything is designed to be upgraded piece by piece.
No need to rewrite the whole system!
"""