"""
Jarvis AI Assistant - Main entry point
"""

import subprocess
from src.assistant import JarvisAssistant


def verify_ollama():
    """Check if Ollama is installed and running"""
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Ollama is not installed or not running")
        print("Please install Ollama from https://ollama.ai")
        return False


def main():
    print("""
    ╔═══════════════════════════════════════╗
    ║   JARVIS AI ASSISTANT v2.0            ║
    ║   Created by Andre S                  ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Verify Ollama
    if not verify_ollama():
        return
    
    # Initialize assistant
    try:
        assistant = JarvisAssistant()
    except Exception as e:
        print(f"\nFailed to initialize assistant: {e}")
        return
    
    print("💡 Tips:")
    print("  - Ask about weather: 'What's the weather in New York?'")
    print("  - Current events: 'latest news' or 'who is the president?'")
    print("  - General questions: 'What is Python?'")
    print("  - Type 'exit' to quit\n")
    print("-" * 50)
    
    # Main conversation loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                print("\nJarvis: Goodbye! Have a great day!")
                break
            
            if not user_input:
                continue
            
            print("\nJarvis: ", end="", flush=True)
            response = assistant.chat(user_input)
            print(response)
            print("\n" + "-" * 50)
            
        except KeyboardInterrupt:
            print("\n\nJarvis: Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    main()