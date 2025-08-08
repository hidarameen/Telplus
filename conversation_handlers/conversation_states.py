"""
Conversation states management for the Telegram bot
"""

# User conversation states
class ConversationStates:
    # Main states
    MAIN_MENU = 0
    
    # Authentication states
    AUTH_PHONE_INPUT = 10
    AUTH_CODE_INPUT = 11
    AUTH_PASSWORD_INPUT = 12
    
    # Task creation states
    CREATE_TASK_NAME = 20
    CREATE_TASK_SOURCE = 21
    CREATE_TASK_TARGET = 22
    CREATE_TASK_CONFIRM = 23
    
    # Task editing states
    EDIT_TASK_SELECT = 30
    EDIT_TASK_NAME = 31
    EDIT_TASK_SOURCE = 32
    EDIT_TASK_TARGET = 33
    EDIT_TASK_CONFIRM = 34
    
    # Settings states
    SETTINGS_MENU = 40
    SETTINGS_USERBOT = 41

# User data storage for conversation context
class UserData:
    def __init__(self):
        self.users = {}
    
    def get_user_state(self, user_id):
        """Get user conversation state"""
        return self.users.get(user_id, {}).get('state', ConversationStates.MAIN_MENU)
    
    def set_user_state(self, user_id, state):
        """Set user conversation state"""
        if user_id not in self.users:
            self.users[user_id] = {}
        self.users[user_id]['state'] = state
    
    def get_user_data(self, user_id, key, default=None):
        """Get user data by key"""
        return self.users.get(user_id, {}).get(key, default)
    
    def set_user_data(self, user_id, key, value):
        """Set user data by key"""
        if user_id not in self.users:
            self.users[user_id] = {}
        self.users[user_id][key] = value
    
    def clear_user_data(self, user_id, keep_auth=False):
        """Clear user data (optionally keep authentication data)"""
        if user_id not in self.users:
            return
        
        if keep_auth:
            auth_data = {
                'phone': self.users[user_id].get('phone'),
                'session_string': self.users[user_id].get('session_string'),
                'authenticated': self.users[user_id].get('authenticated', False)
            }
            self.users[user_id] = auth_data
        else:
            self.users[user_id] = {}
        
        self.set_user_state(user_id, ConversationStates.MAIN_MENU)
    
    def is_authenticated(self, user_id):
        """Check if user is authenticated"""
        return self.users.get(user_id, {}).get('authenticated', False)
    
    def set_authenticated(self, user_id, phone, session_string):
        """Mark user as authenticated"""
        if user_id not in self.users:
            self.users[user_id] = {}
        
        self.users[user_id].update({
            'authenticated': True,
            'phone': phone,
            'session_string': session_string
        })
    
    def get_session_string(self, user_id):
        """Get user session string"""
        return self.users.get(user_id, {}).get('session_string')
    
    def get_phone(self, user_id):
        """Get user phone number"""
        return self.users.get(user_id, {}).get('phone')

# Global user data instance
user_data = UserData()