"""
Configuration file for API keys and settings.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Telegram bot token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# AI API configuration
# Support for both Groq and Ollama APIs
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:1b')

def get_ai_config():
    """Get AI configuration with priority: Groq > Ollama > Fallback."""
    if GROQ_API_KEY:
        return {
            'provider': 'groq',
            'api_key': GROQ_API_KEY,
            'model': GROQ_MODEL
        }
    elif is_ollama_available():
        return {
            'provider': 'ollama',
            'base_url': OLLAMA_BASE_URL,
            'model': OLLAMA_MODEL
        }
    else:
        return {
            'provider': 'fallback',
            'model': 'pattern-based'
        }

def get_ollama_config():
    """Get Ollama configuration (legacy support)."""
    return {
        'base_url': OLLAMA_BASE_URL,
        'model': OLLAMA_MODEL
    }

def is_groq_available():
    """Check if Groq API is configured."""
    return bool(GROQ_API_KEY)

def is_ollama_available():
    """Check if Ollama is available."""
    try:
        import requests
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        return False

def get_telegram_token():
    """Get Telegram bot token from environment variables."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    return token

def validate_config():
    """Validate AI API availability and provide recommendations."""
    issues = []
    
    # Check Telegram token
    telegram_configured = bool(TELEGRAM_BOT_TOKEN)
    if not telegram_configured:
        issues.append("❌ TELEGRAM_BOT_TOKEN не настроен")
        issues.append("💡 Получите токен у @BotFather в Telegram")
    
    # Check AI configuration
    ai_config = get_ai_config()
    ai_available = ai_config['provider'] != 'fallback'
    
    if not ai_available:
        issues.append("⚠️ AI API не настроен (используется базовая классификация)")
        issues.append("💡 Настройте Groq API или Ollama для улучшенной классификации")
    
    # AI recommendations
    if not ai_available:
        issues.extend([
            "🤖 Рекомендации по настройке AI:",
            "• Groq API (рекомендуется):",
            "  - Получите API ключ: https://console.groq.com/",
            "  - Установите GROQ_API_KEY в переменные окружения",
            "  - Быстрая и надежная облачная AI",
            "• Ollama (локальная альтернатива):",
            "  - Установите Ollama: https://ollama.ai/download",
            "  - Запустите сервер: ollama serve",
            "  - Скачайте модель: ollama pull llama3.2",
        ])
    
    return {
        'telegram_configured': telegram_configured,
        'ai_available': ai_available,
        'ai_provider': ai_config['provider'],
        'ollama_available': is_ollama_available(),
        'groq_available': is_groq_available(),
        'issues': issues
    }

def validate_api_keys():
    """Validate API keys and return status (legacy function for compatibility)."""
    return validate_config()

def get_security_report():
    """Get detailed configuration report for AI setup."""
    validation = validate_config()
    
    report = [
        "🔧 Конфигурация DevDataSorter:",
        "",
        "📱 Telegram Bot:"
    ]
    
    if validation['telegram_configured']:
        report.append("✅ Telegram: настроен и готов к работе")
    else:
        report.append("❌ Telegram: требуется настройка токена")
    
    # AI Status
    report.append("")
    report.append("🤖 AI Классификация:")
    
    if validation['ai_available']:
        provider = validation['ai_provider']
        if provider == 'groq':
            report.append("✅ Groq API: настроен и готов к работе")
        elif provider == 'ollama':
            report.append("✅ Ollama: доступен и готов к работе")
    else:
        report.append("⚠️ AI: используется базовая классификация")
    
    # Additional status
    if validation['groq_available']:
        report.append("  • Groq API: доступен")
    if validation['ollama_available']:
        report.append("  • Ollama: доступен")
    
    if validation['issues']:
        report.append("")
        report.append("⚠️ Рекомендации:")
        report.extend([f"  {issue}" for issue in validation['issues']])
    
    # Determine security status
    is_secure = validation['telegram_configured'] and validation['ai_available']
    
    return {
        'status': 'secure' if is_secure else 'warning',
        'issues': validation['issues'],
        'report': "\n".join(report),
        'telegram_configured': validation['telegram_configured'],
        'ai_available': validation['ai_available'],
        'ai_provider': validation['ai_provider']
    }