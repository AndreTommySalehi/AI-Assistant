"""
Application Launcher - Open apps via voice/text commands
Supports custom app configurations with multiple launch methods
"""

import subprocess
import platform
import os
import json
import webbrowser


class AppLauncher:
    """Launch applications and websites"""
    
    def __init__(self, config_file="./jarvis_data/apps_config.json"):
        self.config_file = config_file
        self.system = platform.system()
        self.apps = self._load_config()
    
    def _load_config(self):
        """Load app configurations from file"""
        # Default apps
        default_apps = {
            "google": {
                "type": "website",
                "url": "https://www.google.com",
                "aliases": ["google", "search"]
            },
            "github": {
                "type": "website",
                "url": "https://github.com",
                "aliases": ["github", "git hub"]
            },
            "notes": {
                "type": "app",
                "windows": "notepad.exe",
                "mac": "open -a Notes",
                "linux": "gnome-text-editor",
                "aliases": ["notes", "notepad", "note"]
            },
            "vscode": {
                "type": "app",
                "windows": "code",
                "mac": "open -a 'Visual Studio Code'",
                "linux": "code",
                "aliases": ["vscode", "vs code", "visual studio code", "code editor"]
            },
            "chrome": {
                "type": "app",
                "windows": "start chrome",
                "mac": "open -a 'Google Chrome'",
                "linux": "google-chrome",
                "aliases": ["chrome", "google chrome", "browser"]
            },
            "calculator": {
                "type": "app",
                "windows": "calc.exe",
                "mac": "open -a Calculator",
                "linux": "gnome-calculator",
                "aliases": ["calculator", "calc"]
            },
            "spotify": {
                "type": "app",
                "windows": "start spotify",
                "mac": "open -a Spotify",
                "linux": "spotify",
                "aliases": ["spotify", "music"]
            },
            "discord": {
                "type": "app",
                "windows": "start discord",
                "mac": "open -a Discord",
                "linux": "discord",
                "aliases": ["discord"]
            }
        }
        
        # Create config file if it doesn't exist
        if not os.path.exists(self.config_file):
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(default_apps, f, indent=2)
            return default_apps
        
        # Load existing config
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except:
            return default_apps
    
    def save_config(self):
        """Save current app configurations"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.apps, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False
    
    def add_app(self, name, app_type, command_or_url, aliases=None):
        """Add a new app to the configuration"""
        if aliases is None:
            aliases = [name.lower()]
        
        app_config = {
            "type": app_type,
            "aliases": aliases
        }
        
        if app_type == "website":
            app_config["url"] = command_or_url
        else:
            # For apps, store platform-specific commands
            if self.system == "Windows":
                app_config["windows"] = command_or_url
            elif self.system == "Darwin":
                app_config["mac"] = command_or_url
            else:
                app_config["linux"] = command_or_url
        
        self.apps[name.lower()] = app_config
        self.save_config()
        return True
    
    def can_handle(self, user_input):
        """Check if input is an app launch command"""
        user_lower = user_input.lower().strip()
        
        # Must contain an "open" type keyword
        has_open_keyword = any(word in user_lower for word in ['open', 'launch', 'start', 'run'])
        
        if not has_open_keyword:
            return False
        
        # Must mention an app name or alias
        for app_name, app_config in self.apps.items():
            aliases = app_config.get('aliases', [app_name])
            for alias in aliases:
                # Check for whole word match
                if f" {alias} " in f" {user_lower} " or user_lower.startswith(alias + " ") or user_lower.endswith(" " + alias) or user_lower == alias:
                    return True
        
        return False
    
    def extract_app_name(self, user_input):
        """Extract app name from user input"""
        user_lower = user_input.lower().strip()
        
        # Remove common command words first
        for word in ['please', 'can you', 'could you', 'would you', 'just', 'now']:
            user_lower = user_lower.replace(word, '').strip()
        
        # Find matching app by checking each alias
        for app_name, app_config in self.apps.items():
            aliases = app_config.get('aliases', [app_name])
            for alias in aliases:
                # Check if alias appears in the input
                # Use word boundaries to avoid partial matches
                if f" {alias} " in f" {user_lower} " or user_lower.startswith(alias + " ") or user_lower.endswith(" " + alias) or user_lower == alias:
                    return app_name
        
        return None
    
    def open_app(self, app_name):
        """Open the specified application"""
        app_name = app_name.lower()
        
        if app_name not in self.apps:
            return False, f"I don't know how to open {app_name}"
        
        app_config = self.apps[app_name]
        app_type = app_config.get('type', 'app')
        
        try:
            if app_type == "website":
                # Open website in default browser
                url = app_config.get('url', '')
                if url:
                    webbrowser.open(url)
                    print(f"[DEBUG] Opened website: {url}")
                    return True, f"Opening {app_name}"
                else:
                    return False, f"No URL configured for {app_name}"
            
            else:
                # Open application
                command = None
                
                if self.system == "Windows":
                    command = app_config.get('windows')
                elif self.system == "Darwin":
                    command = app_config.get('mac')
                else:
                    command = app_config.get('linux')
                
                if not command:
                    return False, f"No command configured for {app_name} on {self.system}"
                
                print(f"[DEBUG] Executing command: {command}")
                
                # Execute command
                if self.system == "Windows":
                    subprocess.Popen(command, shell=True)
                else:
                    subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                return True, f"Opening {app_name}"
        
        except Exception as e:
            print(f"[DEBUG] Error opening {app_name}: {e}")
            return False, f"Failed to open {app_name}: {str(e)}"
    
    def handle_command(self, user_input):
        """Handle an app launch command"""
        app_name = self.extract_app_name(user_input)
        
        if not app_name:
            return False, "I couldn't identify which app to open"
        
        return self.open_app(app_name)
    
    def list_apps(self):
        """List all available apps"""
        apps_list = []
        for app_name, app_config in self.apps.items():
            app_type = app_config.get('type', 'app')
            aliases = app_config.get('aliases', [app_name])
            apps_list.append(f"{app_name.capitalize()} ({app_type}) - aliases: {', '.join(aliases)}")
        
        return apps_list
    
    def get_help_text(self):
        """Get help text for app launcher"""
        help_lines = [
            "\nApp Launcher Commands:",
            "  open [app]     - Open an application or website",
            "  list apps      - Show all available apps",
            "\nAvailable apps:"
        ]
        
        for app_name, app_config in self.apps.items():
            aliases = app_config.get('aliases', [app_name])
            help_lines.append(f"  - {app_name} (say: {', '.join(aliases[:2])})")
        
        return "\n".join(help_lines)