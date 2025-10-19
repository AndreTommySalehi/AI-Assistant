"""
LLM communication using Ollama
"""

import ollama
from . import config


class LLMHandler:
    """Handles communication with Ollama LLM"""
    
    def __init__(self, model_name=None):
        self.model_name = model_name or config.DEFAULT_MODEL
        self._verify_model()
    
    def _verify_model(self):
        """Verify the model exists and is working"""
        print(f"Using Ollama model: {self.model_name}")
        
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
            
            if model_names and not any(self.model_name in name for name in model_names):
                print(f"Warning: Model '{self.model_name}' not found")
                print(f"Available models: {', '.join(model_names)}")
                print(f"To install: ollama pull {self.model_name}")
                raise Exception(f"Model {self.model_name} not found")
            
            print(f"Model '{self.model_name}' verified")
            
        except Exception as e:
            print(f"Could not verify model list: {e}")
            print(f"Attempting to use '{self.model_name}' regardless...")
            
            # Quick test
            try:
                test_response = ollama.chat(
                    model=self.model_name,
                    messages=[{'role': 'user', 'content': 'test'}]
                )
                print(f"Model '{self.model_name}' is working")
            except Exception as test_error:
                print(f"Model test failed: {test_error}")
                print(f"Try running: ollama pull {self.model_name}")
                raise
    
    def generate(self, prompt, use_search_context=False):
        """Generate a response from the LLM"""
        try:
            system_content = self._get_system_prompt(use_search_context)
            
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_content},
                    {'role': 'user', 'content': prompt}
                ],
                options=config.MODEL_OPTIONS
            )
            
            return response['message']['content']
            
        except Exception as e:
            return f"Error communicating with Ollama: {str(e)}"
    
    def _get_system_prompt(self, use_search_context):
        """Get the appropriate system prompt"""
        base_prompt = '''You are Jarvis, a helpful AI assistant with access to current information from web searches.

CRITICAL INSTRUCTIONS:
1. When search results are provided, YOU MUST use them to answer the user's question
2. NEVER say "I cannot provide" or "I don't have access" when search results are given
3. Extract and synthesize information directly from the search results
4. For weather queries: provide temperature, conditions, and forecast based on the results
5. Be direct, confident, and helpful
6. Cite which result you're using (e.g., "According to Result 1...")
7. If search results don't contain the answer, then politely say so'''

        if use_search_context:
            base_prompt += "\n\nYou have been provided with CURRENT search results. Use them to answer the question."
        
        return base_prompt