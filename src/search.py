"""
Web search functionality using DuckDuckGo
"""

from duckduckgo_search import DDGS
from . import config
import time


class WebSearch:
    """Handles web search queries"""
    
    def __init__(self):
        self.search_keywords = config.SEARCH_KEYWORDS
        self.credible_domains = config.CREDIBLE_DOMAINS
        self.max_results = config.SEARCH_MAX_RESULTS
        self.timeout = config.SEARCH_TIMEOUT
    
    def needs_search(self, query):
        """Determine if query requires web search"""
        query_lower = query.lower()
        
        # Check for search keywords
        return any(keyword in query_lower for keyword in self.search_keywords)
    
    def search(self, query):
        """Perform web search and return formatted results"""
        try:
            ddgs = DDGS()
            
            # Perform search with timeout
            results = list(ddgs.text(
                query,
                max_results=self.max_results,
                safesearch='moderate'
            ))
            
            if not results:
                return "No search results found."
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                title = result.get('title', 'No title')
                snippet = result.get('body', 'No description')
                url = result.get('href', '')
                
                # Check if from credible source
                is_credible = any(domain in url for domain in self.credible_domains)
                credible_tag = " [CREDIBLE SOURCE]" if is_credible else ""
                
                formatted_results.append(
                    f"Result {i}{credible_tag}:\n"
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Description: {snippet}\n"
                )
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"Search error: {str(e)}\nSearch functionality unavailable."
    
    def search_with_retry(self, query, max_retries=3):
        """Search with retry logic"""
        for attempt in range(max_retries):
            try:
                result = self.search(query)
                if "error" not in result.lower():
                    return result
                
                if attempt < max_retries - 1:
                    time.sleep(config.SEARCH_DELAY)
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"Search failed after {max_retries} attempts: {str(e)}"
                time.sleep(config.SEARCH_DELAY)
        
        return "Search unavailable after multiple attempts."