#!/usr/bin/env python3
"""
Основная точка входа для Render развертывания.
Включает полную функциональность с оптимизациями.
"""

import logging
import os
import sys
import asyncio
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.core.bot_render import DevDataSorterBot
from src.core.config_render import validate_config

# Настройка логирования для Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

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
    
    try:
        bot = DevDataSorterBot()
        
        # Запуск в асинхронном режиме для лучшей производительности
        asyncio.run(bot.run_async())
        
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    main()