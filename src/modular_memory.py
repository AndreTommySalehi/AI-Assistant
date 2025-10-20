"""
MODULAR Memory System - Easily upgradeable and extensible
Each component is independent and can be swapped out
"""

import json
import os
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import re

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


# ============================================================================
# BASE CLASSES - Define interfaces for each component
# ============================================================================

class MemoryBackend(ABC):
    """Base class for memory storage - swap this out for databases, cloud, etc."""
    
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
    """Base class for learning algorithms - upgrade learning strategies here"""
    
    @abstractmethod
    def extract_facts(self, text, context=None):
        """Return list of learned facts with confidence scores"""
        pass


class ContextRetriever(ABC):
    """Base class for retrieving relevant context - upgrade search methods here"""
    
    @abstractmethod
    def get_relevant_context(self, query, limit=5):
        pass


# ============================================================================
# IMPLEMENTATIONS - Current versions (easy to upgrade later)
# ============================================================================

class JSONMemoryBackend(MemoryBackend):
    """File-based memory storage - V1"""
    
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
        # Check for duplicates
        for existing in self.data["facts"]:
            if existing["fact"].lower().strip() == fact.lower().strip():
                return False  # Already exists
        
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
    
    def get_facts(self, query=None, limit=10):
        if not query:
            return self.data["facts"][-limit:]
        
        # IMPROVED: Better keyword matching with synonyms
        query_lower = query.lower()
        relevant = []
        
        # Extract keywords and expand with common variations
        query_words = query_lower.split()
        expanded_keywords = set(query_words)
        
        # Add common variations
        keyword_map = {
            'favorite': ['favourite', 'fav', 'like', 'prefer', 'love'],
            'pizza': ['pizza', 'pie'],
            'food': ['food', 'eat', 'meal', 'dish'],
            'game': ['game', 'gaming', 'play'],
            'live': ['live', 'from', 'location'],
            'name': ['name', 'called']
        }
        
        for word in query_words:
            if word in keyword_map:
                expanded_keywords.update(keyword_map[word])
        
        for fact in self.data["facts"]:
            fact_lower = fact["fact"].lower()
            # Check if any expanded keyword matches
            if any(keyword in fact_lower for keyword in expanded_keywords):
                fact["access_count"] = fact.get("access_count", 0) + 1
                fact["last_accessed"] = datetime.now().isoformat()
                relevant.append(fact)
        
        self._save()
        return relevant[-limit:] if relevant else []
    
    def get_all_facts(self):
        return self.data["facts"]


class LLMBasedLearning(LearningEngine):
    """Learning using LLM analysis - V1"""
    
    def __init__(self, llm_handler):
        self.llm = llm_handler
    
    def extract_facts(self, text, context=None):
        """Use LLM to extract facts from conversation"""
        
        analysis_prompt = f"""Analyze this conversation and extract important personal information.

User said: "{text}"

Extract information about:
- Identity (name, age, location, occupation, education)
- Interests & hobbies
- Relationships (family, friends, pets)
- Events & experiences
- Preferences & opinions
- Goals & problems
- Daily routines

Format as JSON list with confidence scores:
[
  {{"fact": "User's name is Alex", "category": "identity", "confidence": 0.95}},
  {{"fact": "User enjoys gaming", "category": "interests", "confidence": 0.85}}
]

Rules:
- Only extract explicitly stated or strongly implied facts
- Confidence: 0.0-1.0 (only return if >0.7)
- Categories: identity, interests, relationships, events, preferences, goals, routines, other
- Empty list [] if nothing to extract

JSON only:"""
        
        try:
            response = self.llm.generate(analysis_prompt, use_search_context=False)
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            
            if json_match:
                facts = json.loads(json_match.group(0))
                # Filter by confidence
                return [f for f in facts if f.get('confidence', 0) >= 0.7]
            
        except Exception as e:
            print(f"[Learning Error]: {e}")
        
        return []


class PatternBasedLearning(LearningEngine):
    """Pattern recognition learning - V1 (fast, no LLM needed)"""
    
    def extract_facts(self, text, context=None):
        """Extract facts using improved pattern matching"""
        facts = []
        text_lower = text.lower()
        
        # Pattern: Name
        name_patterns = [
            (r"(?:my name is|i'm|i am|call me)\s+([A-Z][a-z]+)", "identity", 0.90),
            (r"(?:i'm|my name's)\s+([A-Z][a-z]+)", "identity", 0.85),
        ]
        
        # Pattern: Location
        location_patterns = [
            (r"(?:i live in|i'm from|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "identity", 0.88),
            (r"(?:based in|located in)\s+([A-Z][a-z]+)", "identity", 0.85),
        ]
        
        # Pattern: Interests (improved)
        interest_patterns = [
            (r"i (?:love|really like|enjoy|am into)\s+([a-z\s]{3,30})(?:\.|!|,|\s+and\s)", "interests", 0.85),
            (r"(?:big fan of|passionate about)\s+([a-z\s]{3,30})", "interests", 0.88),
        ]
        
        # Pattern: Preferences
        preference_patterns = [
            (r"i prefer\s+([^.!?]+?)(?:\s+over|\s+to)", "preferences", 0.85),
            (r"my favorite\s+([a-z]+)\s+is\s+([^.!?]+)", "preferences", 0.90),
        ]
        
        # Pattern: Goals/Plans
        goal_patterns = [
            (r"i (?:want to|plan to|hope to|trying to)\s+([^.!?]{5,50})", "goals", 0.80),
            (r"(?:my goal is|i'm working on)\s+([^.!?]+)", "goals", 0.85),
        ]
        
        all_patterns = (
            name_patterns + location_patterns + interest_patterns + 
            preference_patterns + goal_patterns
        )
        
        for pattern, category, confidence in all_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fact = match.group(0).strip()
                if len(fact) > 5 and len(fact.split()) < 15:  # Reasonable length
                    facts.append({
                        "fact": fact,
                        "category": category,
                        "confidence": confidence
                    })
        
        return facts


class SemanticContextRetriever(ContextRetriever):
    """Semantic search using embeddings - V1"""
    
    def __init__(self, persist_directory):
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB required for semantic search")
        
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name="jarvis_semantic_memory",
            embedding_function=self.embedding_function
        )
    
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
# MAIN MEMORY SYSTEM - Orchestrates all components
# ============================================================================

class ModularMemorySystem:
    """
    Main memory system that uses pluggable components.
    Easy to upgrade individual parts without breaking everything!
    """
    
    def __init__(self, data_dir="./jarvis_data", llm_handler=None, config=None):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        config = config or {}
        
        # Component 1: Storage Backend (easily swap to database later)
        self.storage = JSONMemoryBackend(
            os.path.join(data_dir, "memory_v2.json")
        )
        
        # Component 2: Learning Engines (can use multiple!)
        self.learning_engines = []
        
        if llm_handler:
            self.learning_engines.append(
                LLMBasedLearning(llm_handler)
            )
        
        # Always have pattern-based as fallback (fast, no LLM)
        self.learning_engines.append(
            PatternBasedLearning()
        )
        
        # Component 3: Context Retriever
        self.context_retriever = None
        if CHROMADB_AVAILABLE:
            try:
                self.context_retriever = SemanticContextRetriever(
                    os.path.join(data_dir, "semantic_db")
                )
            except Exception as e:
                print(f"⚠️ Semantic search unavailable: {e}")
        
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
        print(f"  - Semantic search: {'enabled' if self.context_retriever else 'disabled'}")
    
    def learn_from_conversation(self, user_message, assistant_response=None):
        """
        Learn from conversation using all available engines.
        Returns number of facts learned.
        """
        learned_count = 0
        
        # Try each learning engine
        for engine in self.learning_engines:
            try:
                facts = engine.extract_facts(user_message)
                
                for fact_data in facts:
                    fact = fact_data.get('fact', '')
                    category = fact_data.get('category', 'general')
                    confidence = fact_data.get('confidence', 0.8)
                    
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
        
        # Method 1: Semantic search (best, if available)
        if self.context_retriever:
            context = self.context_retriever.get_relevant_context(query, limit=5)
            if context:
                return self._format_context(context)
        
        # Method 2: Fallback to keyword search
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
        """
        Export all conversations in format ready for fine-tuning.
        Future-proofing for when you want to fine-tune!
        """
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
        print("  Ready for fine-tuning when you need it!")
        
        return filepath


# ============================================================================
# UPGRADE EXAMPLES (for future you!)
# ============================================================================

"""
FUTURE UPGRADES - Just swap out components:

1. Better Storage:
   class PostgreSQLMemoryBackend(MemoryBackend):
       # Store in real database instead of JSON
       
2. Advanced Learning:
   class TransformerBasedLearning(LearningEngine):
       # Use dedicated NER/entity extraction model
       
3. Cloud Sync:
   class CloudMemoryBackend(MemoryBackend):
       # Sync across devices
       
4. Graph-based Memory:
   class GraphContextRetriever(ContextRetriever):
       # Build knowledge graph of relationships
       
5. Fine-tuned Model:
   class FineTunedLearning(LearningEngine):
       # Use your own fine-tuned model for learning

Just implement the base class interface and plug it in!
No need to rewrite everything.
"""