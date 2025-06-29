#!/usr/bin/env python3
"""
Основная точка входа для Render развертывания.
"""

import logging
import os
import sys
import threading
from pathlib import Path
from flask import Flask

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.core.bot_minimal import DevDataSorterBot
from src.core.config_minimal import validate_config

# Настройка логирования для Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Создаем Flask app для health check
app = Flask(__name__)

@app.route('/health')
def health_check():
    """Health check endpoint для Render."""
    return {'status': 'healthy', 'service': 'devdatasorter-bot'}, 200

@app.route('/')
def index():
    """Главная страница."""
    return {
        'service': 'DevDataSorter Bot',
        'status': 'running',
        'version': 'render-optimized'
    }, 200

def run_bot():
    """Запуск бота в отдельном потоке."""
    try:
        bot = DevDataSorterBot()
        bot.run()
    except Exception as e:
        logger.error(f"Bot error: {e}")

def main():
    """Главная функция для Render."""
    print("🚀 DevDataSorter - Render Deployment")
    print("=" * 50)
    
    # Проверка конфигурации
    config = validate_config()
    
    if not config['telegram_configured']:
        logger.error("❌ TELEGRAM_BOT_TOKEN не настроен!")
        logger.error("Установите переменную окружения в Render Dashboard")
        return
    
    logger.info("✅ Telegram токен найден")
    
    if config['ai_available']:
        logger.info(f"✅ AI провайдер: {config['ai_provider']}")
    else:
        logger.warning("⚠️ AI не настроен, используется базовая классификация")
    
    # Получение порта для Render
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Порт для Render: {port}")
    
    logger.info("🤖 Запуск бота...")
    
    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запуск Flask для health checks
    logger.info(f"🌐 Запуск веб-сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()