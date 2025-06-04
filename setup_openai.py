#!/usr/bin/env python3
"""
Setup script to configure OpenAI API key for the Telegram bot.
"""

import os
import sys
from openai import OpenAI

def test_openai_key(api_key):
    """Test if the provided OpenAI API key works."""
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5
        )
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)

def main():
    print("OpenAI API Key Setup for Telegram Bot")
    print("=" * 40)
    
    current_key = os.getenv('OPENAI_API_KEY', '')
    print(f"Current key: {current_key[:15]}...")
    print(f"Valid format: {current_key.startswith('sk-')}")
    
    print("\nTo use full AI classification, please provide your OpenAI API key.")
    print("The key should start with 'sk-' and be from platform.openai.com")
    
    api_key = input("\nEnter your OpenAI API key: ").strip()
    
    if not api_key.startswith('sk-'):
        print("❌ Invalid format. OpenAI keys start with 'sk-'")
        return
    
    print("Testing API key...")
    success, message = test_openai_key(api_key)
    
    if success:
        print("✅ API key works!")
        # Set the environment variable for this session
        os.environ['OPENAI_API_KEY_OVERRIDE'] = api_key
        print("OpenAI API configured successfully.")
    else:
        print(f"❌ API key test failed: {message}")

if __name__ == "__main__":
    main()