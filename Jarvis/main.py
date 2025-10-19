import subprocess
import platform
import webbrowser
from datetime import datetime
import time

import ollama
import requests
from duckduckgo_search import DDGS


class JarvisAssistant:
    
    def __init__(self, model_name="llama3.2"):
        print("Initializing Jarvis Assistant...")
        print(f"Using Ollama model: {model_name}")
        
        self.model_name = model_name
        
        try:
            models_response = ollama.list()
            
            if isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            else:
                models_list = models_response
            
            model_names = []
            for model in models_list:
                if isinstance(model, dict):
                    model_names.append(model.get('name', model.get('model', '')))
                else:
                    model_names.append(getattr(model, 'name', getattr(model, 'model', '')))
            
            if model_names and not any(model_name in name for name in model_names):
                print(f"Warning: Model '{model_name}' not found")
                print(f"Available models: {', '.join(model_names)}")
                print(f"To install: ollama pull {model_name}")
                raise Exception(f"Model {model_name} not found")
            
            print(f"Model '{model_name}' verified")
            
        except Exception as e:
            print(f"Could not verify model list: {e}")
            print(f"Attempting to use '{model_name}' regardless...")
            
            try:
                test_response = ollama.chat(
                    model=self.model_name,
                    messages=[{'role': 'user', 'content': 'test'}]
                )
                print(f"Model '{model_name}' is working")
            except Exception as test_error:
                print(f"Model test failed: {test_error}")
                print(f"Try running: ollama pull {model_name}")
                raise
        
        try:
            self.search_available = True
            print("Web search enabled")
        except Exception as e:
            print(f"Warning: Search functionality unavailable - {e}")
            self.search_available = False
        
        print("Jarvis Assistant ready\n")
    
    def needs_web_search(self, query):
        current_info_keywords = [
            'weather', 'news', 'today', 'now', 'current', 'latest',
            'recent', 'president', 'what is happening', 'who is',
            'stock', 'price', 'score', 'election', 'update', 'forecast',
            'temperature', 'celsius', 'fahrenheit', 'rain', 'sunny'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in current_info_keywords)
    
    def search_web(self, query):
        if not self.search_available:
            return "Web search is currently unavailable"
        
        time.sleep(1)
        
        try:
            ddgs = DDGS(timeout=30)
            results = []
            
            credible_domains = [
                'weather.com', 'accuweather.com', 'noaa.gov', 'weather.gov',
                'congress.gov', 'usa.gov',
                'wikipedia.org', 'britannica.com',
                'reuters.com', 'apnews.com', 'bbc.com', 'npr.org',
                'cdc.gov', 'nih.gov', 'who.int'
            ]
            
            query_lower = query.lower()
            
            # Enhanced weather search
            if 'weather' in query_lower:
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
            
            if 'president' in query_lower or 'government' in query_lower:
                try:
                    print("   Searching government sources...")
                    gov_results = ddgs.text(
                        f"site:whitehouse.gov OR site:usa.gov {query}",
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
            
            # Regular search
            try:
                print("   Searching DuckDuckGo...")
                search_results = ddgs.text(
                    query,
                    region='wt-wt',
                    safesearch='off',
                    max_results=7
                )
                
                for result in search_results:
                    url = result.get('href', result.get('url', ''))
                    is_credible = any(domain in url for domain in credible_domains)
                    
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
            
            # News search backup
            if len(results) < 3:
                try:
                    print("   Trying news search...")
                    news_results = ddgs.news(query, max_results=5)
                    
                    for result in news_results:
                        url = result.get('url', result.get('link', ''))
                        is_credible = any(domain in url for domain in credible_domains)
                        
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
            
            if not results:
                return "No search results found. Try rephrasing your question."
            
            results.sort(key=lambda x: (not x.get('credible', False), 0))
            results = results[:5]
            
            formatted_results = []
            for i, result in enumerate(results, 1):
                credible_tag = " [VERIFIED]" if result.get('credible') else ""
                formatted_results.append(
                    f"[Result {i}{credible_tag}]\nTitle: {result['title']}\nInformation: {result['body']}\nURL: {result['url']}"
                )
            
            return "\n\n".join(formatted_results)
                
        except Exception as e:
            print(f"   Search exception: {str(e)}")
            return f"Search error: {str(e)}"
    
    def call_ollama(self, prompt, use_search_context=False):
        try:
            system_content = '''You are Jarvis, a helpful AI assistant with access to current information from web searches.

CRITICAL INSTRUCTIONS:
1. When search results are provided, YOU MUST use them to answer the user's question
2. NEVER say "I cannot provide" or "I don't have access" when search results are given
3. Extract and synthesize information directly from the search results
4. For weather queries: provide temperature, conditions, and forecast based on the results
5. Be direct, confident, and helpful
6. Cite which result you're using (e.g., "According to Result 1...")
7. If search results don't contain the answer, then politely say so'''

            if use_search_context:
                system_content += "\n\nYou have been provided with CURRENT search results. Use them to answer the question."
            
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_content},
                    {'role': 'user', 'content': prompt}
                ],
                options={
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'top_k': 40,
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            return f"Error communicating with Ollama: {str(e)}"
    
    def execute_system_command(self, command):
        command_lower = command.lower()
        
        try:
            # Website opening
            if "open" in command_lower and any(site in command_lower for site in ["google", "youtube", "github", "website", "browser"]):
                
                sites = {
                    "google": "https://www.google.com",
                    "youtube": "https://www.youtube.com",
                    "github": "https://www.github.com",
                    "twitter": "https://www.twitter.com",
                    "reddit": "https://www.reddit.com",
                }
                
                for site_name, url in sites.items():
                    if site_name in command_lower:
                        webbrowser.open(url)
                        return f"✓ Opened {site_name.title()} in your browser"
                
                webbrowser.open("https://www.google.com")
                return "✓ Opened browser"
            
            # Application opening
            elif "open" in command_lower or "launch" in command_lower:
                system = platform.system()
                
                app_mappings = {
                    "notepad": "notepad.exe" if system == "Windows" else "TextEdit" if system == "Darwin" else "gedit",
                    "calculator": "calc.exe" if system == "Windows" else "Calculator" if system == "Darwin" else "gnome-calculator",
                    "terminal": "cmd.exe" if system == "Windows" else "Terminal" if system == "Darwin" else "gnome-terminal",
                    "file explorer": "explorer.exe" if system == "Windows" else "Finder" if system == "Darwin" else "nautilus",
                    "explorer": "explorer.exe" if system == "Windows" else "Finder" if system == "Darwin" else "nautilus",
                    "chrome": "chrome.exe" if system == "Windows" else "Google Chrome" if system == "Darwin" else "google-chrome",
                    "firefox": "firefox.exe" if system == "Windows" else "Firefox" if system == "Darwin" else "firefox",
                }
                
                for app_name, app_command in app_mappings.items():
                    if app_name in command_lower:
                        if system == "Windows":
                            subprocess.Popen(app_command, shell=True)
                        elif system == "Darwin":
                            subprocess.Popen(["open", "-a", app_command])
                        else:
                            subprocess.Popen([app_command])
                        return f"✓ Opened {app_name.title()}"
                
                return "Application not recognized. Available: notepad, calculator, terminal, explorer, chrome, firefox"
            
            return "Command not recognized. Try: 'open chrome' or 'open youtube'"
            
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def chat(self, user_input):
        try:
            # Check for system commands
            command_keywords = ['open', 'launch', 'start']
            is_command = any(keyword in user_input.lower() for keyword in command_keywords)
            
            if is_command:
                result = self.execute_system_command(user_input)
                return result
            
            # Check if web search is needed
            if self.needs_web_search(user_input):
                print("🔍 Searching the web for current information...")
                
                search_results = self.search_web(user_input)
                
                if "error" in search_results.lower() or "unavailable" in search_results.lower():
                    print("Search issue detected, using model knowledge")
                    return self.call_ollama(user_input)
                
                if "no search results" in search_results.lower():
                    print("No results found, using model knowledge")
                    return self.call_ollama(user_input)
                
                # Create enhanced prompt with search results
                current_date = datetime.now().strftime("%B %d, %Y")
                prompt = f"""Current Date: {current_date}

User's Question: {user_input}

===== CURRENT WEB SEARCH RESULTS =====
{search_results}
===== END SEARCH RESULTS =====

INSTRUCTIONS:
You MUST answer the user's question using the search results above. These are CURRENT, REAL results from the web.

- Extract specific information (temperatures, dates, names, facts) from the results
- Synthesize a clear, direct answer
- Mention which result number you're referencing
- DO NOT refuse to answer - the information is provided above

Provide your answer now:"""
                
                print("Processing search results...")
                response = self.call_ollama(prompt, use_search_context=True)
                return response
            else:
                # General questions
                current_date = datetime.now().strftime("%B %d, %Y")
                prompt = f"Today's date is {current_date}. {user_input}"
                response = self.call_ollama(prompt)
                return response
            
        except Exception as e:
            return f"Error: {str(e)}\n\nPlease try rephrasing your question."


def main():
    # Verify Ollama
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Ollama is not installed or not running")
        print("Please install Ollama from https://ollama.ai")
        return
    
    # Initialize assistant
    try:
        assistant = JarvisAssistant(model_name="llama3.2")
    except Exception as e:
        print(f"\nFailed to initialize assistant: {e}")
        return
    
    print("💡 Tips:")
    print("  - Ask about weather: 'What's the weather in New York?'")
    print("  - Open apps: 'open chrome' or 'open calculator'")
    print("  - Open websites: 'open youtube' or 'open google'")
    print("  - Current events: 'latest news' or 'who is the president?'")
    print("  - Type 'exit' to quit\n")
    print("-" * 50)
    
    # Main loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                print("\nJarvis: Goodbye! Have a great day!")
                break
            
            if not user_input:
                continue
            
            print("\nJarvis: ", end="", flush=True)
            response = assistant.chat(user_input)
            print(response)
            print("\n" + "-" * 50)
            
        except KeyboardInterrupt:
            print("\n\nJarvis: Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    main()