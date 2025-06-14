#!/usr/bin/env python3
"""
Минимальная точка входа для Telegram бота.
"""

import logging
import os
import sys
from pathlib import Path

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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Главная функция."""
    print("🤖 DevDataSorter - Минимальная версия")
    print("=" * 40)
    
    # Проверка конфигурации
    config = validate_config()
    
    if not config['telegram_configured']:
        print("❌ Telegram токен не настроен!")
        print("Установите переменную окружения TELEGRAM_BOT_TOKEN")
        return
    
    print("✅ Telegram токен найден")
    
    if config['ai_available']:
        print(f"✅ AI провайдер: {config['ai_provider']}")
    else:
        print("⚠️  AI не настроен, используется базовая классификация")
    
    if config['issues']:
        print("\nПредупреждения:")
        for issue in config['issues']:
            print(f"  {issue}")
    
    print("\n🚀 Запуск бота...")
    
    try:
        bot = DevDataSorterBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️  Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"\n❌ Ошибка: {e}")

if __name__ == '__main__':
    main()