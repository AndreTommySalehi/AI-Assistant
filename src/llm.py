"""
Enhanced LLM with GPT-OSS (HuggingFace), Ollama, and A/B testing
"""

import ollama
from . import config
import re
from datetime import datetime

# Try to import HuggingFace Transformers for GPT-OSS
try:
    from transformers import pipeline
    import torch
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


class LLMHandler:
    """Handles communication with multiple LLM providers"""
    
    def __init__(self, model_name=None):
        self.primary_model = model_name or config.DEFAULT_MODEL
        self.use_ab_testing = config.ENABLE_AB_TESTING
        self.use_gpt_oss = config.USE_GPT_OSS
        
        # Initialize GPT-OSS pipeline if enabled
        self.gpt_oss_pipe = None
        if self.use_gpt_oss and HF_AVAILABLE:
            try:
                print(f"Loading GPT-OSS model: {config.GPT_OSS_MODEL}...")
                print("⏳ This may take a few minutes on first run (downloading ~8GB)...")
                
                self.gpt_oss_pipe = pipeline(
                    "text-generation",
                    model=config.GPT_OSS_MODEL,
                    torch_dtype=torch.bfloat16,
                    device_map="auto",
                )
                print(f"✓ GPT-OSS model loaded successfully!")
            except Exception as e:
                print(f"✗ Failed to load GPT-OSS: {e}")
                self.use_gpt_oss = False
        
        self._verify_ollama_model()
    
    def _verify_ollama_model(self):
        """Verify Ollama model exists"""
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
            
            print(f"✓ Using Ollama model: {self.primary_model}")
            
        except Exception as e:
            pass  # Silent failure
    
    def generate(self, prompt, use_search_context=False):
        """Generate response - prioritize GPT-OSS if available"""
        
        # If GPT-OSS is loaded, use it as primary
        if self.use_gpt_oss and self.gpt_oss_pipe:
            try:
                return self._generate_gpt_oss(prompt, use_search_context)
            except Exception as e:
                print(f"GPT-OSS failed, falling back to Ollama: {e}")
                return self._single_generate(prompt, use_search_context)
        
        # Otherwise use A/B testing or single model
        if self.use_ab_testing and use_search_context:
            return self._ab_test_generate(prompt, use_search_context)
        else:
            return self._single_generate(prompt, use_search_context)
    
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
    
    def _generate_gpt_oss(self, prompt, use_search_context):
        """Generate using GPT-OSS as primary model"""
        system_content = self._get_system_prompt(use_search_context)
        full_prompt = f"{system_content}\n\nUser: {prompt}\n\nAssistant:"
        
        outputs = self.gpt_oss_pipe(
            full_prompt,
            max_new_tokens=config.GPT_OSS_MAX_TOKENS,
            temperature=config.MODEL_OPTIONS.get('temperature', 0.7),
            do_sample=True,
            top_p=config.MODEL_OPTIONS.get('top_p', 0.9),
        )
        
        gpt_oss_response = outputs[0]["generated_text"]
        
        # Extract only the assistant's response
        if "Assistant:" in gpt_oss_response:
            gpt_oss_response = gpt_oss_response.split("Assistant:")[-1].strip()
        
        return gpt_oss_response
    
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
        """A/B test: compare Ollama + GPT-OSS responses"""
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
        except Exception as e:
            pass
        
        # Model 2: Secondary Ollama (if configured)
        if hasattr(config, 'SECONDARY_MODEL') and config.SECONDARY_MODEL:
            try:
                secondary_response = ollama.chat(
                    model=config.SECONDARY_MODEL,
                    messages=[
                        {'role': 'system', 'content': system_content},
                        {'role': 'user', 'content': prompt}
                    ],
                    options=config.MODEL_OPTIONS
                )['message']['content']
                
                confidence = self._calculate_confidence(secondary_response, prompt)
                responses.append({
                    'model': config.SECONDARY_MODEL,
                    'response': secondary_response,
                    'confidence': confidence,
                    'provider': 'Ollama'
                })
            except Exception as e:
                pass
        
        # Model 3: GPT-OSS (if enabled and loaded)
        if self.use_gpt_oss and self.gpt_oss_pipe:
            try:
                # Format prompt for GPT-OSS
                full_prompt = f"{system_content}\n\nUser: {prompt}\n\nAssistant:"
                
                outputs = self.gpt_oss_pipe(
                    full_prompt,
                    max_new_tokens=config.GPT_OSS_MAX_TOKENS,
                    temperature=config.MODEL_OPTIONS.get('temperature', 0.7),
                    do_sample=True,
                    top_p=config.MODEL_OPTIONS.get('top_p', 0.9),
                )
                
                gpt_oss_response = outputs[0]["generated_text"]
                # Extract only the assistant's response
                if "Assistant:" in gpt_oss_response:
                    gpt_oss_response = gpt_oss_response.split("Assistant:")[-1].strip()
                
                confidence = self._calculate_confidence(gpt_oss_response, prompt)
                responses.append({
                    'model': config.GPT_OSS_MODEL,
                    'response': gpt_oss_response,
                    'confidence': confidence,
                    'provider': 'GPT-OSS'
                })
            except Exception as e:
                pass
        
        # Select best response
        if not responses:
            return "I'm having trouble generating a response. Please try again."
        
        best = max(responses, key=lambda x: x['confidence'])
        
        return best['response']
    
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