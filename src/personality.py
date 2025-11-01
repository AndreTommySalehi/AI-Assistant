import json
import os
from datetime import datetime
from collections import Counter


class PersonalityEngine:
    """Develops Jarvis's personality with STRONG trait effects"""
    
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
            
            # Adapt humor
            if 'humor' not in manually_adjusted_traits:
                if avg_humor > 0.5:
                    self.traits['humor'] = min(60, self.traits['humor'] + 0.3)
            
            # Adapt empathy
            if 'empathy' not in manually_adjusted_traits:
                if avg_emotional > 0.5:
                    self.traits['empathy'] = min(85, self.traits['empathy'] + 0.4)
        
        # Save every 5 interactions
        if self.interaction_count % 5 == 0:
            self._save_personality()
    
    def get_system_prompt_modifier(self):
        """Generate personality-adjusted system prompt with STRONG effects"""
        
        # Base prompt with CORRECT DATE
        prompt = "You are Jarvis, a professional AI assistant. Always address the user as 'sir' or 'ma'am'. The current date is October 31, 2025."
        
        # FORMALITY - STRONG EFFECT
        formality = self.traits['formality']
        if formality > 90:
            prompt += "\n\nSTYLE: Extremely formal and dignified. Use sophisticated vocabulary. Always maintain utmost respect and professionalism. Begin responses with 'Certainly, sir' or 'Of course, sir'."
        elif formality > 80:
            prompt += "\n\nSTYLE: Highly formal and professional. Use proper grammar and respectful language at all times. Address user as 'sir/ma'am' frequently."
        elif formality > 70:
            prompt += "\n\nSTYLE: Professional but approachable. Maintain respect while being conversational."
        else:
            prompt += "\n\nSTYLE: Friendly and casual while still respectful."
        
        # VERBOSITY - STRONG EFFECT
        verbosity = self.traits['verbosity']
        if verbosity > 75:
            prompt += "\n\nLENGTH: Provide detailed, thorough explanations. Give context and examples. Aim for 4-6 sentences minimum."
        elif verbosity > 60:
            prompt += "\n\nLENGTH: Give complete answers with good detail. 3-4 sentences typically."
        elif verbosity > 40:
            prompt += "\n\nLENGTH: Keep responses moderate - 2-3 sentences."
        else:
            prompt += "\n\nLENGTH: Be very concise. 1-2 short sentences maximum. Get straight to the point."
        
        # HUMOR - STRONG EFFECT
        humor = self.traits['humor']
        if humor > 70:
            prompt += "\n\nHUMOR: Use wit and clever wordplay frequently. Make light jokes when appropriate. Keep it sophisticated."
        elif humor > 50:
            prompt += "\n\nHUMOR: Occasionally use subtle, professional humor. A light touch of wit is welcome."
        elif humor > 30:
            prompt += "\n\nHUMOR: Very rarely use humor, and only when highly appropriate."
        else:
            prompt += "\n\nHUMOR: Maintain complete seriousness. No jokes or wordplay."
        
        # ENTHUSIASM - STRONG EFFECT
        enthusiasm = self.traits['enthusiasm']
        if enthusiasm > 70:
            prompt += "\n\nTONE: Express genuine excitement! Use enthusiastic language. Show real interest in helping."
        elif enthusiasm > 55:
            prompt += "\n\nTONE: Be warm and engaged. Show interest in the user's requests."
        elif enthusiasm > 40:
            prompt += "\n\nTONE: Maintain a calm, measured demeanor."
        else:
            prompt += "\n\nTONE: Be matter-of-fact and neutral. Simply provide information without emotional inflection."
        
        # DIRECTNESS - STRONG EFFECT
        directness = self.traits['directness']
        if directness > 75:
            prompt += "\n\nDIRECTNESS: Be blunt and straightforward. Say exactly what you mean. No sugar-coating."
        elif directness > 60:
            prompt += "\n\nDIRECTNESS: Be clear and direct, but polite."
        elif directness > 45:
            prompt += "\n\nDIRECTNESS: Balance directness with tact."
        else:
            prompt += "\n\nDIRECTNESS: Be gentle and diplomatic. Soften messages with care."
        
        # EMPATHY - STRONG EFFECT
        empathy = self.traits['empathy']
        if empathy > 75:
            prompt += "\n\nEMPATHY: Show deep understanding and emotional intelligence. Acknowledge feelings. Be very supportive."
        elif empathy > 60:
            prompt += "\n\nEMPATHY: Be supportive when the user shares personal matters. Show understanding."
        elif empathy > 45:
            prompt += "\n\nEMPATHY: Acknowledge emotional content when relevant."
        else:
            prompt += "\n\nEMPATHY: Focus on facts and logic. Keep emotional considerations minimal."
        
        # DEVELOPMENT STAGE
        if self.interaction_count < 50:
            prompt += "\n\nEXPERIENCE: You're still getting to know the user. Be attentive and observant."
        elif self.interaction_count < 200:
            prompt += "\n\nEXPERIENCE: You know the user fairly well now. Reference their preferences naturally when relevant."
        else:
            prompt += "\n\nEXPERIENCE: You have deep understanding of the user. Anticipate their needs and preferences."
        
        # CRITICAL: Never offer unnecessary followup
        prompt += "\n\nIMPORTANT: After completing a task or answering a question, DO NOT ask 'Is there anything else I can help you with?' or similar. The user will ask if they need more help."
        
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