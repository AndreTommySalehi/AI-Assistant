import json
import os
from datetime import datetime, timedelta

# Try to import ChromaDB for RAG
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️  ChromaDB not installed. RAG disabled. Install with: pip install chromadb sentence-transformers")


class MemorySystem:
    """Complete memory system combining all three approaches"""
    
    def __init__(self, data_dir="./jarvis_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize all three systems
        self.persistent = PersistentMemory(os.path.join(data_dir, "memory.json"))
        self.search_cache = SearchCache(os.path.join(data_dir, "search_cache.json"))
        
        # Initialize RAG if available
        self.rag = None
        if CHROMADB_AVAILABLE:
            try:
                self.rag = SimpleRAG(os.path.join(data_dir, "rag_db"))
                print("✓ RAG system initialized")
            except Exception as e:
                print(f"⚠️  RAG initialization failed: {e}")
    
    def remember_fact(self, fact, category="general"):
        """Store a fact the user told you"""
        self.persistent.remember_fact(fact, category)
    
    def get_cached_search(self, query):
        """Check if we have a cached search result"""
        return self.search_cache.get(query)
    
    def cache_search(self, query, result):
        """Cache a search result"""
        self.search_cache.set(query, result)
    
    def add_document(self, text, source="user"):
        """Add document to RAG"""
        if self.rag:
            self.rag.add_document(text, metadata={"source": source})
            return True
        return False
    
    def add_file(self, filepath):
        """Add file to RAG"""
        if self.rag:
            return self.rag.add_file(filepath)
        return False
    
    def get_context(self, query):
        """Get ALL relevant context for a query"""
        context_parts = []
        
        # 1. Get remembered facts
        facts = self.persistent.recall_facts(query, limit=3)
        if facts:
            context_parts.append("Things you've told me before:")
            for fact in facts:
                context_parts.append(f"  - {fact['fact']}")
        
        # 2. Get RAG documents
        if self.rag:
            rag_results = self.rag.search(query, n_results=2)
            if rag_results:
                context_parts.append("\nFrom my knowledge base:")
                context_parts.append(rag_results)
        
        return "\n".join(context_parts) if context_parts else ""
    
    def save_conversation(self, conversation_history):
        """Save conversation at end of session"""
        self.persistent.save_conversation(conversation_history)
    
    def get_stats(self):
        """Get memory statistics"""
        stats = {
            "facts_remembered": len(self.persistent.memory.get("facts", [])),
            "cached_searches": len(self.search_cache.cache),
            "conversations_saved": len(self.persistent.memory.get("conversations", [])),
        }
        
        if self.rag:
            stats["documents_stored"] = self.rag.collection.count()
        
        return stats


class PersistentMemory:
    """Persistent memory - remembers facts across sessions"""
    
    def __init__(self, memory_file):
        self.memory_file = memory_file
        self.memory = self._load_memory()
    
    def _load_memory(self):
        """Load memory from file"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except:
                return {"facts": [], "conversations": []}
        return {"facts": [], "conversations": []}
    
    def save_memory(self):
        """Save memory to file"""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)
    
    def remember_fact(self, fact, category="general"):
        """Store a fact"""
        self.memory["facts"].append({
            "fact": fact,
            "category": category,
            "timestamp": datetime.now().isoformat()
        })
        self.save_memory()
    
    def recall_facts(self, query=None, limit=5):
        """Retrieve relevant facts"""
        if not query:
            return self.memory["facts"][-limit:]
        
        # Simple keyword matching
        relevant = []
        query_lower = query.lower()
        for fact in self.memory["facts"]:
            if any(word in fact["fact"].lower() for word in query_lower.split()):
                relevant.append(fact)
        
        return relevant[-limit:]
    
    def save_conversation(self, conversation_history):
        """Save current conversation"""
        self.memory["conversations"].append({
            "timestamp": datetime.now().isoformat(),
            "messages": conversation_history[-20:]
        })
        
        # Keep only last 10 conversations
        if len(self.memory["conversations"]) > 10:
            self.memory["conversations"] = self.memory["conversations"][-10:]
        
        self.save_memory()


class SearchCache:
    """Cache search results"""
    
    def __init__(self, cache_file, ttl_hours=24):
        self.cache_file = cache_file
        self.ttl_hours = ttl_hours
        self.cache = self._load_cache()
    
    def _load_cache(self):
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def _is_expired(self, timestamp):
        """Check if cached result is expired"""
        cached_time = datetime.fromisoformat(timestamp)
        return datetime.now() - cached_time > timedelta(hours=self.ttl_hours)
    
    def get(self, query):
        """Get cached search result"""
        query_key = query.lower().strip()
        
        if query_key in self.cache:
            entry = self.cache[query_key]
            
            if not self._is_expired(entry['timestamp']):
                return entry['result']
            else:
                del self.cache[query_key]
                self._save_cache()
        
        return None
    
    def set(self, query, result):
        """Cache a search result"""
        query_key = query.lower().strip()
        
        self.cache[query_key] = {
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        # Keep max 100 entries
        if len(self.cache) > 100:
            self._clean_old_entries()
        
        self._save_cache()
    
    def _clean_old_entries(self):
        """Remove oldest entries"""
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1]['timestamp']
        )
        self.cache = dict(sorted_entries[-50:])


class SimpleRAG:
    """Document storage and retrieval using ChromaDB"""
    
    def __init__(self, persist_directory):
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.collection = self.client.get_or_create_collection(
            name="jarvis_knowledge",
            embedding_function=self.embedding_function
        )
    
    def add_document(self, text, doc_id=None, metadata=None):
        """Add document to knowledge base"""
        if doc_id is None:
            doc_id = f"doc_{self.collection.count() + 1}"
        
        if metadata is None:
            metadata = {"source": "user", "type": "text"}
        
        chunks = self._chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            self.collection.add(
                documents=[chunk],
                ids=[f"{doc_id}_chunk_{i}"],
                metadatas=[metadata]
            )
    
    def _chunk_text(self, text, chunk_size=500):
        """Split text into chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks if chunks else [text]
    
    def search(self, query, n_results=2):
        """Search for relevant documents"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results['documents'][0]:
                return ""
            
            context = ""
            for doc in results['documents'][0]:
                context += f"{doc}\n\n"
            
            return context.strip()
        except:
            return ""
    
    def add_file(self, filepath):
        """Add text file to knowledge base"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            
            self.add_document(
                text=text,
                doc_id=filepath,
                metadata={"source": filepath, "type": "file"}
            )
            return True
        except Exception as e:
            print(f"Error adding file: {e}")
            return False