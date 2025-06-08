#!/usr/bin/env python3
"""
Main entry point for the Telegram bot with AI-powered classification system.
"""

import logging
import os
from src.core.bot import DevDataSorterBot

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, continue with system environment variables
    pass

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
    
    # Initialize and run bot
    bot = DevDataSorterBot(bot_token)
    bot.run()

if __name__ == "__main__":
    main()
