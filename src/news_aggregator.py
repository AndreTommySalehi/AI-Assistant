import requests
from bs4 import BeautifulSoup
from datetime import datetime
import random
import time
import re


class NewsAggregator:
    """Fetch news from reputable, fact-based sources with deep-dive capability"""
    
    def __init__(self):
        # REPUTABLE NEWS SOURCES (Non-biased, fact-based journalism)
        self.sources = {
            'general': [
                'https://www.reuters.com',
                'https://apnews.com',
                'https://www.bbc.com/news',
                'https://www.npr.org/sections/news',
            ],
            'tech': [
                'https://arstechnica.com',
                'https://www.theverge.com',
                'https://techcrunch.com',
            ],
            'business': [
                'https://www.reuters.com/business',
                'https://www.bloomberg.com',
                'https://www.wsj.com',
            ],
            'science': [
                'https://www.sciencedaily.com',
                'https://www.nature.com/news',
            ]
        }
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        ]
        
        # Store the last news summary with indexed topics
        self.last_summary = None
        self.indexed_topics = {}
    
    def _get_headers(self):
        """Random user agent to avoid blocking"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    def get_daily_summary(self):
        """Get today's news summary from all categories"""
        today = datetime.now().strftime("%B %d, %Y")
        
        summary = {
            'date': today,
            'general': [],
            'tech': [],
            'business': [],
            'science': []
        }
        
        print("Fetching news from reputable sources...")
        
        # Fetch from each category
        for category in ['general', 'tech', 'business', 'science']:
            print(f"   - {category.capitalize()}...", end=" ", flush=True)
            try:
                headlines = self._fetch_category(category)
                summary[category] = headlines[:8]  # Top 8 per category
                print(f"✓ ({len(headlines)} stories)")
            except Exception as e:
                print(f"✗ (failed)")
                summary[category] = []
        
        # Store and index topics
        self.last_summary = summary
        self._index_topics(summary)
        
        return summary
    
    def _index_topics(self, summary):
        """Index all topics with numbers for easy reference"""
        self.indexed_topics = {}
        topic_num = 1
        
        for category in ['general', 'tech', 'business', 'science']:
            for headline in summary.get(category, []):
                self.indexed_topics[topic_num] = {
                    'headline': headline,
                    'category': category
                }
                topic_num += 1
    
    def get_topic_details(self, topic_identifier):
        """
        Get detailed information about a specific topic
        
        Args:
            topic_identifier: Can be a number (1-32) or keywords from the headline
        
        Returns:
            Detailed information about the topic, or None if not found
        """
        # Check if it's a number
        if isinstance(topic_identifier, int) or (isinstance(topic_identifier, str) and topic_identifier.isdigit()):
            topic_num = int(topic_identifier)
            if topic_num in self.indexed_topics:
                topic = self.indexed_topics[topic_num]
                return self._fetch_topic_details(topic['headline'], topic['category'])
        
        # Otherwise, search by keywords
        topic_lower = str(topic_identifier).lower()
        best_match = None
        best_score = 0
        
        for num, topic in self.indexed_topics.items():
            headline_lower = topic['headline'].lower()
            # Count matching words
            words = topic_lower.split()
            score = sum(1 for word in words if len(word) > 3 and word in headline_lower)
            
            if score > best_score:
                best_score = score
                best_match = topic
        
        if best_match and best_score > 0:
            return self._fetch_topic_details(best_match['headline'], best_match['category'])
        
        return None
    
    def _fetch_topic_details(self, headline, category):
        """Fetch detailed information about a specific topic"""
        print(f"\nSearching for more details on: {headline[:60]}...")
        
        # Use the headline as search query
        search_query = headline.replace(' ', '+')
        details = {
            'headline': headline,
            'category': category,
            'articles': []
        }
        
        # Try to fetch multiple articles about this topic
        sources_to_try = self.sources[category][:2]  # Try first 2 sources
        
        for source_url in sources_to_try:
            try:
                # For now, we'll use web search to find related articles
                # In production, you'd want to use the actual article URLs
                response = requests.get(
                    source_url,
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find articles mentioning key terms from headline
                    key_terms = self._extract_key_terms(headline)
                    
                    # Parse based on source
                    if 'reuters.com' in source_url:
                        articles = self._find_related_reuters(soup, key_terms)
                    elif 'apnews.com' in source_url:
                        articles = self._find_related_ap(soup, key_terms)
                    elif 'bbc.com' in source_url:
                        articles = self._find_related_bbc(soup, key_terms)
                    elif 'arstechnica.com' in source_url:
                        articles = self._find_related_ars(soup, key_terms)
                    elif 'theverge.com' in source_url:
                        articles = self._find_related_verge(soup, key_terms)
                    else:
                        articles = []
                    
                    details['articles'].extend(articles)
                    
                    if len(details['articles']) >= 3:
                        break
                
                time.sleep(0.5)
                
            except Exception as e:
                continue
        
        return details if details['articles'] else None
    
    def _extract_key_terms(self, headline):
        """Extract important keywords from headline"""
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been'}
        
        words = re.findall(r'\w+', headline.lower())
        key_terms = [w for w in words if len(w) > 3 and w not in stopwords]
        return key_terms[:5]  # Top 5 key terms
    
    def _find_related_reuters(self, soup, key_terms):
        """Find related articles on Reuters"""
        articles = []
        for article in soup.find_all(['article', 'div'], limit=10):
            text_content = article.get_text().lower()
            
            # Check if article mentions key terms
            matches = sum(1 for term in key_terms if term in text_content)
            if matches >= 2:
                title_elem = article.find(['h3', 'h2', 'h4'])
                desc_elem = article.find('p')
                
                if title_elem:
                    articles.append({
                        'title': title_elem.get_text().strip(),
                        'description': desc_elem.get_text().strip() if desc_elem else '',
                        'source': 'Reuters'
                    })
        
        return articles[:3]
    
    def _find_related_ap(self, soup, key_terms):
        """Find related articles on AP News"""
        articles = []
        for article in soup.find_all('div', class_='PagePromo', limit=10):
            text_content = article.get_text().lower()
            matches = sum(1 for term in key_terms if term in text_content)
            
            if matches >= 2:
                title_elem = article.find(['h3', 'h2'])
                desc_elem = article.find('p')
                
                if title_elem:
                    articles.append({
                        'title': title_elem.get_text().strip(),
                        'description': desc_elem.get_text().strip() if desc_elem else '',
                        'source': 'AP News'
                    })
        
        return articles[:3]
    
    def _find_related_bbc(self, soup, key_terms):
        """Find related articles on BBC"""
        articles = []
        for article in soup.find_all(['article', 'div'], limit=10):
            text_content = article.get_text().lower()
            matches = sum(1 for term in key_terms if term in text_content)
            
            if matches >= 2:
                title_elem = article.find(['h3', 'h2'])
                desc_elem = article.find('p')
                
                if title_elem:
                    articles.append({
                        'title': title_elem.get_text().strip(),
                        'description': desc_elem.get_text().strip() if desc_elem else '',
                        'source': 'BBC'
                    })
        
        return articles[:3]
    
    def _find_related_ars(self, soup, key_terms):
        """Find related articles on Ars Technica"""
        articles = []
        for article in soup.find_all(['article', 'div'], limit=10):
            text_content = article.get_text().lower()
            matches = sum(1 for term in key_terms if term in text_content)
            
            if matches >= 2:
                title_elem = article.find(['h2', 'h3'])
                desc_elem = article.find('p', class_='excerpt')
                
                if title_elem:
                    articles.append({
                        'title': title_elem.get_text().strip(),
                        'description': desc_elem.get_text().strip() if desc_elem else '',
                        'source': 'Ars Technica'
                    })
        
        return articles[:3]
    
    def _find_related_verge(self, soup, key_terms):
        """Find related articles on The Verge"""
        articles = []
        for article in soup.find_all(['article', 'div'], limit=10):
            text_content = article.get_text().lower()
            matches = sum(1 for term in key_terms if term in text_content)
            
            if matches >= 2:
                title_elem = article.find(['h2', 'h3'])
                desc_elem = article.find('p')
                
                if title_elem:
                    articles.append({
                        'title': title_elem.get_text().strip(),
                        'description': desc_elem.get_text().strip() if desc_elem else '',
                        'source': 'The Verge'
                    })
        
        return articles[:3]
    
    def _fetch_category(self, category):
        """Fetch headlines from a specific category"""
        headlines = []
        
        for source_url in self.sources[category]:
            try:
                response = requests.get(
                    source_url,
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    if 'reuters.com' in source_url:
                        headlines.extend(self._parse_reuters(soup))
                    elif 'apnews.com' in source_url:
                        headlines.extend(self._parse_ap(soup))
                    elif 'bbc.com' in source_url:
                        headlines.extend(self._parse_bbc(soup))
                    elif 'npr.org' in source_url:
                        headlines.extend(self._parse_npr(soup))
                    elif 'arstechnica.com' in source_url:
                        headlines.extend(self._parse_ars(soup))
                    elif 'theverge.com' in source_url:
                        headlines.extend(self._parse_verge(soup))
                    elif 'techcrunch.com' in source_url:
                        headlines.extend(self._parse_techcrunch(soup))
                    elif 'bloomberg.com' in source_url:
                        headlines.extend(self._parse_bloomberg(soup))
                    elif 'wsj.com' in source_url:
                        headlines.extend(self._parse_wsj(soup))
                    
                    if headlines:
                        break
                
                time.sleep(0.5)
                
            except Exception as e:
                continue
        
        return list(set(headlines))
    
    # [Keep all the existing _parse_* methods from original code]
    def _parse_reuters(self, soup):
        headlines = []
        for article in soup.find_all(['h3', 'h2'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_ap(self, soup):
        headlines = []
        for article in soup.find_all('a', class_=['Component-headline-0-2-116', 'CardHeadline'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_bbc(self, soup):
        headlines = []
        for article in soup.find_all(['h3', 'h2'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20 and not text.startswith('BBC'):
                headlines.append(text)
        return headlines
    
    def _parse_npr(self, soup):
        headlines = []
        for article in soup.find_all('h2', class_='title', limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_ars(self, soup):
        headlines = []
        for article in soup.find_all('h2', limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_verge(self, soup):
        headlines = []
        for article in soup.find_all(['h2', 'h3'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_techcrunch(self, soup):
        headlines = []
        for article in soup.find_all('h2', class_='wp-block-tc23-title', limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_bloomberg(self, soup):
        headlines = []
        for article in soup.find_all(['h3', 'h2'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_wsj(self, soup):
        headlines = []
        for article in soup.find_all('h2', limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def format_summary(self, summary, show_numbers=True):
        """Format the news summary for display with optional numbering"""
        output = [f"\nDaily News Summary - {summary['date']}\n"]
        output.append("=" * 60)
        
        if show_numbers:
            output.append("\n(Type 'more [number]' or 'more [topic]' for details)")
        
        categories = {
            'general': '🌍 General News',
            'tech': '💻 Technology',
            'business': '📈 Business & Markets',
            'science': '🔬 Science'
        }
        
        topic_num = 1
        for category, title in categories.items():
            headlines = summary.get(category, [])
            if headlines:
                output.append(f"\n{title}:")
                for headline in headlines:
                    if show_numbers:
                        output.append(f"  [{topic_num}] {headline}")
                        topic_num += 1
                    else:
                        output.append(f"  • {headline}")
            else:
                output.append(f"\n{title}: (No stories available)")
        
        output.append("\n" + "=" * 60)
        output.append("Sources: Reuters, AP News, BBC, NPR, Ars Technica, The Verge, Bloomberg")
        
        return "\n".join(output)
    
    def format_topic_details(self, details):
        """Format detailed topic information"""
        if not details:
            return "Sorry, I couldn't find more details on that topic."
        
        output = [f"\n{'='*60}"]
        output.append(f"DEEP DIVE: {details['headline']}")
        output.append(f"Category: {details['category'].upper()}")
        output.append(f"{'='*60}\n")
        
        if details['articles']:
            output.append("Related Coverage:\n")
            for i, article in enumerate(details['articles'], 1):
                output.append(f"{i}. {article['title']}")
                output.append(f"   Source: {article['source']}")
                if article['description']:
                    output.append(f"   {article['description'][:200]}...")
                output.append("")
        else:
            output.append("No additional details available at this time.")
        
        output.append(f"{'='*60}")
        return "\n".join(output)
    
    def get_summary_for_llm(self, summary):
        """Format news for LLM processing"""
        lines = []
        
        for category in ['general', 'tech', 'business', 'science']:
            headlines = summary.get(category, [])
            if headlines:
                lines.append(f"\n{category.upper()} NEWS:")
                for headline in headlines:
                    lines.append(f"- {headline}")
        
        return "\n".join(lines)