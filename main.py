"""
Jarvis AI Assistant - Main entry point with VOICE MODE
"""

import warnings
import sys
import os
import re

warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore::RuntimeWarning'

import subprocess
from src.assistant import JarvisAssistant

# Try to import voice system
try:
    from src.voice import VoiceAssistant
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("⚠️  Voice system not available (install: pip install SpeechRecognition pyttsx3 pyaudio)")


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
  help               - Show this message
  exit/quit          - Save and quit
"""
    
    if VOICE_AVAILABLE:
        help_text += """
Voice Commands:
  voice mode         - Enter continuous voice interaction mode
  wake word mode     - Always-listening mode (say 'Jarvis' to activate)
  test voice         - Test voice input and output
  list voices        - Show available TTS voices
  set voice [#]      - Change TTS voice (use number from 'list voices')
"""
    
    print(help_text)


def main():
    print("""
    ╔═══════════════════════════════════════╗
    ║              JARVIS AI                ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Check for voice mode flag
    voice_mode_start = '--voice' in sys.argv or '-v' in sys.argv
    wake_word_mode_start = '--wake' in sys.argv or '-w' in sys.argv
    
    # Verify Ollama
    print("Checking Ollama installation...")
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Ollama not found. Install from https://ollama.ai")
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
        return
    
    # Initialize voice assistant if available
    voice_assistant = None
    voice_available = VOICE_AVAILABLE  # Use the module-level variable
    if voice_available:
        try:
            voice_assistant = VoiceAssistant(assistant, voice_enabled=True)
            print("✓ Voice system ready!")
        except Exception as e:
            print(f"⚠️  Voice system failed: {e}")
            voice_available = False
    
    print("\nMode Options:")
    print("  [1] Text Mode (type commands)")
    if VOICE_AVAILABLE:
        print("  [2] Voice Mode (speak naturally)")
        print("  [3] Wake Word Mode (always listening)")
    print("\nTips:")
    print("  - Type 'help' to see all commands")
    print("  - Watch for [*] when Jarvis learns something new")
    
    # Auto-start voice mode if flag present
    if VOICE_AVAILABLE and voice_mode_start:
        print("\n🎤 Starting in Voice Mode...")
        time.sleep(1)
        voice_assistant.voice_chat_loop()
        assistant.shutdown()
        return
    elif VOICE_AVAILABLE and wake_word_mode_start:
        print("\n🎤 Starting in Wake Word Mode...")
        time.sleep(1)
        voice_assistant.wake_word_mode()
        assistant.shutdown()
        return
    
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
            
            # Voice mode commands
            if VOICE_AVAILABLE:
                if user_input.lower() == 'voice mode':
                    print("\n🎤 Entering Voice Mode...")
                    print("Tip: Say 'exit' or 'goodbye' to return to text mode\n")
                    voice_assistant.voice_chat_loop()
                    print("\n✓ Returned to text mode")
                    continue
                
                if user_input.lower() in ['wake word mode', 'wake mode']:
                    print("\n🎤 Entering Wake Word Mode...")
                    print("Tip: Say 'Jarvis' followed by your command\n")
                    voice_assistant.wake_word_mode()
                    print("\n✓ Returned to text mode")
                    continue
                
                if user_input.lower() == 'test voice':
                    print("\nTesting voice system...")
                    voice_assistant.voice.speak("Voice test. I am Jarvis, sir.", wait=True)
                    print("Now say something:")
                    text = voice_assistant.voice.listen(timeout=5)
                    if text:
                        print(f"✓ Recognized: {text}")
                        voice_assistant.voice.speak(f"You said: {text}", wait=True)
                    continue
                
                if user_input.lower() == 'list voices':
                    voice_assistant.voice.list_available_voices()
                    continue
                
                if user_input.lower().startswith('set voice '):
                    try:
                        voice_num = int(user_input.split()[2])
                        if voice_assistant.voice.set_voice_by_number(voice_num):
                            voice_assistant.voice.speak("Voice changed successfully.", wait=True)
                    except:
                        print("Usage: set voice [number]")
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
                    print(f"\n✓ Training data exported to: {filepath}")
                except Exception as e:
                    print(f"\n❌ Export failed: {e}")
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
                print("✓ Conversation history cleared (memories preserved)")
                continue
            
            # Normal chat
            print("Jarvis: ", end="", flush=True)
            response = assistant.chat(user_input)
            print(response)
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
    import time
    main()