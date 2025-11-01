import warnings
warnings.filterwarnings("ignore")

from . import config
import time
import requests
from bs4 import BeautifulSoup
import random
import urllib.parse
import json
import subprocess
import platform


class WebSearch:
    """Multi-source web search with unlimited usage - NO CONSOLE FLASH"""
    
    def __init__(self):
        self.search_keywords = config.SEARCH_KEYWORDS
        self.credible_domains = config.CREDIBLE_DOMAINS
        self.max_results = config.SEARCH_MAX_RESULTS
        self.timeout = config.SEARCH_TIMEOUT
        self.system = platform.system()
        
        # Rotating user agents to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
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
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
    
    def _get_creation_flags(self):
        """Get subprocess creation flags to hide console"""
        if self.system == "Windows":
            return subprocess.CREATE_NO_WINDOW
        return 0
    
    def _get_startup_info(self):
        """Get startup info to hide console on Windows"""
        if self.system != "Windows":
            return None
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo
    
    def search(self, query):
        """Try multiple search methods until one works"""
        
        # Method 1: DuckDuckGo HTML (most reliable, no blocking)
        try:
            result = self._search_ddg_html(query)
            if result and "error" not in result.lower() and len(result) > 50:
                return result
        except Exception as e:
            pass
        
        # Method 2: Google scraping
        try:
            result = self._search_google(query)
            if result and "error" not in result.lower() and len(result) > 50:
                return result
        except Exception as e:
            pass
        
        # Method 3: Bing scraping
        try:
            result = self._search_bing(query)
            if result and "error" not in result.lower() and len(result) > 50:
                return result
        except Exception as e:
            pass
        
        # Method 4: Brave Search (good for crypto/finance)
        try:
            result = self._search_brave(query)
            if result and "error" not in result.lower() and len(result) > 50:
                return result
        except Exception as e:
            pass
        
        return "Search temporarily unavailable. Please try again in a moment."
    
    def _search_ddg_html(self, query):
        """Scrape DuckDuckGo HTML (most reliable)"""
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
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                # Snippet
                snippet_elem = result.find('a', class_='result__snippet')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                
                if title and snippet:
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
    
    def _search_google(self, query):
        """Scrape Google search results"""
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
            
            results = []
            
            # Try multiple selector patterns
            search_divs = soup.find_all('div', class_='g')
            if not search_divs:
                search_divs = soup.find_all('div', attrs={'data-sokoban-container': True})
            
            for g in search_divs:
                # Title
                title_elem = g.find('h3')
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # URL
                link_elem = g.find('a')
                url = link_elem.get('href', '') if link_elem else ''
                
                # Snippet - try multiple patterns
                snippet = ''
                snippet_elem = g.find('div', class_=['VwiC3b', 'yXK7lf', 'lEBKkf'])
                if not snippet_elem:
                    snippet_elem = g.find('span', class_=['aCOpRe', 'st'])
                if not snippet_elem:
                    # Look for any div with text content
                    for div in g.find_all('div'):
                        text = div.get_text(strip=True)
                        if len(text) > 50 and title not in text:
                            snippet = text
                            break
                else:
                    snippet = snippet_elem.get_text(strip=True)
                
                if title and snippet and len(snippet) > 20:
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
                
                title = link.get_text(strip=True)
                url = link.get('href', '')
                
                # Snippet
                snippet = ''
                snippet_elem = li.find('p')
                if not snippet_elem:
                    snippet_elem = li.find('div', class_='b_caption')
                if snippet_elem:
                    snippet = snippet_elem.get_text(strip=True)
                
                if title and snippet and len(snippet) > 20:
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
    
    def _search_brave(self, query):
        """Scrape Brave Search (good for crypto)"""
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://search.brave.com/search?q={encoded_query}"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            # Brave uses different selectors
            for result_div in soup.find_all('div', class_=['snippet', 'fdb']):
                # Title
                title_elem = result_div.find(['h2', 'h3', 'a'])
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # URL
                link_elem = result_div.find('a')
                url = link_elem.get('href', '') if link_elem else ''
                
                # Snippet
                snippet = ''
                snippet_elem = result_div.find('p', class_='snippet-description')
                if not snippet_elem:
                    for p in result_div.find_all('p'):
                        text = p.get_text(strip=True)
                        if len(text) > 20:
                            snippet = text
                            break
                else:
                    snippet = snippet_elem.get_text(strip=True)
                
                if title and snippet and len(snippet) > 20:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
            
            if not results:
                return None
            
            return self._format_results(results[:self.max_results], "Brave")
            
        except Exception as e:
            return None
    
    def _format_results(self, results, source):
        """Format search results - clean and concise for LLM processing"""
        if not results:
            return None
        
        formatted = []
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            snippet = result.get('snippet', 'No description')
            
            # Clean up the snippet
            snippet = snippet.replace('\n', ' ').strip()
            
            # For crypto queries, prioritize results with numbers/prices
            if any(word in title.lower() or word in snippet.lower() 
                   for word in ['bitcoin', 'btc', 'crypto', 'price', '$']):
                formatted.insert(0, f"{title}. {snippet}")
            else:
                formatted.append(f"{title}. {snippet}")
        
        return "\n\n".join(formatted)
    
    def search_with_retry(self, query, max_retries=3):
        """Search with retry logic and delays"""
        for attempt in range(max_retries):
            try:
                result = self.search(query)
                if result and "error" not in result.lower() and len(result) > 50:
                    return result
                
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(1, 2))
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"Search failed after {max_retries} attempts."
                time.sleep(random.uniform(1, 2))
        
        return "Search unavailable after multiple attempts."