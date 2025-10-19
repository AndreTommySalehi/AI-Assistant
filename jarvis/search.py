"""
Web search functionality using DuckDuckGo
"""

import time
from duckduckgo_search import DDGS
from . import config


class WebSearch:
    """Handles web searches for current information"""
    
    def __init__(self):
        self.available = True
        print("Web search enabled")
    
    def needs_search(self, query):
        """Determine if a query requires web search"""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in config.SEARCH_KEYWORDS)
    
    def search(self, query):
        """Perform web search and return formatted results"""
        if not self.available:
            return "Web search is currently unavailable"
        
        time.sleep(config.SEARCH_DELAY)
        
        try:
            ddgs = DDGS(timeout=config.SEARCH_TIMEOUT)
            results = []
            query_lower = query.lower()
            
            # Enhanced weather search
            if 'weather' in query_lower:
                results.extend(self._search_weather(ddgs, query))
            
            # Government/political searches
            if 'president' in query_lower or 'government' in query_lower:
                results.extend(self._search_government(ddgs, query))
            
            # Regular search
            results.extend(self._regular_search(ddgs, query))
            
            # News search as backup
            if len(results) < 3:
                results.extend(self._search_news(ddgs, query))
            
            if not results:
                return "No search results found. Try rephrasing your question."
            
            # Sort by credibility and limit results
            results.sort(key=lambda x: (not x.get('credible', False), 0))
            results = results[:5]
            
            return self._format_results(results)
                
        except Exception as e:
            print(f"   Search exception: {str(e)}")
            return f"Search error: {str(e)}"
    
    def _search_weather(self, ddgs, query):
        """Search for weather information"""
        results = []
        try:
            print("   Searching for weather information...")
            weather_results = ddgs.text(
                f"{query} weather forecast temperature",
                region='wt-wt',
                safesearch='off',
                max_results=5
            )
            for result in weather_results:
                results.append({
                    'title': result.get('title', 'No title'),
                    'body': result.get('body', 'No description'),
                    'url': result.get('href', result.get('url', '')),
                    'credible': True
                })
        except Exception as e:
            print(f"   Weather search failed: {e}")
        return results
    
    def _search_government(self, ddgs, query):
        """Search government sources"""
        results = []
        try:
            print("   Searching government sources...")
            gov_results = ddgs.text(
                f"site:usa.gov {query}",
                region='wt-wt',
                safesearch='off',
                max_results=2
            )
            for result in gov_results:
                results.append({
                    'title': result.get('title', 'No title'),
                    'body': result.get('body', 'No description'),
                    'url': result.get('href', result.get('url', '')),
                    'credible': True
                })
        except:
            pass
        return results
    
    def _regular_search(self, ddgs, query):
        """Perform regular web search"""
        results = []
        try:
            print("   Searching DuckDuckGo...")
            search_results = ddgs.text(
                query,
                region='wt-wt',
                safesearch='off',
                max_results=config.SEARCH_MAX_RESULTS
            )
            
            for result in search_results:
                url = result.get('href', result.get('url', ''))
                is_credible = any(domain in url for domain in config.CREDIBLE_DOMAINS)
                
                results.append({
                    'title': result.get('title', 'No title'),
                    'body': result.get('body', 'No description'),
                    'url': url,
                    'credible': is_credible
                })
            
            if results:
                print(f"   Found {len(results)} search results")
                
        except Exception as e:
            print(f"   Search failed: {e}")
        return results
    
    def _search_news(self, ddgs, query):
        """Search news sources"""
        results = []
        try:
            print("   Trying news search...")
            news_results = ddgs.news(query, max_results=5)
            
            for result in news_results:
                url = result.get('url', result.get('link', ''))
                is_credible = any(domain in url for domain in config.CREDIBLE_DOMAINS)
                
                results.append({
                    'title': result.get('title', 'No title'),
                    'body': result.get('body', result.get('description', 'No description')),
                    'url': url,
                    'credible': is_credible
                })
            
            if results:
                print(f"   Found {len(results)} total results")
                
        except Exception as e:
            print(f"   News search failed: {e}")
        return results
    
    def _format_results(self, results):
        """Format search results for display"""
        formatted_results = []
        for i, result in enumerate(results, 1):
            credible_tag = " [VERIFIED]" if result.get('credible') else ""
            formatted_results.append(
                f"[Result {i}{credible_tag}]\n"
                f"Title: {result['title']}\n"
                f"Information: {result['body']}\n"
                f"URL: {result['url']}"
            )
        return "\n\n".join(formatted_results)