"""
Unlimited web search - No API keys, No rate limits
Uses multiple search methods with fallbacks
"""

import warnings
warnings.filterwarnings("ignore")

from . import config
import time
import requests
from bs4 import BeautifulSoup
import random
import urllib.parse


class WebSearch:
    """Multi-source web search with unlimited usage"""
    
    def __init__(self):
        self.search_keywords = config.SEARCH_KEYWORDS
        self.credible_domains = config.CREDIBLE_DOMAINS
        self.max_results = config.SEARCH_MAX_RESULTS
        self.timeout = config.SEARCH_TIMEOUT
        
        # Rotating user agents to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101',
        ]
    
    def needs_search(self, query):
        """Determine if query requires web search"""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.search_keywords)
    
    def _get_headers(self):
        """Get randomized headers to avoid blocking"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def search(self, query):
        """Try multiple search methods until one works"""
        
        # Method 1: Google scraping (works most of the time)
        try:
            result = self._search_google(query)
            if result and "error" not in result.lower():
                return result
        except:
            pass
        
        # Method 2: Bing scraping (backup)
        try:
            result = self._search_bing(query)
            if result and "error" not in result.lower():
                return result
        except:
            pass
        
        # Method 3: Yahoo scraping (backup)
        try:
            result = self._search_yahoo(query)
            if result and "error" not in result.lower():
                return result
        except:
            pass
        
        # Method 4: DuckDuckGo HTML scraping (last resort)
        try:
            result = self._search_ddg_html(query)
            if result and "error" not in result.lower():
                return result
        except:
            pass
        
        return "All search methods failed. Please try again."
    
    def _search_google(self, query):
        """Scrape Google search results directly"""
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}&num={self.max_results}"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search result divs
            results = []
            for g in soup.find_all('div', class_='g'):
                # Title
                title_elem = g.find('h3')
                title = title_elem.text if title_elem else 'No title'
                
                # URL
                link_elem = g.find('a')
                url = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ''
                
                # Snippet
                snippet_elem = g.find('div', class_=['VwiC3b', 'yXK7lf'])
                snippet = snippet_elem.text if snippet_elem else 'No description'
                
                if title and url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
            
            if not results:
                return None
            
            return self._format_results(results[:self.max_results], "Google")
            
        except Exception as e:
            return None
    
    def _search_bing(self, query):
        """Scrape Bing search results"""
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://www.bing.com/search?q={encoded_query}&count={self.max_results}"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for li in soup.find_all('li', class_='b_algo'):
                # Title and URL
                h2 = li.find('h2')
                if not h2:
                    continue
                    
                link = h2.find('a')
                if not link:
                    continue
                
                title = link.text
                url = link.get('href', '')
                
                # Snippet
                snippet_elem = li.find('p') or li.find('div', class_='b_caption')
                snippet = snippet_elem.text if snippet_elem else 'No description'
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet
                })
            
            if not results:
                return None
            
            return self._format_results(results[:self.max_results], "Bing")
            
        except Exception as e:
            return None
    
    def _search_yahoo(self, query):
        """Scrape Yahoo search results"""
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://search.yahoo.com/search?p={encoded_query}&n={self.max_results}"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for div in soup.find_all('div', class_='dd'):
                # Title and URL
                title_elem = div.find('h3')
                if not title_elem:
                    continue
                
                link = title_elem.find('a')
                if not link:
                    continue
                
                title = link.text
                url = link.get('href', '')
                
                # Snippet
                snippet_elem = div.find('p', class_='fz-ms')
                snippet = snippet_elem.text if snippet_elem else 'No description'
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet
                })
            
            if not results:
                return None
            
            return self._format_results(results[:self.max_results], "Yahoo")
            
        except Exception as e:
            return None
    
    def _search_ddg_html(self, query):
        """Scrape DuckDuckGo HTML (no JavaScript needed)"""
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            response = requests.post(
                url,
                data={'q': query, 'b': '', 'kl': 'us-en'},
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for result in soup.find_all('div', class_='result'):
                # Title and URL
                title_elem = result.find('a', class_='result__a')
                if not title_elem:
                    continue
                
                title = title_elem.text
                url = title_elem.get('href', '')
                
                # Snippet
                snippet_elem = result.find('a', class_='result__snippet')
                snippet = snippet_elem.text if snippet_elem else 'No description'
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet
                })
            
            if not results:
                return None
            
            return self._format_results(results[:self.max_results], "DuckDuckGo")
            
        except Exception as e:
            return None
    
    def _format_results(self, results, source):
        """Format search results - clean and concise for LLM processing"""
        formatted = []
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            snippet = result.get('snippet', 'No description')
            url = result.get('url', '')
            
            # Just concatenate the info cleanly
            formatted.append(f"{title}. {snippet}")
        
        return "\n\n".join(formatted)
    
    def search_with_retry(self, query, max_retries=3):
        """Search with retry logic and delays"""
        for attempt in range(max_retries):
            try:
                result = self.search(query)
                if result and "error" not in result.lower():
                    return result
                
                if attempt < max_retries - 1:
                    # Random delay between retries (1-3 seconds)
                    time.sleep(random.uniform(1, 3))
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"Search failed after {max_retries} attempts: {str(e)}"
                time.sleep(random.uniform(1, 3))
        
        return "Search unavailable after multiple attempts."