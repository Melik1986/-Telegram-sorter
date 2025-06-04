#!/usr/bin/env python3
"""
Main entry point for the Telegram bot with AI-powered classification system.
"""

import logging
import os
from bot import TelegramBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Start the Telegram bot."""
    # Get bot token from environment variables
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
        return
    
    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable is required")
        return
    
    logger.info("Starting Telegram bot...")
    
    # Initialize and start the bot
    bot = TelegramBot(bot_token, openai_api_key)
    bot.run()

if __name__ == "__main__":
    main()
