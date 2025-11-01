import warnings
import sys
import os
import re

warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore::RuntimeWarning'

import subprocess
from src.assistant import JarvisAssistant

# Try to import voice system
VOICE_AVAILABLE = False
try:
    from src.voice import VoiceAssistant, list_microphones
    VOICE_AVAILABLE = True
except ImportError:
    pass


def print_help():
    """Show available commands"""
    help_text = """
Available Commands:
  news               - Get today's news summary from reputable sources
  more [#/topic]     - Get details on a news topic (e.g., 'more 5' or 'more bitcoin')
  stats              - Show detailed memory statistics
  personality        - Show personality development status
  set [trait] [val]  - Adjust personality trait (e.g., 'set humor 50')
  show facts         - Display all stored facts (last 10)
  export             - Export training data for fine-tuning
  learn on/off       - Toggle auto-learning on or off
  remember [msg]     - Manually remember something
  clear              - Clear conversation history (memory preserved)
  list apps          - Show all apps Jarvis can open
  help               - Show this message
  exit/quit          - Save and quit

App Launcher:
  open [app]         - Open an application (e.g., 'open google', 'open vscode')
"""
    
    if VOICE_AVAILABLE:
        help_text += """
Voice Commands:
  voice on/off       - Toggle voice responses in text mode
  voice mode         - Enter continuous voice interaction mode
  wake word mode     - Always-listening mode (say 'Jarvis' to activate)
  test voice         - Test voice system
"""
    
    print(help_text)


def main():
    print("""
    ╔══════════════════════════════════════╗
    ║              JARVIS AI                ║
    ╚══════════════════════════════════════╝
    """)
    
    # Check for voice mode flag
    voice_mode_start = '--voice' in sys.argv or '-v' in sys.argv
    wake_word_mode_start = '--wake' in sys.argv or '-w' in sys.argv or len(sys.argv) == 1  # Default to wake word mode
    
    # Verify Ollama
    print("Checking Ollama installation...")
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True)
        print("Ollama found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Ollama not found. Install from https://ollama.ai")
        input("\nPress Enter to exit...")
        return
    
    # Initialize assistant
    print("Initializing Jarvis...")
    try:
        assistant = JarvisAssistant(debug=False)
        
        # Show initial stats
        stats = assistant.get_memory_stats()
        print(f"\nMemory System Ready:")
        print(f"   Total facts: {stats['total_facts']}")
        print(f"   Storage: {stats['storage_backend']}")
        
    except Exception as e:
        print(f"\nFailed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Initialize voice assistant if available
    voice_assistant = None
    microphone_index = None
    
    if VOICE_AVAILABLE:
        try:
            # List available microphones
            print("\nAvailable microphones:")
            mic_list = list_microphones()
            
            if mic_list:
                # Look for webcam or default
                default_index = None
                for idx, name in mic_list:
                    if 'webcam' in name.lower() or 'camera' in name.lower():
                        default_index = idx
                        print(f"\nUsing microphone: {name}")
                        break
                
                if default_index is None and mic_list:
                    default_index = mic_list[0][0]
                    print(f"\nUsing default microphone: {mic_list[0][1]}")
                
                microphone_index = default_index
            
            voice_assistant = VoiceAssistant(
                assistant, 
                voice_enabled=True, 
                voice_mode="hybrid",
                microphone_index=microphone_index
            )
        except Exception as e:
            print(f"Warning: Voice system failed to initialize: {e}")
            print("Voice features will be disabled")
            voice_assistant = None
    else:
        print("\nVoice system not available - text mode only")
    
    
    if voice_assistant:
        print("\nVoice mode available.")
        print("Starting wake word mode...")
        import time
        time.sleep(1)
        voice_assistant.wake_word_mode()
        assistant.shutdown()
        return
    
    # Only show text mode prompt if no voice
    print("\nType 'help' for commands.")
    print("\n" + "-" * 60)
    
    # Main conversation loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            # Exit commands
            if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                assistant.shutdown()
                if voice_assistant:
                    voice_assistant.shutdown()
                break
            
            # Help command
            if user_input.lower() == 'help':
                print_help()
                continue
            
            # List apps command
            if user_input.lower() == 'list apps':
                print("\nAvailable Applications:")
                for app_info in assistant.app_launcher.list_apps():
                    print(f"  {app_info}")
                continue
            
            # Voice toggle commands
            if user_input.lower() == 'voice on':
                if voice_assistant:
                    voice_assistant.voice_enabled = True
                    print("Voice responses enabled (hybrid mode)")
                    if voice_assistant.voice:
                        voice_assistant.voice.speak("Voice responses enabled, sir.", wait=True)
                else:
                    print("Voice system not available")
                continue
            
            if user_input.lower() == 'voice off':
                if voice_assistant:
                    if voice_assistant.voice:
                        voice_assistant.voice.speak("Voice responses disabled, sir.", wait=True)
                    voice_assistant.voice_enabled = False
                    print("Voice responses disabled")
                else:
                    print("Voice system not available")
                continue
            
            # Voice mode commands
            if voice_assistant:
                if user_input.lower() == 'voice mode':
                    print("\nEntering Voice Mode...")
                    print("Tip: Say 'exit' or 'goodbye' to return to text mode\n")
                    voice_assistant.voice_chat_loop()
                    print("\nReturned to text mode")
                    continue
                
                if user_input.lower() in ['wake word mode', 'wake mode']:
                    print("\nEntering Wake Word Mode...")
                    print("Tip: Say 'Jarvis' followed by your command\n")
                    voice_assistant.wake_word_mode()
                    print("\nReturned to text mode")
                    continue
                
                if user_input.lower() == 'test voice':
                    print("\nTesting voice system...")
                    voice_assistant.voice.speak("Voice test. I am Jarvis, sir.", wait=True)
                    print("Now say something:")
                    text = voice_assistant.voice.listen(timeout=5)
                    if text:
                            print(f"Recognized: {text}")
                            voice_assistant.voice.speak(f"You said: {text}", wait=True)
                    continue
            
            # Stats command
            if user_input.lower() == 'stats':
                stats = assistant.get_memory_stats()
                print(f"\nMemory Statistics:")
                print(f"   Total facts stored: {stats['total_facts']}")
                print(f"   Learned this session: {stats['learned_this_session']}")
                
                if stats.get('by_category'):
                    print(f"\nFacts by Category:")
                    for category, count in stats['by_category'].items():
                        print(f"      {category}: {count}")
                continue
            
            # Personality command
            if user_input.lower() == 'personality':
                if hasattr(assistant, 'personality') and assistant.personality:
                    personality = assistant.personality.get_personality_summary()
                    print(f"\nPersonality Status:")
                    print(f"   Development: {personality['development_stage']}")
                    print(f"   Total interactions: {personality['interactions']}")
                    
                    print(f"\nCurrent Traits:")
                    for trait, value in personality['traits'].items():
                        bar = '█' * (value // 5) + '░' * (20 - value // 5)
                        print(f"   {trait.capitalize():12} [{bar}] {value}/100")
                else:
                    print("\nPersonality system not initialized.")
                continue
            
            # Set trait command
            if user_input.lower().startswith('set '):
                if hasattr(assistant, 'personality') and assistant.personality:
                    parts = user_input.split()
                    if len(parts) >= 3:
                        trait = parts[1]
                        value = parts[2]
                        success, message = assistant.personality.adjust_trait(trait, value)
                        print(f"\n{message}")
                    else:
                        print("\nUsage: set [trait] [value]")
                else:
                    print("\nPersonality system not initialized.")
                continue
            
            # Show facts command
            if user_input.lower() == 'show facts':
                facts = assistant.memory.storage.get_all_facts()
                if facts:
                    print(f"\nStored Facts ({len(facts)} total):")
                    for i, fact in enumerate(facts[-10:], 1):
                        print(f"   {i}. [{fact['category']}] {fact['fact']}")
                else:
                    print("\nNo facts stored yet!")
                continue
            
            # Export command
            if user_input.lower() == 'export':
                try:
                    filepath = assistant.export_for_finetuning()
                    print(f"\nTraining data exported to: {filepath}")
                except Exception as e:
                    print(f"\nExport failed: {e}")
                continue
            
            # Learn toggle command
            if user_input.lower().startswith('learn '):
                command = user_input.lower().split()[1]
                if command == 'on':
                    assistant.toggle_learning(True)
                elif command == 'off':
                    assistant.toggle_learning(False)
                else:
                    print("Usage: 'learn on' or 'learn off'")
                continue
            
            # Remember command
            if user_input.lower().startswith('remember '):
                fact = user_input[9:].strip()
                if fact:
                    success = assistant.memory.remember_fact_manually(fact, "user_specified")
                    if success:
                        print(f"[*] Remembered: {fact}")
                    else:
                        print(f"Already knew that!")
                else:
                    print("Usage: remember [something to remember]")
                continue
            
            # Clear conversation command
            if user_input.lower() == 'clear':
                assistant.conversation_history = []
                print("Conversation history cleared (memories preserved)")
                continue
            
            # Normal chat
            print("Jarvis: ", end="", flush=True)
            response = assistant.chat(user_input)
            print(response)
            
            # Hybrid voice: Pass user query for smart voice selection
            if voice_assistant and voice_assistant.voice_enabled:
                voice_assistant.speak_response(response, user_query=user_input)
            
            print("\n" + "-" * 60)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Saving...")
            assistant.shutdown()
            if voice_assistant:
                voice_assistant.shutdown()
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()