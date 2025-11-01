"""
Voice Assistant - Using Piper TTS for lightning-fast, high-quality speech
Windows-compatible version with automatic setup
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")
import subprocess
import wave
import json
import platform

# Audio playback
AUDIO_PLAYBACK = False
try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_PLAYBACK = True
except ImportError:
    pass

# Speech recognition
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


class PiperVoice:
    """Lightning-fast TTS using Piper"""
    
    def __init__(self, model_name="en_GB-alan-medium", microphone_index=None):
        self.model_name = model_name
        self.microphone_index = microphone_index
        self.system = platform.system()
        self.piper_path = self._find_piper()
        
        # Models directory
        if self.system == "Windows":
            self.models_dir = os.path.join(os.path.dirname(__file__), "..", "piper_models")
        else:
            self.models_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "piper-tts")
        
        # Available British voices (download automatically)
        self.available_voices = {
            "alan-low": "en_GB-alan-low",        # Fast, lighter voice
            "alan-medium": "en_GB-alan-medium",  # Standard British
            "northern-male": "en_GB-northern_english_male-medium",  # Deep, closest to Jarvis
            "semaine": "en_GB-semaine-medium",   # Professional British male
            "cori": "en_GB-cori-medium",         # Alternative British male
            "alba-medium": "en_GB-alba-medium",  # Female alternative
            "jenny-medium": "en_GB-jenny_dioco-medium",  # Female, expressive
        }
        
        # Initialize the model
        self._ensure_model_downloaded()
        
        # Initialize speech recognition
        self.recognizer = None
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 4000
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 1.5
    
    def _find_piper(self):
        """Find or guide user to install piper"""
        # Windows executable name
        exe_name = "piper.exe" if self.system == "Windows" else "piper"
        
        # Get absolute paths - try multiple methods
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        
        # Also try from current working directory (often more reliable)
        cwd = os.getcwd()
        
        # Check project directory first (./piper/ or ./piper_windows/)
        possible_locations = [
            os.path.join(cwd, "piper", exe_name),  # Try CWD first
            os.path.join(project_dir, "piper", exe_name),
            os.path.join(project_dir, "piper_windows", exe_name),
            os.path.join(project_dir, exe_name),
            os.path.join(cwd, "piper_windows", exe_name),
            os.path.join(cwd, exe_name),
        ]
        
        # Debug: show what we're checking
        print(f"[DEBUG] Looking for Piper in these locations:")
        for path in possible_locations:
            exists = "✓" if os.path.exists(path) else "✗"
            print(f"  {exists} {path}")
            if os.path.exists(path):
                print(f"✓ Found Piper at: {path}")
                return os.path.abspath(path)  # Return absolute path
        
        # Check PATH
        try:
            result = subprocess.run([exe_name, "--version"], 
                                   capture_output=True, 
                                   text=True, 
                                   timeout=5)
            if result.returncode == 0:
                return exe_name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Check system locations (Linux/Mac)
        if self.system != "Windows":
            system_paths = [
                os.path.expanduser("~/.local/bin/piper"),
                "/usr/local/bin/piper",
                "/usr/bin/piper",
            ]
            for path in system_paths:
                if os.path.exists(path):
                    return path
        
        # Not found - provide instructions
        print("\n" + "="*60)
        print("⚠️  PIPER TTS NOT FOUND")
        print("="*60)
        
        if self.system == "Windows":
            print("\nQuick Setup for Windows:")
            print("  1. Download: https://github.com/rhasspy/piper/releases/latest")
            print("     Look for: piper_windows_amd64.zip")
            print("  2. Extract the ZIP file")
            print("  3. Move the 'piper' folder to your project directory:")
            print(f"     {project_dir}")
            print("     (Should have: piper/piper.exe)")
            print("\nOR simply extract and run again - I'll find it!")
        else:
            print("\nSetup for Linux/Mac:")
            print("  1. Download: https://github.com/rhasspy/piper/releases/latest")
            print("  2. Extract and move 'piper' binary to ~/.local/bin/")
            print("     OR use: pip install piper-tts")
        
        print("\nAfter installing, run the program again.")
        print("="*60 + "\n")
        
        raise Exception("Piper TTS not found. Please install it first.")
    
    def _ensure_model_downloaded(self):
        """Download model if not present"""
        model_path = os.path.join(self.models_dir, f"{self.model_name}.onnx")
        config_path = os.path.join(self.models_dir, f"{self.model_name}.onnx.json")
        
        if os.path.exists(model_path) and os.path.exists(config_path):
            return True
        
        os.makedirs(self.models_dir, exist_ok=True)
        
        print(f"\n📥 Downloading Piper voice model: {self.model_name}")
        print("   (This only happens once, ~20-30 MB)")
        
        # Download URLs - HuggingFace format
        # Model name format: en_GB-alan-medium
        # URL format: https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/
        
        lang_region = self.model_name.split('-')[0]  # e.g., en_GB
        voice_name_quality = '-'.join(self.model_name.split('-')[1:])  # e.g., alan-medium
        
        base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{lang_region.split('_')[0]}/{lang_region}/{voice_name_quality.replace('-', '/')}/"
        model_url = f"{base_url}{self.model_name}.onnx"
        config_url = f"{base_url}{self.model_name}.onnx.json"
        
        try:
            import urllib.request
            
            print("   Downloading model file...", end=" ", flush=True)
            urllib.request.urlretrieve(model_url, model_path)
            print("✓")
            
            print("   Downloading config file...", end=" ", flush=True)
            urllib.request.urlretrieve(config_url, config_path)
            print("✓")
            
            print("   Model ready!\n")
            return True
            
        except Exception as e:
            print(f"\n   ✗ Download failed: {e}")
            print("\n   Manual download:")
            print(f"   1. Model: {model_url}")
            print(f"      Save to: {model_path}")
            print(f"   2. Config: {config_url}")
            print(f"      Save to: {config_path}")
            raise
    
    def speak(self, text, wait=True):
        """Generate and play speech"""
        if not text:
            return
        
        temp_file = "./temp_speech.wav"
        
        try:
            # Generate speech with Piper (lightning fast!)
            model_path = os.path.join(self.models_dir, f"{self.model_name}.onnx")
            
            cmd = [
                self.piper_path,
                "--model", model_path,
                "--output_file", temp_file
            ]
            
            # Run piper
            result = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                timeout=10
            )
            
            if result.returncode != 0:
                print(f"Piper error: {result.stderr}")
                return
            
            # Play audio with proper blocking
            if AUDIO_PLAYBACK and os.path.exists(temp_file):
                # Stop any currently playing audio first
                sd.stop()
                
                data, samplerate = sf.read(temp_file)
                
                # Always use blocking playback for sentences
                sd.play(data, samplerate)
                sd.wait()  # Block until playback finishes
            
            # Cleanup
            try:
                os.remove(temp_file)
            except:
                pass
                
        except subprocess.TimeoutExpired:
            print("Speech generation timeout")
        except Exception as e:
            print(f"Speech error: {e}")
    
    def speak_streaming(self, text):
        """Stream response sentence by sentence with proper waiting"""
        if not text:
            return
        
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            # Always wait for each sentence to finish before starting the next
            self.speak(sentence.strip(), wait=True)
    
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
    
    def change_voice(self, voice_name):
        """Change to a different voice"""
        if voice_name not in self.available_voices:
            print(f"Voice '{voice_name}' not found.")
            print(f"Available voices: {', '.join(self.available_voices.keys())}")
            return False
        
        self.model_name = self.available_voices[voice_name]
        self._ensure_model_downloaded()
        return True
    
    def list_voices(self):
        """List available voices"""
        print("\nAvailable Piper voices:")
        for name, model in self.available_voices.items():
            current = " (current)" if model == self.model_name else ""
            print(f"  - {name}{current}")


class VoiceAssistant:
    """Voice wrapper for Jarvis with Piper TTS"""
    
    def __init__(self, jarvis_assistant, voice_enabled=True, voice_mode="piper", microphone_index=None):
        self.assistant = jarvis_assistant
        self.voice_enabled = voice_enabled
        self.voice = None
        self.wake_word = "jarvis"
        self.microphone_index = microphone_index
        
        if voice_enabled:
            try:
                self.voice = PiperVoice(microphone_index=microphone_index)
                print("✓ Piper TTS initialized (lightning fast!)")
            except Exception as e:
                print(f"Voice init failed: {e}")
                self.voice_enabled = False
    
    def speak_response(self, text, user_query=""):
        """Speak the response"""
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
        """Continuous listening mode"""
        if not self.voice_enabled or not self.voice:
            print("Voice system not available")
            return
        
        self.voice.speak("Continuous listening activated. I'm ready, sir.", wait=True)
        print("\nListening continuously... Say 'Jarvis' followed by your command")
        print("(Press Ctrl+C to exit)\n")
        
        while True:
            try:
                heard_text = self.voice.listen_continuous(timeout=None)
                
                if not heard_text:
                    continue
                
                if self.wake_word in heard_text:
                    command = self.voice.extract_command_after_wake_word(heard_text, self.wake_word)
                    
                    if command:
                        print(f"\nDetected: {heard_text}")
                        print(f"Command: {command}")
                        
                        if any(word in command.lower() for word in ['exit', 'goodbye', 'quit', 'stop', 'deactivate']):
                            self.voice.speak("Continuous listening deactivated.", wait=True)
                            break
                        
                        print("\nJarvis: ", end="", flush=True)
                        response = self.assistant.chat(command)
                        print(response)
                        self.speak_response(response, command)
                        
                        print("\nListening...")
                    else:
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
        pass