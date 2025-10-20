"""
Jarvis AI Assistant - Main entry point
Modular system with easy upgrades!
"""

import warnings
import sys
import os

warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore::RuntimeWarning'
if not sys.warnoptions:
    warnings.simplefilter("ignore")

import subprocess
from src.assistant import JarvisAssistant


def verify_ollama():
    """Check if Ollama is running"""
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Ollama not found. Install from https://ollama.ai")
        return False


def print_help():
    """Show available commands"""
    print("""
Available Commands:
  stats          - Show detailed memory statistics
  show facts     - Display all stored facts (last 10)
  export         - Export training data for fine-tuning
  learn on/off   - Toggle auto-learning on or off
  remember [msg] - Manually remember something
  clear          - Clear conversation history (memory preserved)
  help           - Show this message
  exit/quit      - Save and quit
    """)


def main():
    print("""
    ╔═══════════════════════════════════════╗
    ║   JARVIS AI - Modular Edition         ║
    ║   Created by Andre S                  ║
    ║   Version 2.0 - Future-Proof          ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Verify Ollama
    if not verify_ollama():
        return
    
    # Initialize assistant
    print("Initializing Jarvis...")
    try:
        # Enable debug mode temporarily
        assistant = JarvisAssistant(debug=True)
        
        # Show initial stats
        stats = assistant.get_memory_stats()
        print(f"\nMemory System Ready:")
        print(f"   Total facts: {stats['total_facts']}")
        print(f"   Storage: {stats['storage_backend']}")
        print(f"   Learning engines: {len(stats['learning_engines'])}")
        print(f"   Semantic search: {'✓' if stats['semantic_search'] else '✗ (install: pip install sentence-transformers)'}")
        
    except Exception as e:
        print(f"\nFailed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\nTips:")
    print("  - Just chat naturally! Jarvis learns automatically 🧠")
    print("  - Type 'help' to see all commands")
    print("  - Watch for 🧠 icon when Jarvis learns something")
    print("  - Your conversations are auto-exported for future fine-tuning")
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
                break
            
            # Help command
            if user_input.lower() == 'help':
                print_help()
                continue
            
            # Stats command
            if user_input.lower() == 'stats':
                stats = assistant.get_memory_stats()
                print(f"\nMemory Statistics:")
                print(f"   Total facts stored: {stats['total_facts']}")
                print(f"   Learned this session: {stats['learned_this_session']}")
                print(f"   Storage backend: {stats['storage_backend']}")
                print(f"   Semantic search: {'Enabled' if stats['semantic_search'] else 'Disabled'}")
                
                if stats.get('by_category'):
                    print(f"\nFacts by Category:")
                    for category, count in stats['by_category'].items():
                        print(f"      {category}: {count}")
                
                if stats.get('by_learning_engine'):
                    print(f"\nLearning Methods Used:")
                    for engine, count in stats['by_learning_engine'].items():
                        engine_name = engine.replace('Learning', '')
                        print(f"      {engine_name}: {count} facts")
                
                continue
            
            # Show facts command (NEW - for debugging)
            if user_input.lower() == 'show facts':
                facts = assistant.memory.storage.get_all_facts()
                if facts:
                    print(f"\nAll Stored Facts ({len(facts)} total):")
                    for i, fact in enumerate(facts[-10:], 1):  # Show last 10
                        print(f"   {i}. [{fact['category']}] {fact['fact']}")
                else:
                    print("\nNo facts stored yet!")
                continue
            
            # Export command
            if user_input.lower() == 'export':
                try:
                    filepath = assistant.export_for_finetuning()
                    print(f"\n✓ Training data exported to: {filepath}")
                    print("  Ready for fine-tuning when you need it!")
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
                        print(f"✓ Remembered: {fact}")
                    else:
                        print(f"ℹ️ Already knew that!")
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
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    main()