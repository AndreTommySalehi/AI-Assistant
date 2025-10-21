"""
News Aggregator - Reputable, non-biased sources only
Categorized daily news summary
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import random
import time


class NewsAggregator:
    """Fetch news from reputable, fact-based sources"""
    
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
                summary[category] = headlines[:8]  # Top 8 per category (more stories)
                print(f"✓ ({len(headlines)} stories)")
            except Exception as e:
                print(f"✗ (failed)")
                summary[category] = []
        
        return summary
    
    def _fetch_category(self, category):
        """Fetch headlines from a specific category"""
        headlines = []
        
        # Try multiple sources for redundancy
        for source_url in self.sources[category]:
            try:
                response = requests.get(
                    source_url,
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract headlines (different for each site)
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
                    
                    # Break after first successful source
                    if headlines:
                        break
                
                time.sleep(0.5)  # Be polite
                
            except Exception as e:
                continue
        
        return list(set(headlines))  # Remove duplicates
    
    def _parse_reuters(self, soup):
        """Parse Reuters headlines"""
        headlines = []
        for article in soup.find_all(['h3', 'h2'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_ap(self, soup):
        """Parse AP News headlines"""
        headlines = []
        for article in soup.find_all('a', class_=['Component-headline-0-2-116', 'CardHeadline'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_bbc(self, soup):
        """Parse BBC headlines"""
        headlines = []
        for article in soup.find_all(['h3', 'h2'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20 and not text.startswith('BBC'):
                headlines.append(text)
        return headlines
    
    def _parse_npr(self, soup):
        """Parse NPR headlines"""
        headlines = []
        for article in soup.find_all('h2', class_='title', limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_ars(self, soup):
        """Parse Ars Technica headlines"""
        headlines = []
        for article in soup.find_all('h2', limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_verge(self, soup):
        """Parse The Verge headlines"""
        headlines = []
        for article in soup.find_all(['h2', 'h3'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_techcrunch(self, soup):
        """Parse TechCrunch headlines"""
        headlines = []
        for article in soup.find_all('h2', class_='wp-block-tc23-title', limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_bloomberg(self, soup):
        """Parse Bloomberg headlines"""
        headlines = []
        for article in soup.find_all(['h3', 'h2'], limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def _parse_wsj(self, soup):
        """Parse WSJ headlines"""
        headlines = []
        for article in soup.find_all('h2', limit=10):
            text = article.get_text().strip()
            if text and len(text) > 20:
                headlines.append(text)
        return headlines
    
    def format_summary(self, summary):
        """Format the news summary for display"""
        output = [f"\nDaily News Summary - {summary['date']}\n"]
        output.append("=" * 60)
        
        categories = {
            'general': '🌍 General News',
            'tech': '💻 Technology',
            'business': '📈 Business & Markets',
            'science': '🔬 Science'
        }
        
        for category, title in categories.items():
            headlines = summary.get(category, [])
            if headlines:
                output.append(f"\n{title}:")
                for i, headline in enumerate(headlines, 1):
                    output.append(f"  {i}. {headline}")
            else:
                output.append(f"\n{title}: (No stories available)")
        
        output.append("\n" + "=" * 60)
        output.append("Sources: Reuters, AP News, BBC, NPR, Ars Technica, The Verge, Bloomberg")
        
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


def test_news():
    """Test the news aggregator"""
    aggregator = NewsAggregator()
    summary = aggregator.get_daily_summary()
    print(aggregator.format_summary(summary))


if __name__ == "__main__":
    test_news()