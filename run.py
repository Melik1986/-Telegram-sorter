#!/usr/bin/env python3
"""
DevDataSorter - Telegram Bot Runner

Этот скрипт запускает Telegram бота с проверкой конфигурации.
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import get_telegram_token, get_openai_api_key, validate_api_keys, get_security_report
    from bot import TelegramBot
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все зависимости установлены: pip install -r requirements.txt")
    sys.exit(1)

def setup_logging():
    """Настройка логирования."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )

def check_environment():
    """Проверка окружения и конфигурации."""
    print("🔍 Проверка конфигурации...")
    
    # Проверка Telegram токена
    telegram_token = get_telegram_token()
    if not telegram_token:
        print("❌ TELEGRAM_BOT_TOKEN не найден!")
        print("   Создайте файл .env и добавьте: TELEGRAM_BOT_TOKEN=your_token_here")
        print("   Получите токен у @BotFather в Telegram")
        return False
    
    print("✅ Telegram токен найден")
    
    # Проверка OpenAI ключа (опционально)
    openai_key = get_openai_api_key()
    if openai_key:
        print("✅ OpenAI API ключ найден (улучшенная классификация включена)")
    else:
        print("⚠️  OpenAI API ключ не найден (будет использоваться базовая классификация)")
        print("   Для улучшенной классификации добавьте: OPENAI_API_KEY=your_key_here")
    
    # Проверка безопасности
    try:
        security_report = get_security_report()
        if security_report['status'] == 'secure':
            print("🔒 Конфигурация безопасности: ОК")
        else:
            print("⚠️  Обнаружены проблемы безопасности:")
            for issue in security_report['issues']:
                print(f"   - {issue}")
    except Exception as e:
        print(f"⚠️  Не удалось проверить безопасность: {e}")
    
    # Проверка директорий
    data_dir = Path('data')
    if not data_dir.exists():
        print("📁 Создание директории data/")
        data_dir.mkdir(exist_ok=True)
    
    uploads_dir = data_dir / 'uploads'
    if not uploads_dir.exists():
        print("📁 Создание директории data/uploads/")
        uploads_dir.mkdir(exist_ok=True)
    
    backups_dir = data_dir / 'backups'
    if not backups_dir.exists():
        print("📁 Создание директории data/backups/")
        backups_dir.mkdir(exist_ok=True)
    
    return True

def main():
    """Основная функция запуска."""
    print("🤖 DevDataSorter - Telegram Bot")
    print("=" * 40)
    
    # Настройка логирования
    setup_logging()
    
    # Проверка окружения
    if not check_environment():
        print("\n❌ Проверка конфигурации не пройдена. Исправьте ошибки и попробуйте снова.")
        sys.exit(1)
    
    print("\n🚀 Запуск бота...")
    
    try:
        # Создание и запуск бота
        bot = TelegramBot()
        print("✅ Бот успешно инициализирован")
        print("📱 Бот готов к работе! Найдите его в Telegram и отправьте /start")
        print("🌐 Веб-интерфейс: запустите web_interface.py для управления через браузер")
        print("\n⏹️  Для остановки нажмите Ctrl+C")
        print("-" * 40)
        
        # Запуск бота
        bot.run()
        
    except KeyboardInterrupt:
        print("\n⏹️  Получен сигнал остановки")
        print("👋 Бот остановлен")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n❌ Критическая ошибка: {e}")
        print("📋 Подробности в файле bot.log")
        sys.exit(1)

if __name__ == '__main__':
    main()