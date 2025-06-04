"""
Configuration file for API keys and settings.
"""

import os

# Telegram bot token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# OpenAI API key configuration
# To enable AI classification, provide your OpenAI API key here
OPENAI_API_KEY_DIRECT = None

def is_valid_openai_key(key):
    """Check if the API key is in valid OpenAI format."""
    if not key:
        return False
    return key.startswith('sk-')

def get_openai_key():
    """Get the correct OpenAI API key."""
    # Check various sources for a valid OpenAI key
    sources = [
        OPENAI_API_KEY_DIRECT,
        os.getenv('OPENAI_API_KEY_OVERRIDE'),
        os.getenv('OPENAI_API_KEY_NEW')
    ]
    
    for key in sources:
        if key and is_valid_openai_key(key):
            return key
    
    # Check if environment key is valid format
    env_key = os.getenv('OPENAI_API_KEY')
    if env_key and is_valid_openai_key(env_key):
        return env_key
    
    return None