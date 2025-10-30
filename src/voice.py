"""
Voice Assistant - Inverted hybrid mode with continuous wake word detection
Smart approach:
- Short responses: Cloned voice (quick to generate, high quality)
- Long responses: System voice (instant, avoids 30+ second wait)
- Continuous listening: Processes commands immediately after "Jarvis"
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import hashlib
import re
import threading

sys.path.insert(0, os.path.dirname(__file__))

# Try importing voice cloning libraries
COQUI_AVAILABLE = False
try:
    from TTS.api import TTS
    COQUI_AVAILABLE = True
except ImportError:
    pass

AUDIO_PLAYBACK = False
try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_PLAYBACK = True
except ImportError:
    pass

PYTTSX3_AVAILABLE = False
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    pass

SPEECH_RECOGNITION_AVAILABLE = False
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    pass


def list_microphones():
    """List all available microphones"""
    if not SPEECH_RECOGNITION_AVAILABLE:
        return []
    
    mic_list = []
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        mic_list.append((index, name))
        print(f"  [{index}] {name}")
    return mic_list


class JarvisVoice:
    """Inverted hybrid: Quality for short, fast for long"""
    
    def __init__(self, voice_mode="hybrid", voice_samples_dir="./voice_samples", reference_file=None, microphone_index=None):
        self.voice_mode = voice_mode
        self.voice_samples_dir = voice_samples_dir
        self.tts = None
        self.pyttsx3_engine = None
        self.speaker_wav = None
        self.reference_file = reference_file
        self.microphone_index = microphone_index
        
        # Speed optimization: cache
        self.cache_dir = os.path.join(voice_samples_dir, ".cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Inverted hybrid mode settings
        self.hybrid_mode = (voice_mode == "hybrid")
        self.cloned_word_limit = 30  # Use cloned if under this (short = quality)
        self.tts_speed = 1.2
        
        # Initialize both voice systems for hybrid mode
        if self.hybrid_mode or voice_mode == "cloned":
            self._init_cloned_voice()
        
        # Always init system voice (fallback + long responses)
        self._init_system_voice()
        
        # Initialize speech recognition
        self.recognizer = None
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 4000
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 1.5  # Longer pause before stopping (was 0.8)
    
    def _init_cloned_voice(self):
        """Initialize Coqui TTS for short, high-quality responses"""
        if not COQUI_AVAILABLE:
            return False
        
        try:
            self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
            
            # Check for voice samples
            if os.path.exists(self.voice_samples_dir):
                samples = [f for f in os.listdir(self.voice_samples_dir) 
                          if f.endswith(('.wav', '.mp3', '.flac')) 
                          and not f.startswith('_combined')
                          and not f.startswith('.')]
                
                if samples:
                    # Use best sample only for speed
                    self.speaker_wav = os.path.join(self.voice_samples_dir, samples[0])
                    return True
            
            return True
            
        except Exception as e:
            self.tts = None
            return False
    
    def _init_system_voice(self):
        """Initialize pyttsx3 for long responses"""
        if not PYTTSX3_AVAILABLE:
            return False
        
        try:
            self.pyttsx3_engine = pyttsx3.init()
            
            # Find best voice
            voices = self.pyttsx3_engine.getProperty('voices')
            for voice in voices:
                if 'british' in voice.name.lower() or 'daniel' in voice.name.lower():
                    self.pyttsx3_engine.setProperty('voice', voice.id)
                    break
            
            # Optimized settings for clarity
            self.pyttsx3_engine.setProperty('rate', 175)
            self.pyttsx3_engine.setProperty('volume', 0.9)
            
            return True
            
        except Exception as e:
            return False
    
    def should_use_cloned_voice(self, text):
        """Decide: short = cloned (quality), long = system (instant)"""
        if not self.hybrid_mode:
            return True
        
        word_count = len(text.split())
        
        if word_count <= self.cloned_word_limit:
            return True
        
        return False
    
    def speak(self, text, wait=True, use_cache=True, force_mode=None):
        """Smart: cloned for short, system for long"""
        if not text:
            return
        
        if force_mode == "cloned":
            use_cloned = True
        elif force_mode == "system":
            use_cloned = False
        else:
            use_cloned = self.should_use_cloned_voice(text)
        
        if use_cloned and self.tts:
            print("(quality) ", end="", flush=True)
            try:
                self._speak_cloned_fast(text, wait, use_cache)
            except Exception as e:
                if self.pyttsx3_engine:
                    self._speak_system(text, wait)
        elif self.pyttsx3_engine:
            print("(fast) ", end="", flush=True)
            self._speak_system(text, wait)
    
    def _speak_cloned_fast(self, text, wait=True, use_cache=True):
        """High-quality cloned voice generation"""
        import hashlib
        
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cached_file = os.path.join(self.cache_dir, f"{text_hash}.wav")
        
        if use_cache and os.path.exists(cached_file):
            if AUDIO_PLAYBACK:
                data, samplerate = sf.read(cached_file)
                sd.play(data, int(samplerate * 0.95))
                if wait:
                    sd.wait()
            return
        
        output_file = "./temp_speech.wav"
        
        try:
            if self.speaker_wav:
                self.tts.tts_to_file(
                    text=text,
                    file_path=output_file,
                    speaker_wav=self.speaker_wav,
                    language="en",
                    speed=self.tts_speed,
                )
            else:
                self.tts.tts_to_file(
                    text=text,
                    file_path=output_file,
                    language="en",
                    speed=self.tts_speed
                )
            
            if AUDIO_PLAYBACK:
                data, samplerate = sf.read(output_file)
                sd.play(data, int(samplerate * 0.95))
                
                threading.Thread(target=self._cache_audio, args=(cached_file, data, samplerate), daemon=True).start()
                
                if wait:
                    sd.wait()
            
            try:
                os.remove(output_file)
            except:
                pass
                    
        except Exception as e:
            raise Exception(f"Speech generation failed: {e}")
    
    def _cache_audio(self, filepath, data, samplerate):
        """Background caching"""
        try:
            sf.write(filepath, data, samplerate)
        except:
            pass
    
    def _speak_system(self, text, wait=True):
        """Fast system voice"""
        self.pyttsx3_engine.say(text)
        if wait:
            self.pyttsx3_engine.runAndWait()
    
    def speak_streaming(self, text):
        """Stream response intelligently"""
        if not text:
            return
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            is_last = (i == len(sentences) - 1)
            self.speak(sentence.strip(), wait=is_last, use_cache=True)
    
    def listen_continuous(self, timeout=None):
        """Continuously listen and return full phrase"""
        if not self.recognizer:
            return None
        
        try:
            mic_kwargs = {}
            if self.microphone_index is not None:
                mic_kwargs['device_index'] = self.microphone_index
                
            with sr.Microphone(**mic_kwargs) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=None
                )
                
                try:
                    text = self.recognizer.recognize_google(audio)
                    return text.lower()
                except sr.UnknownValueError:
                    return None
                
        except sr.WaitTimeoutError:
            return None
        except Exception:
            return None
    
    def extract_command_after_wake_word(self, text, wake_word="jarvis"):
        """Extract command from text containing wake word"""
        if not text:
            return None
        
        text_lower = text.lower()
        wake_word_lower = wake_word.lower()
        
        if wake_word_lower not in text_lower:
            return None
        
        # Find position of wake word and extract everything after
        wake_word_index = text_lower.find(wake_word_lower)
        command_start = wake_word_index + len(wake_word_lower)
        
        # Get the command part
        command = text[command_start:].strip()
        
        # Remove common filler words at start
        filler_words = ['please', 'can you', 'could you', 'would you']
        for filler in filler_words:
            if command.lower().startswith(filler):
                command = command[len(filler):].strip()
        
        return command if command else None
    
    def listen(self, timeout=5, phrase_limit=None):
        """Listen for speech input"""
        if not self.recognizer:
            return None
        
        try:
            mic_kwargs = {}
            if self.microphone_index is not None:
                mic_kwargs['device_index'] = self.microphone_index
                
            with sr.Microphone(**mic_kwargs) as source:
                print("\nListening...", end=" ", flush=True)
                
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
                
                print("Processing...", end=" ", flush=True)
                
                text = self.recognizer.recognize_google(audio)
                print(f"Done\nYou: {text}")
                return text
                
        except sr.WaitTimeoutError:
            print("(timeout)")
            return None
        except sr.UnknownValueError:
            print("(couldn't understand)")
            return None
        except sr.RequestError as e:
            print(f"(recognition error: {e})")
            return None
        except Exception as e:
            print(f"(error: {e})")
            return None
    
    def clear_cache(self):
        """Clear voice cache"""
        try:
            import shutil
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir)
            print("Voice cache cleared")
        except Exception as e:
            print(f"Failed to clear cache: {e}")
    
    def get_cache_size(self):
        """Get cache size in MB"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(self.cache_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
            return total_size / (1024 * 1024)
        except:
            return 0


class VoiceAssistant:
    """Voice wrapper with continuous wake word detection"""
    
    def __init__(self, jarvis_assistant, voice_enabled=True, voice_mode="hybrid", microphone_index=None):
        self.assistant = jarvis_assistant
        self.voice_enabled = voice_enabled
        self.voice = None
        self.wake_word = "jarvis"
        self.microphone_index = microphone_index
        
        if voice_enabled:
            try:
                self.voice = JarvisVoice(
                    voice_mode=voice_mode,
                    voice_samples_dir="./voice_samples",
                    microphone_index=microphone_index
                )
            except Exception as e:
                print(f"Voice init failed: {e}")
                self.voice_enabled = False
    
    def speak_response(self, text, user_query=""):
        """Stream response with smart voice selection"""
        if not self.voice_enabled or not self.voice:
            return
        
        try:
            self.voice.speak_streaming(text)
                
        except Exception as e:
            print(f"Speech failed: {e}")
    
    def voice_chat_loop(self):
        """Interactive voice conversation"""
        if not self.voice_enabled or not self.voice:
            print("Voice system not available")
            return
        
        self.voice.speak("Voice mode activated. How may I help you, sir?", wait=True)
        
        while True:
            user_input = self.voice.listen(timeout=10)
            
            if not user_input:
                continue
            
            if any(word in user_input.lower() for word in ['exit', 'goodbye', 'quit', 'stop']):
                self.voice.speak("Goodbye, sir.", wait=True)
                break
            
            print("\nJarvis: ", end="", flush=True)
            response = self.assistant.chat(user_input)
            print(response)
            
            self.speak_response(response, user_input)
    
    def wake_word_mode(self):
        """Continuous listening mode - processes commands immediately after wake word"""
        if not self.voice_enabled or not self.voice:
            print("Voice system not available")
            return
        
        self.voice.speak("Continuous listening activated. I'm ready, sir.", wait=True)
        print("\nListening continuously... Say 'Jarvis' followed by your command")
        print("(Press Ctrl+C to exit)\n")
        
        while True:
            try:
                # Continuously listen for any speech
                heard_text = self.voice.listen_continuous(timeout=None)
                
                if not heard_text:
                    continue
                
                # Check if wake word is present
                if self.wake_word in heard_text:
                    # Extract the command that came after the wake word
                    command = self.voice.extract_command_after_wake_word(heard_text, self.wake_word)
                    
                    if command:
                        print(f"\nDetected: {heard_text}")
                        print(f"Command: {command}")
                        
                        # Check for exit commands
                        if any(word in command.lower() for word in ['exit', 'goodbye', 'quit', 'stop', 'deactivate']):
                            self.voice.speak("Continuous listening deactivated.", wait=True)
                            break
                        
                        # Process the command immediately
                        print("\nJarvis: ", end="", flush=True)
                        response = self.assistant.chat(command)
                        print(response)
                        self.speak_response(response, command)
                        
                        print("\nListening...")
                    else:
                        # Wake word detected but no command followed
                        print(f"\nHeard: {heard_text}")
                        print("(No command detected after wake word)")
                        
            except KeyboardInterrupt:
                print("\n\nContinuous listening stopped.")
                break
            except Exception as e:
                print(f"\nError in wake word mode: {e}")
                continue
    
    def shutdown(self):
        """Cleanup"""
        if self.voice and hasattr(self.voice, 'pyttsx3_engine') and self.voice.pyttsx3_engine:
            self.voice.pyttsx3_engine.stop()