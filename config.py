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

def get_telegram_token():
    """Get Telegram bot token from environment variables."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    return token

def validate_api_keys():
    """Validate all required API keys and provide security recommendations."""
    issues = []
    recommendations = []
    
    # Check Telegram token
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        issues.append("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    elif len(telegram_token) < 40:
        issues.append("⚠️ TELEGRAM_BOT_TOKEN выглядит некорректно (слишком короткий)")
    
    # Check OpenAI key
    openai_key = get_openai_key()
    if not openai_key:
        issues.append("⚠️ OPENAI_API_KEY не найден (AI классификация отключена)")
    elif not openai_key.startswith('sk-'):
        issues.append("⚠️ OPENAI_API_KEY имеет неверный формат")
    
    # Security recommendations
    recommendations.extend([
        "🔐 Рекомендации по безопасности API ключей:",
        "• Никогда не коммитьте API ключи в репозиторий",
        "• Используйте файл .env для локальной разработки",
        "• Добавьте .env в .gitignore",
        "• Используйте переменные окружения в продакшене",
        "• Регулярно ротируйте API ключи",
        "• Ограничьте права доступа для API ключей",
        "• Мониторьте использование API ключей",
        "• Используйте разные ключи для разработки и продакшена"
    ])
    
    return {
        'issues': issues,
        'recommendations': recommendations,
        'telegram_configured': bool(telegram_token),
        'openai_configured': bool(openai_key)
    }

def get_security_report():
    """Get detailed security report for API keys configuration."""
    validation = validate_api_keys()
    
    report = ["🔍 Отчет по безопасности API ключей:\n"]
    
    # Status
    if validation['telegram_configured']:
        report.append("✅ Telegram Bot Token: настроен")
    else:
        report.append("❌ Telegram Bot Token: не настроен")
        
    if validation['openai_configured']:
        report.append("✅ OpenAI API Key: настроен")
    else:
        report.append("⚠️ OpenAI API Key: не настроен (опционально)")
    
    # Issues
    if validation['issues']:
        report.append("\n🚨 Обнаруженные проблемы:")
        report.extend(validation['issues'])
    
    # Recommendations
    report.append("\n" + "\n".join(validation['recommendations']))
    
    return "\n".join(report)