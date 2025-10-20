"""
Configuration with GPT-OSS (HuggingFace) support
"""

# Ollama Models
DEFAULT_MODEL = "llama3.1:8b"  # Primary Ollama model
SECONDARY_MODEL = "mistral:7b"  # Secondary for comparison

# GPT-OSS Configuration (HuggingFace)
USE_GPT_OSS = True  # Set to True to use GPT-OSS
GPT_OSS_MODEL = "openai/gpt-oss-20b"  # or "openai/gpt-oss-120b" (needs more RAM)
GPT_OSS_MAX_TOKENS = 512  # Max response length

# A/B Testing
ENABLE_AB_TESTING = True  # Compare all models - MUST BE TRUE FOR GPT-OSS
CONFIDENCE_THRESHOLD = 50  # Lower threshold so models compete fairly

# Search Configuration
SEARCH_TIMEOUT = 30
SEARCH_MAX_RESULTS = 7
SEARCH_DELAY = 1

# Credible source domains
CREDIBLE_DOMAINS = [
    'weather.com', 'accuweather.com', 'noaa.gov', 'weather.gov',
    'congress.gov', 'usa.gov', 'whitehouse.gov',
    'wikipedia.org', 'britannica.com',
    'reuters.com', 'apnews.com', 'bbc.com', 'npr.org',
    'cdc.gov', 'nih.gov', 'who.int'
]

# Search trigger keywords
SEARCH_KEYWORDS = [
    'weather', 'news', 'today', 'now', 'current', 'latest',
    'recent', 'president', 'what is happening', 'who is',
    'stock', 'price', 'score', 'election', 'update', 'forecast',
    'temperature', 'celsius', 'fahrenheit', 'rain', 'sunny',
    '2024', '2025', 'bitcoin', 'crypto', 'cost', 'worth',
    'trading at', 'right now'
]

# Model generation options
MODEL_OPTIONS = {
    'temperature': 0.7,  # 0=deterministic, 1=creative
    'top_p': 0.9,
    'top_k': 40,
}