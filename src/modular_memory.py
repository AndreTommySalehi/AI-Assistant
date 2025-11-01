import json
import os
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import re

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError as e:
    CHROMADB_AVAILABLE = False
    CHROMADB_ERROR = str(e)


# ============================================================================
# BASE CLASSES
# ============================================================================

class MemoryBackend(ABC):
    @abstractmethod
    def save_fact(self, fact, category, metadata=None):
        pass
    
    @abstractmethod
    def get_facts(self, query=None, limit=10):
        pass
    
    @abstractmethod
    def get_all_facts(self):
        pass


class LearningEngine(ABC):
    @abstractmethod
    def extract_facts(self, text, context=None):
        pass


class ContextRetriever(ABC):
    @abstractmethod
    def get_relevant_context(self, query, limit=5):
        pass


# ============================================================================
# IMPLEMENTATIONS
# ============================================================================

class JSONMemoryBackend(MemoryBackend):
    """File-based memory storage"""
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load()
    
    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except:
                return {"facts": [], "metadata": {}}
        return {"facts": [], "metadata": {}}
    
    def _save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def save_fact(self, fact, category, metadata=None):
        # Check for duplicates with better matching
        fact_lower = fact.lower().strip()
        for existing in self.data["facts"]:
            existing_lower = existing["fact"].lower().strip()
            # More lenient duplicate checking
            if self._are_similar(fact_lower, existing_lower):
                # Update if new fact is more specific
                if len(fact) > len(existing["fact"]):
                    existing["fact"] = fact
                    existing["timestamp"] = datetime.now().isoformat()
                    existing["metadata"] = metadata or {}
                    self._save()
                return False
        
        fact_entry = {
            "fact": fact,
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "access_count": 0,
            "last_accessed": None,
            "metadata": metadata or {}
        }
        
        self.data["facts"].append(fact_entry)
        self._save()
        return True
    
    def _are_similar(self, fact1, fact2):
        """Check if two facts are similar enough to be duplicates"""
        # Exact match
        if fact1 == fact2:
            return True
        
        # Check if one contains the other (for birthday updates)
        if fact1 in fact2 or fact2 in fact1:
            return True
        
        # Word overlap check
        words1 = set(fact1.split())
        words2 = set(fact2.split())
        overlap = len(words1 & words2)
        min_length = min(len(words1), len(words2))
        
        # If 70% of words match, consider it similar
        if min_length > 0 and overlap / min_length > 0.7:
            return True
        
        return False
    
    def get_facts(self, query=None, limit=10):
        if not query:
            return self.data["facts"][-limit:]
        
        query_lower = query.lower()
        relevant = []
        
        # Better keyword matching
        query_words = query_lower.split()
        expanded_keywords = set(query_words)
        
        # Synonym expansion
        keyword_map = {
            'birthday': ['birthday', 'born', 'birth date', 'age', 'bday'],
            'favorite': ['favorite', 'favourite', 'fav', 'like', 'prefer', 'love'],
            'pizza': ['pizza', 'pie'],
            'food': ['food', 'eat', 'meal', 'dish'],
            'game': ['game', 'gaming', 'play'],
            'live': ['live', 'from', 'location', 'city'],
            'name': ['name', 'called'],
            'dog': ['dog', 'puppy', 'pet'],
            'cat': ['cat', 'kitten', 'pet'],
        }
        
        for word in query_words:
            if word in keyword_map:
                expanded_keywords.update(keyword_map[word])
        
        for fact in self.data["facts"]:
            fact_lower = fact["fact"].lower()
            
            # Prioritize exact category matches
            if fact["category"] == "identity" and any(k in query_lower for k in ['birthday', 'born', 'age']):
                if any(keyword in fact_lower for keyword in expanded_keywords):
                    fact["access_count"] = fact.get("access_count", 0) + 1
                    fact["last_accessed"] = datetime.now().isoformat()
                    relevant.insert(0, fact)  # Put at front
                    continue
            
            # Check if any expanded keyword matches
            if any(keyword in fact_lower for keyword in expanded_keywords):
                fact["access_count"] = fact.get("access_count", 0) + 1
                fact["last_accessed"] = datetime.now().isoformat()
                relevant.append(fact)
        
        self._save()
        
        # Sort by access count and recency
        relevant.sort(key=lambda x: (x.get("access_count", 0), x["timestamp"]), reverse=True)
        
        return relevant[:limit] if relevant else []
    
    def get_all_facts(self):
        return self.data["facts"]


class LLMBasedLearning(LearningEngine):
    """Learning using LLM - IMPROVED with better filtering"""
    
    def __init__(self, llm_handler):
        self.llm = llm_handler
        
        # Phrases to NEVER learn from (trivial/generic responses)
        self.ignore_phrases = [
            "i'm fine", "i'm okay", "i'm good", "i'm alright",
            "sounds good", "that's fine", "no problem", "sure",
            "yes", "no", "maybe", "thanks", "thank you",
            "okay", "ok", "cool", "nice", "great",
            "i see", "got it", "understood", "alright"
        ]
    
    def extract_facts(self, text, context=None):
        """Use LLM to extract IMPORTANT facts only"""
        
        # Skip if too short
        if len(text.split()) < 3:
            return []
        
        # Skip trivial responses
        text_lower = text.lower().strip()
        if any(phrase in text_lower for phrase in self.ignore_phrases):
            return []
        
        # Skip questions
        if any(text_lower.startswith(q) for q in ['what', 'where', 'when', 'who', 'why', 'how', 'is', 'are', 'do', 'does', 'can', 'could', 'would']):
            return []
        
        # Enhanced prompt for better extraction
        analysis_prompt = f"""Extract ONLY important personal facts from this statement. Ignore generic responses.

User said: "{text}"

RULES:
1. IGNORE: "I'm fine", "sounds good", "okay", "yes", "no", "thanks" - these are NOT facts
2. For birthdays: Always specify if it's the USER'S birthday or someone else's (dog, family, friend)
3. Extract names, dates, preferences, relationships, goals
4. Only extract if confidence > 0.85 (very certain)

Examples:
✓ "My birthday is March 24, 2010" → {{"fact": "User's birthday is March 24, 2010", "category": "identity", "confidence": 0.95}}
✓ "My dog's birthday is June 5" → {{"fact": "User's dog's birthday is June 5", "category": "relationships", "confidence": 0.90}}
✗ "I'm fine" → [] (ignore trivial response)
✗ "Sounds good" → [] (ignore trivial response)

Return JSON list (empty [] if nothing important):
[
  {{"fact": "...", "category": "...", "confidence": 0.xx}}
]

Categories: identity, interests, preferences, relationships, events, goals, routines, other

JSON only:"""
        
        try:
            response = self.llm.generate(analysis_prompt, use_search_context=False)
            
            # Find JSON in response
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            
            if json_match:
                facts = json.loads(json_match.group(0))
                
                # Very strict filtering - only high confidence, important facts
                valid_facts = []
                for f in facts:
                    confidence = f.get('confidence', 0)
                    fact_text = f.get('fact', '').strip().lower()
                    
                    # Skip if low confidence
                    if confidence < 0.85:
                        continue
                    
                    # Skip if contains trivial phrases
                    if any(phrase in fact_text for phrase in self.ignore_phrases):
                        continue
                    
                    # Fact must be substantial
                    if len(fact_text) < 10:
                        continue
                    
                    valid_facts.append(f)
                
                return valid_facts
            
        except Exception as e:
            print(f"[LLM Learning Error]: {e}")
        
        return []


class PatternBasedLearning(LearningEngine):
    """Pattern recognition - IMPROVED"""
    
    def extract_facts(self, text, context=None):
        """Extract facts using patterns - IGNORES trivial responses"""
        facts = []
        text_lower = text.lower()
        
        # CRITICAL: Skip trivial responses
        trivial = [
            "i'm fine", "i'm okay", "i'm good", "i'm alright",
            "sounds good", "that's fine", "no problem", "sure",
            "yes", "no", "maybe", "thanks", "okay", "ok", "cool"
        ]
        if any(phrase in text_lower for phrase in trivial):
            return []
        
        # Skip questions
        if any(text_lower.strip().startswith(q) for q in ['what', 'where', 'when', 'who', 'why', 'how', 'is', 'are', 'do', 'does']):
            return []
        
        # Pattern: Birthday (with clear subject identification)
        birthday_patterns = [
            (r"my birthday is ([A-Z][a-z]+ \d{1,2},? \d{4})", "identity", 0.95, "User's birthday is {}"),
            (r"i was born (?:on )?([A-Z][a-z]+ \d{1,2},? \d{4})", "identity", 0.95, "User's birthday is {}"),
            (r"my (?:dog|cat|pet)(?:'s)? birthday is ([A-Z][a-z]+ \d{1,2})", "relationships", 0.90, "User's pet's birthday is {}"),
        ]
        
        for pattern, category, confidence, fact_template in birthday_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date = match.group(1).strip()
                fact = fact_template.format(date)
                facts.append({
                    "fact": fact,
                    "category": category,
                    "confidence": confidence
                })
        
        # Pattern: Name
        name_patterns = [
            (r"(?:my name is|i'm|i am|call me)\s+([A-Z][a-z]+)", "identity", 0.90, "User's name is {}"),
        ]
        
        for pattern, category, confidence, fact_template in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if name not in ['Fine', 'Okay', 'Good', 'Alright']:  # Don't learn "I'm Fine" as name
                    fact = fact_template.format(name)
                    facts.append({
                        "fact": fact,
                        "category": category,
                        "confidence": confidence
                    })
        
        # Pattern: Location
        location_patterns = [
            (r"i live in ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "identity", 0.88, "User lives in {}"),
            (r"i'm from ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "identity", 0.88, "User is from {}"),
        ]
        
        for pattern, category, confidence, fact_template in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                fact = fact_template.format(location)
                facts.append({
                    "fact": fact,
                    "category": category,
                    "confidence": confidence
                })
        
        # Pattern: Strong preferences (avoid weak ones)
        strong_preference_patterns = [
            (r"i (?:really love|absolutely love|love)\s+([a-z\s]{3,30})(?:\.|!|,)", "preferences", 0.88, "User loves {}"),
            (r"my favorite\s+(?:food|game|movie|book|color)\s+is\s+([^.!?,]+)", "preferences", 0.92, "User's favorite is {}"),
        ]
        
        for pattern, category, confidence, fact_template in strong_preference_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                thing = match.group(1).strip()
                # Must be substantial
                if len(thing) > 3 and thing not in trivial:
                    fact = fact_template.format(thing)
                    facts.append({
                        "fact": fact,
                        "category": category,
                        "confidence": confidence
                    })
        
        return facts


class SemanticContextRetriever(ContextRetriever):
    """Semantic search using embeddings"""
    
    def __init__(self, persist_directory):
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB required for semantic search")
        
        print(f"  - Initializing semantic search in {persist_directory}...")
        
        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self.collection = self.client.get_or_create_collection(
                name="jarvis_semantic_memory",
                embedding_function=self.embedding_function
            )
            print(f"  - Semantic search: enabled")
        except Exception as e:
            import traceback
            print(f"  - Semantic search initialization failed:")
            print(f"    Error: {str(e)}")
            traceback.print_exc()
            raise Exception(f"Failed to initialize semantic search: {str(e)}")
    
    def add_fact(self, fact, metadata):
        """Add fact to semantic search index"""
        doc_id = f"fact_{self.collection.count()}_{datetime.now().timestamp()}"
        self.collection.add(
            documents=[fact],
            ids=[doc_id],
            metadatas=[metadata]
        )
    
    def get_relevant_context(self, query, limit=5):
        """Get semantically similar facts"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            if results['documents'][0]:
                context = []
                for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                    context.append({
                        'fact': doc,
                        'category': metadata.get('category', 'general'),
                        'relevance': 'high'
                    })
                return context
        except Exception as e:
            print(f"[Retrieval Error]: {e}")
        
        return []


# ============================================================================
# MAIN MEMORY SYSTEM
# ============================================================================

class ModularMemorySystem:
    """Main memory system with much better fact filtering"""
    
    def __init__(self, data_dir="./jarvis_data", llm_handler=None, config=None):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        config = config or {}
        
        # Storage Backend
        self.storage = JSONMemoryBackend(
            os.path.join(data_dir, "memory_v2.json")
        )
        
        # Learning Engines
        self.learning_engines = []
        
        if llm_handler:
            self.learning_engines.append(
                LLMBasedLearning(llm_handler)
            )
        
        # Pattern-based as fallback
        self.learning_engines.append(
            PatternBasedLearning()
        )
        
        # Context Retriever
        self.context_retriever = None
        if CHROMADB_AVAILABLE:
            try:
                self.context_retriever = SemanticContextRetriever(
                    os.path.join(data_dir, "semantic_db")
                )
            except Exception as e:
                print(f"  - Semantic search: disabled ({str(e)[:50]}...)")
                self.context_retriever = None
        
        # Stats tracking
        self.stats = {
            "total_learned": 0,
            "by_category": {},
            "by_engine": {},
            "session_start": datetime.now().isoformat()
        }
        
        print(f"✓ Memory system initialized")
        print(f"  - Storage: {type(self.storage).__name__}")
        print(f"  - Learning engines: {len(self.learning_engines)}")
    
    def learn_from_conversation(self, user_message, assistant_response=None):
        """Learn from conversation - MUCH STRICTER filtering"""
        learned_count = 0
        
        # Try each learning engine
        for engine in self.learning_engines:
            try:
                facts = engine.extract_facts(user_message)
                
                for fact_data in facts:
                    fact = fact_data.get('fact', '')
                    category = fact_data.get('category', 'general')
                    confidence = fact_data.get('confidence', 0.8)
                    
                    # Only save high-confidence facts
                    if confidence < 0.85:
                        continue
                    
                    # Save to storage
                    if self.storage.save_fact(fact, category, {
                        'confidence': confidence,
                        'engine': type(engine).__name__,
                        'learned_from': user_message[:100]
                    }):
                        learned_count += 1
                        
                        # Also add to semantic search
                        if self.context_retriever:
                            self.context_retriever.add_fact(fact, {
                                'category': category,
                                'confidence': confidence,
                                'timestamp': datetime.now().isoformat()
                            })
                        
                        # Update stats
                        self.stats['total_learned'] += 1
                        self.stats['by_category'][category] = \
                            self.stats['by_category'].get(category, 0) + 1
                        self.stats['by_engine'][type(engine).__name__] = \
                            self.stats['by_engine'].get(type(engine).__name__, 0) + 1
                
            except Exception as e:
                print(f"[Engine Error - {type(engine).__name__}]: {e}")
                continue
        
        return learned_count
    
    def get_context_for_query(self, query):
        """Get relevant context using best available method"""
        
        # Method 1: Semantic search (best)
        if self.context_retriever:
            context = self.context_retriever.get_relevant_context(query, limit=5)
            if context:
                return self._format_context(context)
        
        # Method 2: Keyword search
        facts = self.storage.get_facts(query, limit=5)
        if facts:
            context = [{'fact': f['fact'], 'category': f['category']} for f in facts]
            return self._format_context(context)
        
        return ""
    
    def _format_context(self, context_list):
        """Format context for LLM"""
        if not context_list:
            return ""
        
        formatted = ["What I know about you:"]
        
        # Group by category
        by_category = {}
        for item in context_list:
            cat = item['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item['fact'])
        
        for category, facts in by_category.items():
            formatted.append(f"\n{category.title()}:")
            for fact in facts:
                formatted.append(f"  - {fact}")
        
        return "\n".join(formatted)
    
    def remember_fact_manually(self, fact, category="general"):
        """Manually add a fact"""
        return self.storage.save_fact(fact, category)
    
    def get_stats(self):
        """Get memory statistics"""
        all_facts = self.storage.get_all_facts()
        
        return {
            "total_facts": len(all_facts),
            "learned_this_session": self.stats['total_learned'],
            "by_category": self.stats['by_category'],
            "by_learning_engine": self.stats['by_engine'],
            "storage_backend": type(self.storage).__name__,
            "learning_engines": [type(e).__name__ for e in self.learning_engines],
            "semantic_search": self.context_retriever is not None
        }
    
    def export_training_data(self, filepath):
        """Export all facts for fine-tuning"""
        all_facts = self.storage.get_all_facts()
        
        training_data = {
            "metadata": {
                "exported": datetime.now().isoformat(),
                "total_facts": len(all_facts),
                "format": "jarvis_v1"
            },
            "facts": all_facts
        }
        
        with open(filepath, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        print(f"✓ Exported {len(all_facts)} facts to {filepath}")
        
        return filepath