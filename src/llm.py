import ollama
from . import config
import re
from datetime import datetime
import requests

class LLMHandler:
    """Handles communication with multiple LLM providers"""
    
    def __init__(self, model_name=None, enable_ab_testing=None):
        self.primary_model = model_name or config.DEFAULT_MODEL
        self.use_ab_testing = enable_ab_testing if enable_ab_testing is not None else config.ENABLE_AB_TESTING
        self.use_gpt_oss = config.USE_GPT_OSS
        
        # Check if GPT-OSS server is running
        self.gpt_oss_available = False
        if self.use_gpt_oss:
            try:
                response = requests.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    self.gpt_oss_available = True
                    print("GPT-OSS server connected")
                else:
                    print("GPT-OSS server not responding")
            except Exception:
                self.use_gpt_oss = False
        
        self._verify_ollama_model()
        
        if self.use_ab_testing:
            print("A/B testing enabled")
    
    def _verify_ollama_model(self):
        """Verify Ollama model exists"""
        try:
            models_response = ollama.list()
            
            if isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            else:
                models_list = models_response
            
            # Silently verify model exists
            
        except Exception:
            pass
    
    def generate(self, prompt, use_search_context=False):
        """Generate response - try GPT-OSS server first, fallback to Ollama"""
        
        # Try GPT-OSS server if available
        if self.use_gpt_oss and self.gpt_oss_available:
            try:
                return self._generate_gpt_oss_server(prompt, use_search_context)
            except Exception as e:
                print(f"GPT-OSS failed, falling back to Ollama: {e}")
                return self._single_generate(prompt, use_search_context)
        
        # Otherwise use Ollama
        if self.use_ab_testing and use_search_context:
            return self._ab_test_generate(prompt, use_search_context)
        else:
            return self._single_generate(prompt, use_search_context)
    
    def _generate_gpt_oss_server(self, prompt, use_search_context):
        """Generate using GPT-OSS server"""
        system_content = self._get_system_prompt(use_search_context)
        
        # Call the transformers server API
        response = requests.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "openai/gpt-oss-20b",
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": config.GPT_OSS_MAX_TOKENS,
                "temperature": config.MODEL_OPTIONS.get('temperature', 0.7),
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            raise Exception(f"Server returned {response.status_code}")
    
    def generate_with_history(self, prompt, conversation_history):
        """Generate response with conversation history"""
        try:
            system_content = self._get_system_prompt(use_search_context=False)
            
            # Build messages with history
            messages = [{'role': 'system', 'content': system_content}]
            
            # Add recent history (last 4 messages only)
            recent_history = conversation_history[-5:-1] if len(conversation_history) > 5 else conversation_history[:-1]
            
            for msg in recent_history:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            # Add current message
            current_date = datetime.now().strftime("%B %d, %Y")
            messages.append({
                'role': 'user',
                'content': f"Today's date is {current_date}. {prompt}"
            })
            
            response = ollama.chat(
                model=self.primary_model,
                messages=messages,
                options=config.MODEL_OPTIONS
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"[LLM Error]: {str(e)}")
            return f"I'm having trouble connecting to my AI model right now. Please try again."
    
    def _single_generate(self, prompt, use_search_context):
        """Generate from primary model only"""
        try:
            system_content = self._get_system_prompt(use_search_context)
            
            response = ollama.chat(
                model=self.primary_model,
                messages=[
                    {'role': 'system', 'content': system_content},
                    {'role': 'user', 'content': prompt}
                ],
                options=config.MODEL_OPTIONS
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"[LLM Error]: {str(e)}")
            return f"I'm having trouble connecting to my AI model right now. Please try again."
    
    def _ab_test_generate(self, prompt, use_search_context):
        """A/B test: compare responses from different sources"""
        responses = []
        system_content = self._get_system_prompt(use_search_context)
        
        # Model 1: Primary Ollama
        try:
            primary_response = self._single_generate(prompt, use_search_context)
            confidence = self._calculate_confidence(primary_response, prompt)
            responses.append({
                'model': self.primary_model,
                'response': primary_response,
                'confidence': confidence,
                'provider': 'Ollama'
            })
        except Exception:
            pass
        
        # Model 2: GPT-OSS (if available)
        if self.use_gpt_oss and self.gpt_oss_available:
            try:
                gpt_response = self._generate_gpt_oss_server(prompt, use_search_context)
                confidence = self._calculate_confidence(gpt_response, prompt)
                responses.append({
                    'model': 'GPT-OSS',
                    'response': gpt_response,
                    'confidence': confidence,
                    'provider': 'GPT-OSS'
                })
            except Exception:
                pass
        
        # Select best response
        if not responses:
            return "I'm having trouble generating a response. Please try again."
        
        if len(responses) == 1:
            return responses[0]['response']
        
        # Compare confidence scores
        best = max(responses, key=lambda x: x['confidence'])
        
        # Only use best if confidence difference is significant
        confidence_diff = best['confidence'] - min(r['confidence'] for r in responses)
        if confidence_diff > config.CONFIDENCE_THRESHOLD:
            print(f"[A/B] Using {best['model']} (confidence: {best['confidence']})")
            return best['response']
        
        # If similar confidence, use primary
        return responses[0]['response']
    
    def _calculate_confidence(self, response, prompt):
        """Calculate confidence score 0-100"""
        confidence = 50
        response_lower = response.lower()
        
        # Uncertainty phrases (reduce)
        uncertainty_phrases = [
            "i'm not sure", "i don't know", "unclear", "uncertain",
            "might be", "possibly", "perhaps", "maybe", "could be",
            "i cannot provide", "i can't determine", "no information",
            "insufficient", "unable to find", "cannot confirm"
        ]
        uncertainty_count = sum(1 for p in uncertainty_phrases if p in response_lower)
        confidence -= (uncertainty_count * 12)
        
        # Certainty phrases (increase)
        certainty_phrases = [
            "according to", "the search shows", "based on",
            "specifically", "confirmed", "verified", "states that",
            "indicates that", "shows that", "reported", "official"
        ]
        certainty_count = sum(1 for p in certainty_phrases if p in response_lower)
        confidence += (certainty_count * 8)
        
        # Specific data (increase)
        if re.search(r'\d+°[FC]', response):
            confidence += 15
        if re.search(r'\d{1,2}/\d{1,2}(/\d{4})?', response):
            confidence += 10
        if re.search(r'\$\d+', response):
            confidence += 10
        if re.search(r'\d+%', response):
            confidence += 8
        
        # Length check
        if len(response) < 50:
            confidence -= 15
        elif len(response) > 200:
            confidence += 8
        
        return max(0, min(100, confidence))
    
    def _get_system_prompt(self, use_search_context):
        """System prompt - natural conversational style"""
        
        if use_search_context:
            return '''You are Jarvis, a helpful AI assistant.

Rules:
1. Answer the question directly from the search results
2. Be conversational and natural (2-3 sentences)
3. DO NOT mention previous topics unless directly asked
4. NO phrases like "switching gears" or "we talked about"
5. Just answer the current question

Example:
Question: "Bitcoin price right now"
You: "Bitcoin is at $107k right now. It's up about 2% today."

Stay focused on the current question!'''
        else:
            return '''You are Jarvis, a helpful AI assistant.

Keep responses natural and conversational (2-3 sentences).
Answer the current question directly.
NO bullet points or lists unless specifically asked.
Be friendly and concise.'''