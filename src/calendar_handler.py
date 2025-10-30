"""
Calendar Handler - Complete calendar management system
Handles both conversational and direct event creation
"""

import webbrowser
import urllib.parse
import re
from datetime import datetime, timedelta


class CalendarHandler:
    """Manage all calendar functionality"""
    
    def __init__(self):
        # Track conversational event composition
        self.creating = False
        self.draft = {
            'title': None,
            'date': None,
            'time': None,
            'description': None,
            'step': None
        }
    
    def can_handle(self, user_input):
        """Check if this is a calendar-related command"""
        if self.creating:
            return True
        
        user_lower = user_input.lower().strip()
        calendar_keywords = [
            'schedule', 'create event', 'add event', 'calendar',
            'remind me', 'set reminder', 'add reminder',
            'meeting', 'appointment'
        ]
        
        return any(keyword in user_lower for keyword in calendar_keywords)
    
    def handle_command(self, user_input):
        """Main handler for calendar commands"""
        user_lower = user_input.lower().strip()
        
        # If already creating, continue the conversation
        if self.creating:
            return self._handle_conversation_step(user_input)
        
        # Check if this is a complete event command (all info provided)
        event_data = self._parse_complete_event(user_input)
        if event_data['title'] and event_data['date']:
            # Create immediately
            success = self._create_event(
                event_data['title'],
                event_data['date'],
                event_data['time'],
                event_data['description']
            )
            return True, "Calendar event creator opened with your details, sir."
        # Start conversational flow
        if any(keyword in user_lower for keyword in ['schedule', 'create event', 'add event', 'create an event']):
            self.creating = True
            self.draft = {'title': None, 'date': None, 'time': None, 'description': None, 'step': 'title'}
            
            # Try to extract both title and date from the command
            title = self._extract_event_title(user_input)
            date_time = self._extract_date_time(user_input)
            
            if title and date_time:
                # Both title and date found - create immediately
                success = self._create_event(
                    title,
                    date_time['date'],
                    date_time.get('time'),
                    None
                )
                self.creating = False
                self.draft = {'title': None, 'date': None, 'time': None, 'description': None, 'step': None}
                return True, f"Event '{title}' created for {date_time['date']}, sir."
            elif title:
                # Only title found - ask for date
                self.draft['title'] = title
                self.draft['step'] = 'date'
                return True, f"Creating event '{title}'. When should this event be, sir?"
            
            return True, "What would you like to call this event, sir?"
        
        # Handle reminders
        if any(keyword in user_lower for keyword in ['remind me', 'set reminder', 'add reminder']):
            task = self._extract_reminder_task(user_input)
            date_time = self._extract_date_time(user_input)
            
            if task and date_time:
                success = self._create_event(
                    f"Reminder: {task}",
                    date_time['date'],
                    date_time['time'],
                    task
                )
                return True, "Reminder created, sir."
            else:
                self.creating = True
                self.draft = {'title': None, 'date': None, 'time': None, 'description': None, 'step': 'title'}
                if task:
                    self.draft['title'] = f"Reminder: {task}"
                    self.draft['step'] = 'date'
                    return True, f"When should I remind you about '{task}', sir?"
                return True, "What should I remind you about, sir?"
        
        return False, "I'm not sure what calendar action you want, sir."
    
    def _handle_conversation_step(self, user_input):
        """Handle multi-step event creation"""
        current_step = self.draft['step']
        
        # Cancel command
        if user_input.lower().strip() in ['cancel', 'nevermind', 'never mind', 'stop']:
            self.creating = False
            self.draft = {'title': None, 'date': None, 'time': None, 'description': None, 'step': None}
            return True, "Event creation cancelled, sir."
        
        # Step 1: Get title
        if current_step == 'title':
            self.draft['title'] = user_input.strip()
            self.draft['step'] = 'date'
            return True, "When should this event be, sir?"
        
        # Step 2: Get date/time
        elif current_step == 'date':
            date_time = self._extract_date_time(user_input)
            if date_time:
                self.draft['date'] = date_time['date']
                self.draft['time'] = date_time.get('time')
                self.draft['step'] = 'description'
                return True, "Would you like to add any additional details, or should I create it now? Say 'done' to finish."
            else:
                return True, "I couldn't understand that date. Please try again with something like 'tomorrow at 2pm' or 'next Monday'."
        
        # Step 3: Get description (optional)
        elif current_step == 'description':
            if user_input.lower().strip() in ['done', 'no', 'create it', 'finish']:
                self.draft['description'] = None
            else:
                self.draft['description'] = user_input.strip()
            
            # Create the event
            success = self._create_event(
                self.draft['title'],
                self.draft['date'],
                self.draft['time'],
                self.draft['description']
            )
            
            # Reset state
            title = self.draft['title']
            self.creating = False
            self.draft = {'title': None, 'date': None, 'time': None, 'description': None, 'step': None}
            
            if success:
                return True, f"Event '{title}' created, sir."
            else:
                return True, "Calendar creator opened for you, sir."
        
        return False, "Something went wrong, sir."
    
    def _parse_complete_event(self, user_input):
        """Try to extract complete event info from one command"""
        event_data = {
            'title': self._extract_event_title(user_input),
            'date': None,
            'time': None,
            'description': None
        }
        
        date_time = self._extract_date_time(user_input)
        if date_time:
            event_data['date'] = date_time['date']
            event_data['time'] = date_time.get('time')
        
        return event_data
    
    def _extract_event_title(self, text):
        """Extract event title from text"""
        user_lower = text.lower()
        
        patterns = [
            # "create event for X" or "create an event for X"
            r'create\s+(?:an?\s+)?event\s+for\s+(.+?)(?:\s+(?:on|at|this|next|tomorrow|today)|\s*$)',
            # "schedule X for/at/on"
            r'schedule\s+(?:a\s+)?(?:meeting|event|appointment)?\s*(?:called|named|titled)?\s+["\']?([^"\']+?)["\']?\s+(?:for|at|on)',
            # "create event called X"
            r'create\s+(?:an?\s+)?event\s+(?:called|named|titled)\s+["\']?([^"\']+?)["\']?\s+(?:for|at|on)',
            # With quotes
            r'(?:schedule|create|add)\s+["\']([^"\']+)["\']',
            # "schedule X" (greedy catch-all)
            r'schedule\s+(.+?)(?:\s+(?:on|at|for|this|next|tomorrow|today)|\s*$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_lower)
            if match:
                title = match.group(1).strip()
                # Clean up common trailing words
                title = re.sub(r'\s+(on|at|for|this|next)$', '', title)
                return title
        
        return None
    
    def _extract_reminder_task(self, text):
        """Extract task from reminder command"""
        user_lower = text.lower()
        
        patterns = [
            r'remind me to\s+(.+?)(?:\s+(?:on|at|tomorrow|next|in)|\s*$)',
            r'reminder to\s+(.+?)(?:\s+(?:on|at|tomorrow|next|in)|\s*$)',
            r'remind me about\s+(.+?)(?:\s+(?:on|at|tomorrow|next|in)|\s*$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_lower)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_date_time(self, text):
        """Extract date and time from natural language"""
        text_lower = text.lower()
        now = datetime.now()
        
        result = {'date': None, 'time': None}
        
        # Handle relative dates
        if 'today' in text_lower:
            result['date'] = now.strftime('%Y-%m-%d')
        elif 'tomorrow' in text_lower:
            result['date'] = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'next week' in text_lower:
            result['date'] = (now + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Handle day of week
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(days):
            if day in text_lower:
                days_ahead = i - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                if 'next' in text_lower:
                    days_ahead += 7
                result['date'] = (now + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                break
        
        # Handle specific dates
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})/(\d{1,2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 3:
                    month, day, year = match.groups()
                    result['date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                else:
                    month, day = match.groups()
                    result['date'] = f"{now.year}-{month.zfill(2)}-{day.zfill(2)}"
                break
        
        # Extract time
        time_patterns = [
            r'at\s+(\d{1,2}):(\d{2})\s*(am|pm)?',
            r'at\s+(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*(am|pm)?',
            r'(\d{1,2})\s*(am|pm)',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                groups = match.groups()
                hour = int(groups[0])
                minute = int(groups[1]) if len(groups) > 1 and groups[1] and groups[1].isdigit() else 0
                period = groups[-1] if groups[-1] in ['am', 'pm'] else None
                
                if period == 'pm' and hour < 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
                
                result['time'] = f"{hour:02d}:{minute:02d}:00"
                break
        
        return result if result['date'] else None
    
    def _create_event(self, title, date, time=None, description=None):
        """Open Google Calendar with event details"""
        # Build Google Calendar URL
        calendar_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
        calendar_url += f"&text={urllib.parse.quote(title)}"
        
        # Add date/time
        if date:
            if time:
                start_datetime = f"{date.replace('-', '')}T{time.replace(':', '')}"
                calendar_url += f"&dates={start_datetime}/{start_datetime}"
            else:
                start_date = date.replace('-', '')
                end_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y%m%d')
                calendar_url += f"&dates={start_date}/{end_date}"
        
        if description:
            calendar_url += f"&details={urllib.parse.quote(description)}"
        
        webbrowser.open(calendar_url)
        return True
    
    def is_creating(self):
        """Check if currently creating an event"""
        return self.creating
    
    def cancel_creation(self):
        """Cancel current event creation"""
        self.creating = False
        self.draft = {'title': None, 'date': None, 'time': None, 'description': None, 'step': None}