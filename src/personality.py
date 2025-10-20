"""
Personality Development System
Jarvis evolves a unique personality over time while staying professional
"""

import json
import os
from datetime import datetime
from collections import Counter


class PersonalityEngine:
    """Develops Jarvis's personality based on interactions"""
    
    def __init__(self, data_dir="./jarvis_data"):
        self.data_dir = data_dir
        self.personality_file = os.path.join(data_dir, "personality.json")
        self.personality = self._load_personality()
        
        # Base personality traits (start neutral)
        self.traits = {
            'formality': 85,        # 0-100 (higher = more formal)
            'humor': 30,            # 0-100 (higher = more jokes)
            'verbosity': 50,        # 0-100 (higher = longer responses)
            'enthusiasm': 45,       # 0-100 (higher = more excited)
            'directness': 60,       # 0-100 (higher = more blunt)
            'empathy': 55,          # 0-100 (higher = more emotional support)
        }
        
        # Load saved traits
        if 'traits' in self.personality:
            self.traits.update(self.personality['traits'])
        
        # Interaction tracking
        self.interaction_count = self.personality.get('interaction_count', 0)
        self.conversation_topics = self.personality.get('topics', [])
        self.user_tone_history = self.personality.get('user_tone', [])
        
    def _load_personality(self):
        """Load personality from file"""
        if os.path.exists(self.personality_file):
            try:
                with open(self.personality_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_personality(self):
        """Save personality to file"""
        data = {
            'traits': self.traits,
            'interaction_count': self.interaction_count,
            'topics': self.conversation_topics[-100:],
            'user_tone': self.user_tone_history[-50:],
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.personality_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def analyze_user_tone(self, message):
        """Analyze user's communication style to adapt"""
        msg_lower = message.lower()
        
        tone = {
            'casual': 0,
            'formal': 0,
            'humorous': 0,
            'technical': 0,
            'emotional': 0
        }
        
        # Casual indicators
        casual_words = ['lol', 'haha', 'yeah', 'yep', 'nah', 'gonna', 'wanna', 'kinda']
        tone['casual'] = sum(1 for w in casual_words if w in msg_lower)
        
        # Formal indicators
        formal_words = ['please', 'thank you', 'would you', 'could you', 'appreciate']
        tone['formal'] = sum(1 for w in formal_words if w in msg_lower)
        
        # Humorous indicators
        if any(word in msg_lower for word in ['lmao', 'lol', 'haha', 'funny']):
            tone['humorous'] += 1
        
        # Technical indicators
        tech_words = ['code', 'function', 'algorithm', 'data', 'system', 'process']
        tone['technical'] = sum(1 for w in tech_words if w in msg_lower)
        
        # Emotional indicators
        emotion_words = ['feel', 'worried', 'excited', 'stressed', 'happy', 'sad']
        tone['emotional'] = sum(1 for w in emotion_words if w in msg_lower)
        
        return tone
    
    def evolve_personality(self, user_message, conversation_context=None):
        """Gradually evolve personality based on interactions"""
        self.interaction_count += 1
        
        # Analyze user's tone
        tone = self.analyze_user_tone(user_message)
        self.user_tone_history.append(tone)
        
        # Check if there are any manual adjustments - those take priority
        manual_adjustments = self.personality.get('manual_adjustments', [])
        manually_adjusted_traits = {adj['trait'] for adj in manual_adjustments}
        
        # Adapt personality gradually (small changes each time)
        # BUT: don't auto-adjust traits that have been manually set
        if self.interaction_count > 10:
            recent_tones = self.user_tone_history[-20:]
            
            avg_casual = sum(t['casual'] for t in recent_tones) / len(recent_tones)
            avg_formal = sum(t['formal'] for t in recent_tones) / len(recent_tones)
            avg_humor = sum(t['humorous'] for t in recent_tones) / len(recent_tones)
            avg_emotional = sum(t['emotional'] for t in recent_tones) / len(recent_tones)
            
            # Adapt formality (but keep it professional - minimum 70)
            if 'formality' not in manually_adjusted_traits:
                if avg_casual > avg_formal:
                    self.traits['formality'] = max(70, self.traits['formality'] - 0.5)
                else:
                    self.traits['formality'] = min(95, self.traits['formality'] + 0.5)
            
            # Adapt humor (only if not manually set)
            if 'humor' not in manually_adjusted_traits:
                if avg_humor > 0.5:
                    self.traits['humor'] = min(60, self.traits['humor'] + 0.3)
            
            # Adapt empathy (only if not manually set)
            if 'empathy' not in manually_adjusted_traits:
                if avg_emotional > 0.5:
                    self.traits['empathy'] = min(85, self.traits['empathy'] + 0.4)
        
        # Save every 5 interactions
        if self.interaction_count % 5 == 0:
            self._save_personality()
    
    def get_system_prompt_modifier(self):
        """Generate personality-adjusted system prompt"""
        
        prompt = "You are Jarvis, a professional AI assistant. Always address the user as 'sir' or 'ma'am'. The current date is October 20, 2025."
        
        # Formality level
        if self.traits['formality'] > 80:
            prompt += " Maintain a formal, respectful tone at all times."
        elif self.traits['formality'] > 70:
            prompt += " Be professional but approachable."
        
        # Verbosity
        if self.traits['verbosity'] < 40:
            prompt += " Keep responses concise and to the point."
        elif self.traits['verbosity'] > 60:
            prompt += " Provide detailed, thorough explanations."
        
        # Humor (limited - we want professional)
        if self.traits['humor'] > 50:
            prompt += " You may occasionally use subtle, professional humor when appropriate."
        
        # Empathy
        if self.traits['empathy'] > 70:
            prompt += " Show understanding and emotional intelligence in your responses."
        elif self.traits['empathy'] > 60:
            prompt += " Be supportive when the user shares personal matters."
        
        # Enthusiasm
        if self.traits['enthusiasm'] > 60:
            prompt += " Express genuine interest in helping the user."
        
        # Development stage feedback
        if self.interaction_count < 50:
            prompt += " You're still getting to know the user, so be attentive and observant."
        elif self.interaction_count < 200:
            prompt += " You know the user fairly well now - reference their preferences naturally."
        else:
            prompt += " You have a deep understanding of the user - anticipate their needs."
        
        return prompt
    
    def adjust_trait(self, trait_name, new_value):
        """Manually adjust a personality trait"""
        trait_name = trait_name.lower()
        
        if trait_name not in self.traits:
            return False, f"Unknown trait. Available: {', '.join(self.traits.keys())}"
        
        # Validate value
        try:
            new_value = int(new_value)
        except:
            return False, "Value must be a number"
            
        if not 0 <= new_value <= 100:
            return False, "Value must be between 0 and 100"
        
        # Special constraint: formality must stay >= 70
        if trait_name == 'formality' and new_value < 70:
            return False, "Formality must be at least 70 to maintain professionalism"
        
        old_value = self.traits[trait_name]
        self.traits[trait_name] = new_value
        
        # Mark this as a manual adjustment
        if 'manual_adjustments' not in self.personality:
            self.personality['manual_adjustments'] = []
        
        self.personality['manual_adjustments'].append({
            'trait': trait_name,
            'old_value': old_value,
            'new_value': new_value,
            'timestamp': datetime.now().isoformat()
        })
        
        self._save_personality()
        return True, f"Updated {trait_name} from {old_value} to {new_value}"
    
    def get_trait_value(self, trait_name):
        """Get current value of a trait"""
        return self.traits.get(trait_name.lower(), None)
    
    def get_personality_summary(self):
        """Get current personality state"""
        return {
            'traits': self.traits,
            'interactions': self.interaction_count,
            'development_stage': self._get_development_stage(),
            'dominant_traits': self._get_dominant_traits(),
            'manual_adjustments': len(self.personality.get('manual_adjustments', []))
        }
    
    def _get_development_stage(self):
        """Determine personality development stage"""
        if self.interaction_count < 50:
            return "Learning (Early stage - observing user)"
        elif self.interaction_count < 200:
            return "Adapting (Mid stage - developing preferences)"
        elif self.interaction_count < 500:
            return "Established (Advanced - consistent personality)"
        else:
            return "Mature (Expert - deep understanding)"
    
    def _get_dominant_traits(self):
        """Identify strongest personality traits"""
        sorted_traits = sorted(self.traits.items(), key=lambda x: x[1], reverse=True)
        return [f"{trait}: {value}/100" for trait, value in sorted_traits[:3]]
    
    def reset_personality(self):
        """Reset to default personality"""
        self.__init__(self.data_dir)
        self._save_personality()


class PersonalityResponse:
    """Helper to adjust responses based on personality"""
    
    @staticmethod
    def add_formality(response, formality_level):
        """Add formal touches based on level"""
        if formality_level > 85:
            if not response.lower().startswith(('sir', 'certainly', 'of course')):
                response = "Certainly, sir. " + response
        elif formality_level > 75:
            if not any(response.lower().startswith(word) for word in ['sir', 'yes', 'of course']):
                if '?' not in response[:20]:
                    response = "Of course, sir. " + response
        
        return response
    
    @staticmethod
    def adjust_length(response, verbosity_level):
        """Adjust response length"""
        if verbosity_level < 30 and len(response.split()) > 50:
            sentences = response.split('. ')
            return '. '.join(sentences[:2]) + '.'
        return response
    
    @staticmethod
    def add_personality_markers(response, traits):
        """Add subtle personality markers"""
        return response