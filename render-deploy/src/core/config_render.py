"""
Конфигурация для Render развертывания.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Основные переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile')

# Redis для кэширования (если доступен)
REDIS_URL = os.getenv('REDIS_URL')

def get_telegram_token():
    """Получить токен Telegram бота."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    return TELEGRAM_BOT_TOKEN

def get_ai_config():
    """Получить конфигурацию AI."""
    if GROQ_API_KEY:
        return {
            'provider': 'groq',
            'api_key': GROQ_API_KEY,
            'model': GROQ_MODEL
        }
    else:
        return {
            'provider': 'fallback',
            'model': 'pattern-based'
        }

def is_groq_available():
    """Проверить доступность Groq API."""
    return bool(GROQ_API_KEY)

def is_redis_available():
    """Проверить доступность Redis."""
    return bool(REDIS_URL)

def validate_config():
    """Валидация конфигурации для Render."""
    issues = []
    
    if not TELEGRAM_BOT_TOKEN:
        issues.append("❌ TELEGRAM_BOT_TOKEN не настроен")
    
    ai_config = get_ai_config()
    if ai_config['provider'] == 'fallback':
        issues.append("⚠️ AI API не настроен (используется базовая классификация)")
    
    if not REDIS_URL:
        issues.append("⚠️ Redis не настроен (кэширование отключено)")
    
    return {
        'telegram_configured': bool(TELEGRAM_BOT_TOKEN),
        'ai_available': ai_config['provider'] != 'fallback',
        'ai_provider': ai_config['provider'],
        'redis_available': bool(REDIS_URL),
        'issues': issues
    }