"""
Jarvis AI Assistant - Main entry point
Modular system with easy upgrades!
"""

import warnings
import sys
import os
import re

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
        print("❌ Ollama not found. Install from https://ollama.ai")
        return False


def print_help():
    """Show available commands"""
    print("""
Available Commands:
  news               - Get today's news summary from reputable sources
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
    """)


def is_personality_adjustment(user_input):
    """Check if the input is trying to adjust personality"""
    user_lower = user_input.lower()
    
    # Check for personality adjustment patterns
    adjustment_patterns = [
        r'(increase|raise|boost|up|higher)\s+(.*?)\s+to\s+(\d+)',
        r'(decrease|lower|reduce|down)\s+(.*?)\s+to\s+(\d+)',
        r'make\s+(.*?)\s+(more|less|higher|lower)',
        r'set\s+(.*?)\s+to\s+(\d+)',
    ]
    
    for pattern in adjustment_patterns:
        if re.search(pattern, user_lower):
            return True
    
    return False


def parse_personality_command(user_input):
    """Parse natural language personality adjustments"""
    user_lower = user_input.lower()
    
    # Available traits
    traits = ['formality', 'humor', 'verbosity', 'enthusiasm', 'directness', 'empathy']
    
    # Pattern 1: "increase/raise humor to 60"
    match = re.search(r'(increase|raise|boost|up|higher)\s+(.*?)\s+to\s+(\d+)', user_lower)
    if match:
        trait = match.group(2).strip()
        value = match.group(3)
        for t in traits:
            if t in trait:
                return t, value
    
    # Pattern 2: "decrease/lower humor to 40"
    match = re.search(r'(decrease|lower|reduce|down)\s+(.*?)\s+to\s+(\d+)', user_lower)
    if match:
        trait = match.group(2).strip()
        value = match.group(3)
        for t in traits:
            if t in trait:
                return t, value
    
    # Pattern 3: "set humor to 50" or "set humor 50"
    match = re.search(r'set\s+(\w+)\s+(?:to\s+)?(\d+)', user_lower)
    if match:
        trait = match.group(1).strip()
        value = match.group(2)
        for t in traits:
            if t in trait:
                return t, value
    
    # Pattern 4: "make humor higher/lower"
    match = re.search(r'make\s+(\w+)\s+(more|less|higher|lower)', user_lower)
    if match:
        trait = match.group(1).strip()
        direction = match.group(2)
        for t in traits:
            if t in trait:
                # Get current value and adjust
                return t, None  # Signal that we need to get current value
    
    return None, None


def main():
    print("""
    ╔═══════════════════════════════════════╗
    ║              JARVIS AI                ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Verify Ollama
    print("Checking Ollama installation...")
    if not verify_ollama():
        print("\n❌ Ollama check failed. Please make sure Ollama is installed and running.")
        print("Download from: https://ollama.ai")
        print("\nAfter installing, run: ollama pull qwen2.5:14b")
        input("\nPress Enter to exit...")
        return
    
    # Initialize assistant
    print("Initializing Jarvis...")
    try:
        # Check if personality module exists
        try:
            from src.personality import PersonalityEngine
            personality_available = True
        except ImportError:
            personality_available = False
            print("Note: Personality system not available (personality.py not found)")
        
        # Enable debug mode temporarily
        assistant = JarvisAssistant(debug=True)
        
        # Show initial stats
        stats = assistant.get_memory_stats()
        print(f"\nMemory System Ready:")
        print(f"   Total facts: {stats['total_facts']}")
        print(f"   Storage: {stats['storage_backend']}")
        print(f"   Learning engines: {len(stats['learning_engines'])}")
        if stats['semantic_search']:
            print(f"   Semantic search: enabled")
        else:
            print(f"   Semantic search: disabled")
        
    except Exception as e:
        print(f"\nFailed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\nTips:")
    print("  - Just chat naturally - Jarvis learns automatically")
    print("  - Type 'help' to see all commands")
    print("  - Watch for [*] when Jarvis learns something new")
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
            
            # Personality command
            if user_input.lower() == 'personality':
                if hasattr(assistant, 'personality') and assistant.personality:
                    personality = assistant.personality.get_personality_summary()
                    print(f"\nPersonality Status:")
                    print(f"   Development: {personality['development_stage']}")
                    print(f"   Total interactions: {personality['interactions']}")
                    print(f"   Manual adjustments: {personality['manual_adjustments']}")
                    print(f"\nCurrent Traits:")
                    for trait, value in personality['traits'].items():
                        bar = '█' * (value // 5) + '░' * (20 - value // 5)
                        print(f"   {trait.capitalize():12} [{bar}] {value}/100")
                    print(f"\nDominant Traits:")
                    for trait in personality['dominant_traits']:
                        print(f"   - {trait}")
                    print(f"\nTip: Use 'set [trait] [value]' to adjust (e.g., 'set humor 50')")
                else:
                    print("\nPersonality system not initialized. Please restart Jarvis.")
                continue
            
            # Set trait command - now supports natural language!
            if user_input.lower().startswith('set ') or is_personality_adjustment(user_input):
                if hasattr(assistant, 'personality') and assistant.personality:
                    # Try to parse natural language first
                    trait, value = parse_personality_command(user_input)
                    
                    if trait and value:
                        success, message = assistant.personality.adjust_trait(trait, value)
                        if success:
                            print(f"\n[*] {message}")
                            print(f"    This setting will be preserved across sessions.")
                        else:
                            print(f"\nError: {message}")
                    else:
                        print("\nUsage: set [trait] [value]")
                        print("Or say naturally: 'increase humor to 60', 'lower formality to 75', etc.")
                        print(f"Available traits: formality, humor, verbosity, enthusiasm, directness, empathy")
                else:
                    print("\nPersonality system not initialized. Please restart Jarvis.")
                continue
            
            # Show facts command
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
                    print(f"\nTraining data exported to: {filepath}")
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
            print("\n" + "-" * 60)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Saving...")
            assistant.shutdown()
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            import traceback
            traceback.print_exc()
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    main()