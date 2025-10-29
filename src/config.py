# GPT-OSS Configuration
USE_GPT_OSS = False  # Set to True if you have GPT-OSS server running
GPT_OSS_MODEL = "openai/gpt-oss-20b"
GPT_OSS_MAX_TOKENS = 512
GPT_OSS_PRIORITY = False

# Ollama Models
DEFAULT_MODEL = "qwen2.5:14b"
SECONDARY_MODEL = None

# A/B Testing - Now enabled by default
ENABLE_AB_TESTING = True
CONFIDENCE_THRESHOLD = 30  # Minimum confidence difference to prefer one model

# Search Configuration
SEARCH_TIMEOUT = 30
SEARCH_MAX_RESULTS = 5
SEARCH_DELAY = 1

# Credible source domains
CREDIBLE_DOMAINS = [
    'weather.com', 'accuweather.com', 'noaa.gov', 'weather.gov',
    'congress.gov', 'usa.gov', 'whitehouse.gov',
    'wikipedia.org', 'britannica.com',
    'reuters.com', 'apnews.com', 'bbc.com', 'npr.org',
    'cdc.gov', 'nih.gov', 'who.int'
]

# Search trigger keywords - expanded
SEARCH_KEYWORDS = [
    # Time-based
    'weather', 'news', 'today', 'now', 'current', 'latest',
    'recent', 'update', 'forecast', 'right now', 'this week',
    
    # People/Politics
    'president', 'who is', 'elected', 'winner', 'election',
    
    # Finance
    'stock', 'price', 'cost', 'worth', 'bitcoin', 'crypto',
    'trading', 'market', 'dollar', 'USD', 'exchange rate',
    
    # Weather specific
    'temperature', 'celsius', 'fahrenheit', 'rain', 'sunny',
    'cloudy', 'storm', 'snow', 'forecast',
    
    # General search triggers
    'what is happening', 'happening now', 'score', 'result',
    '2024', '2025', 'search for', 'look up', 'find out'
]

# Model generation options
MODEL_OPTIONS = {
    'temperature': 0.7,  # 0=deterministic, 1=creative
    'top_p': 0.9,
    'top_k': 40,
}