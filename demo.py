#!/usr/bin/env python3
"""
Демонстрационный скрипт для презентации DevDataSorter
"""

import sys
import os
import time
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def print_header(title):
    """Печать заголовка секции"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_step(step, description):
    """Печать шага демонстрации"""
    print(f"\n[{step}] {description}")
    print("-" * 40)

def demo_config():
    """Демонстрация конфигурации"""
    print_header("ДЕМОНСТРАЦИЯ КОНФИГУРАЦИИ")
    
    try:
        from src.core.config import get_ai_config, TELEGRAM_BOT_TOKEN
        
        print_step("1", "Проверка переменных окружения")
        
        if TELEGRAM_BOT_TOKEN:
            print(f"✓ Telegram Bot Token: установлен (длина: {len(TELEGRAM_BOT_TOKEN)})")
        else:
            print("⚠ Telegram Bot Token: не установлен")
        
        ai_config = get_ai_config()
        provider = ai_config.get('provider', 'unknown')
        
        print(f"✓ AI провайдер: {provider}")
        
        if provider == 'groq':
            print("  - Используется Groq API (рекомендуется)")
        elif provider == 'ollama':
            print("  - Используется локальная Ollama")
        elif provider == 'fallback':
            print("  - Используется fallback режим")
        
    except Exception as e:
        print(f"✗ Ошибка конфигурации: {e}")

def demo_classifier():
    """Демонстрация классификатора"""
    print_header("ДЕМОНСТРАЦИЯ AI КЛАССИФИКАТОРА")
    
    try:
        from src.core.classifier import ContentClassifier
        
        print_step("1", "Инициализация классификатора")
        classifier = ContentClassifier()
        print(f"✓ Классификатор инициализирован")
        print(f"✓ Провайдер: {classifier.provider}")
        print(f"✓ Количество категорий: {len(classifier.categories)}")
        
        print_step("2", "Демонстрация категорий")
        categories = list(classifier.categories.keys())[:10]  # Первые 10
        for i, category in enumerate(categories, 1):
            description = classifier.categories[category]['description']
            print(f"  {i:2d}. {category}: {description}")
        
        if len(classifier.categories) > 10:
            print(f"     ... и еще {len(classifier.categories) - 10} категорий")
        
        print_step("3", "Тестовая классификация")
        
        test_content = """
        def hello_world():
            print("Hello, World!")
            return "success"
        """
        
        print("Тестовый контент:")
        print(test_content)
        
        # Fallback классификация
        result = classifier._fallback_classify(test_content)
        print(f"\nРезультат классификации:")
        print(f"  Категория: {result.get('category', 'unknown')}")
        print(f"  Подкатегория: {result.get('subcategory', 'unknown')}")
        print(f"  Уверенность: {result.get('confidence', 0):.2f}")
        
    except Exception as e:
        print(f"✗ Ошибка классификатора: {e}")
        import traceback
        traceback.print_exc()

def demo_storage():
    """Демонстрация системы хранения"""
    print_header("ДЕМОНСТРАЦИЯ СИСТЕМЫ ХРАНЕНИЯ")
    
    try:
        from src.utils.storage import ResourceStorage
        
        print_step("1", "Инициализация хранилища")
        storage = ResourceStorage()
        print("✓ Хранилище инициализировано")
        
        print_step("2", "Структура директорий")
        base_path = Path("data/sorted_content")
        if base_path.exists():
            dirs = [d for d in base_path.iterdir() if d.is_dir()]
            print(f"Найдено {len(dirs)} категорий:")
            for d in dirs[:5]:  # Первые 5
                files_count = len(list(d.rglob("*"))) if d.exists() else 0
                print(f"  - {d.name}: {files_count} файлов")
            if len(dirs) > 5:
                print(f"  ... и еще {len(dirs) - 5} категорий")
        else:
            print("Директория sorted_content еще не создана")
        
    except Exception as e:
        print(f"✗ Ошибка хранилища: {e}")

def demo_web_interface():
    """Демонстрация веб-интерфейса"""
    print_header("ДЕМОНСТРАЦИЯ ВЕБ-ИНТЕРФЕЙСА")
    
    try:
        print_step("1", "Проверка Flask")
        import flask
        print(f"✓ Flask версия: {flask.__version__}")
        
        print_step("2", "Проверка веб-модуля")
        from src.web.app import WebApp
        print("✓ Веб-приложение доступно")
        
        print_step("3", "Информация о запуске")
        print("Для запуска веб-интерфейса используйте:")
        print("  python -m src.web.app")
        print("")
        print("Веб-интерфейс будет доступен по адресу:")
        print("  http://localhost:5000")
        print("")
        print("Возможности веб-интерфейса:")
        print("  - Дашборд с визуализацией")
        print("  - Управление настройками")
        print("  - Поиск и фильтрация")
        print("  - GitHub интеграция")
        print("  - Экспорт данных")
        
    except Exception as e:
        print(f"✗ Ошибка веб-интерфейса: {e}")

def demo_telegram_bot():
    """Демонстрация Telegram бота"""
    print_header("ДЕМОНСТРАЦИЯ TELEGRAM БОТА")
    
    try:
        print_step("1", "Проверка python-telegram-bot")
        import telegram
        print(f"✓ python-telegram-bot версия: {telegram.__version__}")
        
        print_step("2", "Проверка основного бота")
        from src.core.bot import DevDataSorterBot
        print("✓ Класс бота доступен")
        
        print_step("3", "Информация о запуске")
        print("Для запуска Telegram бота используйте:")
        print("  python main.py")
        print("")
        print("Основные команды бота:")
        print("  /start - начало работы")
        print("  /help - справка по командам")
        print("  /list - список сохраненных ресурсов")
        print("  /search - поиск по содержимому")
        print("")
        print("Возможности бота:")
        print("  - Автоматическая сортировка файлов")
        print("  - Анализ ссылок и URL")
        print("  - Семантический поиск")
        print("  - Интеллектуальные команды")
        print("  - Многоязычная поддержка")
        
    except Exception as e:
        print(f"✗ Ошибка Telegram бота: {e}")

def demo_github_integration():
    """Демонстрация GitHub интеграции"""
    print_header("ДЕМОНСТРАЦИЯ GITHUB ИНТЕГРАЦИИ")
    
    try:
        print_step("1", "Проверка GitHub модуля")
        from src.utils.github_integration import create_github_integration
        print("✓ GitHub интеграция доступна")
        
        print_step("2", "Проверка конфигурации")
        github_token = os.getenv('GITHUB_TOKEN')
        github_username = os.getenv('GITHUB_USERNAME')
        
        if github_token:
            print(f"✓ GitHub Token: установлен (длина: {len(github_token)})")
        else:
            print("⚠ GitHub Token: не установлен")
        
        if github_username:
            print(f"✓ GitHub Username: {github_username}")
        else:
            print("⚠ GitHub Username: не установлен")
        
        print_step("3", "Возможности интеграции")
        print("GitHub интеграция позволяет:")
        print("  - Создавать резервные копии")
        print("  - Синхронизировать данные")
        print("  - Автоматические коммиты")
        print("  - Управление через веб-интерфейс")
        
    except Exception as e:
        print(f"✗ Ошибка GitHub интеграции: {e}")

def main():
    """Основная функция демонстрации"""
    print("🚀 DevDataSorter - Демонстрация возможностей")
    print("Интеллектуальная система сортировки данных для разработчиков")
    
    # Запуск всех демонстраций
    demo_config()
    demo_classifier()
    demo_storage()
    demo_web_interface()
    demo_telegram_bot()
    demo_github_integration()
    
    print_header("ЗАВЕРШЕНИЕ ДЕМОНСТРАЦИИ")
    print("")
    print("📋 Следующие шаги для полного запуска:")
    print("")
    print("1. Настройте переменные окружения в .env файле")
    print("2. Запустите проверку: python health_check.py")
    print("3. Запустите Telegram бота: python main.py")
    print("4. Запустите веб-интерфейс: python -m src.web.app")
    print("5. Откройте http://localhost:5000 в браузере")
    print("")
    print("📚 Документация: см. SETUP_GUIDE.md")
    print("🧪 Тестирование: python tests/run_tests.py")
    print("")
    print("✨ Готово к презентации!")

if __name__ == "__main__":
    main()