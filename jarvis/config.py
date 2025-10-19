"""
Configuration settings for Jarvis AI Assistant
"""

# Model Configuration
DEFAULT_MODEL = "llama3.2"  # Change to "llama3.1" or "mistral" for better results

# Search Configuration
SEARCH_TIMEOUT = 30
SEARCH_MAX_RESULTS = 7
SEARCH_DELAY = 1  # Delay between searches to avoid rate limiting

# Credible domains for prioritizing search results
CREDIBLE_DOMAINS = [
    'weather.com', 'accuweather.com', 'noaa.gov', 'weather.gov',
    'congress.gov', 'usa.gov',
    'wikipedia.org', 'britannica.com',
    'reuters.com', 'apnews.com', 'bbc.com', 'npr.org',
    'cdc.gov', 'nih.gov', 'who.int'
]

# Keywords that trigger web search
SEARCH_KEYWORDS = [
    'weather', 'news', 'today', 'now', 'current', 'latest',
    'recent', 'president', 'what is happening', 'who is',
    'stock', 'price', 'score', 'election', 'update', 'forecast',
    'temperature', 'celsius', 'fahrenheit', 'rain', 'sunny'
]

# Ollama Model Settings
MODEL_OPTIONS = {
    'temperature': 0.7,  # Higher = more creative, Lower = more factual
    'top_p': 0.9,
    'top_k': 40,
}