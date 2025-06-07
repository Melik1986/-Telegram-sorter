"""
Configuration file for API keys and settings.
"""

import os

# Telegram bot token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Ollama API configuration
# Ollama runs locally and doesn't require API keys
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:1b')

def get_ollama_config():
    """Get Ollama configuration."""
    return {
        'base_url': OLLAMA_BASE_URL,
        'model': OLLAMA_MODEL
    }

def is_ollama_available():
    """Check if Ollama is available."""
    try:
        import requests
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def get_telegram_token():
    """Get Telegram bot token from environment variables."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    return token

def validate_api_keys():
    """Validate Ollama availability and provide recommendations."""
    issues = []
    recommendations = []
    
    # Check Telegram token
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        issues.append("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    elif len(telegram_token) < 40:
        issues.append("⚠️ TELEGRAM_BOT_TOKEN выглядит некорректно (слишком короткий)")
    
    # Check Ollama availability
    ollama_available = is_ollama_available()
    if not ollama_available:
        issues.append("⚠️ Ollama не запущен или недоступен (AI классификация отключена)")
        issues.append("💡 Запустите Ollama командой: ollama serve")
    
    # Ollama recommendations
    recommendations.extend([
        "🤖 Рекомендации по настройке Ollama:",
        "• Установите Ollama: https://ollama.ai/download",
        "• Запустите сервер: ollama serve",
        "• Скачайте модель: ollama pull llama3.2",
        "• Проверьте доступность: curl http://localhost:11434/api/tags",
        "• Настройте OLLAMA_BASE_URL если используете другой порт",
        "• Настройте OLLAMA_MODEL для использования другой модели",
        "• Ollama работает локально и не требует API ключей",
        "• Модели хранятся локально и работают офлайн"
    ])
    
    return {
        'issues': issues,
        'recommendations': recommendations,
        'telegram_configured': bool(telegram_token),
        'ollama_available': ollama_available
    }

def get_security_report():
    """Get detailed configuration report for Ollama setup."""
    validation = validate_api_keys()
    
    report = ["🔍 Отчет по конфигурации системы:\n"]
    
    # Status
    if validation['telegram_configured']:
        report.append("✅ Telegram Bot Token: настроен")
    else:
        report.append("❌ Telegram Bot Token: не настроен")
        
    if validation['ollama_available']:
        report.append("✅ Ollama: доступен и готов к работе")
    else:
        report.append("⚠️ Ollama: недоступен (требуется установка и запуск)")
    
    # Issues
    if validation['issues']:
        report.append("\n🚨 Обнаруженные проблемы:")
        report.extend(validation['issues'])
    
    # Recommendations
    report.append("\n" + "\n".join(validation['recommendations']))
    
    # Determine security status
    is_secure = validation['telegram_configured'] and len(validation['issues']) == 0
    
    return {
        'status': 'secure' if is_secure else 'warning',
        'issues': validation['issues'],
        'report': "\n".join(report),
        'telegram_configured': validation['telegram_configured'],
        'ollama_available': validation['ollama_available']
    }