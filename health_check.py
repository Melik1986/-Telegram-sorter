#!/usr/bin/env python3
"""
Проверка работоспособности проекта DevDataSorter
"""

import sys
import os
import traceback
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def check_imports():
    """Проверка импорта основных модулей"""
    print("=== Проверка импортов ===")
    
    tests = [
        ('telegram', 'python-telegram-bot'),
        ('flask', 'Flask'),
        ('requests', 'requests'),
        ('numpy', 'numpy'),
        ('sklearn', 'scikit-learn'),
        ('PIL', 'Pillow'),
        ('groq', 'groq'),
    ]
    
    for module, package in tests:
        try:
            __import__(module)
            print(f"✓ {package}: OK")
        except ImportError as e:
            print(f"✗ {package}: {e}")
    
    # Проверка основных модулей проекта
    project_modules = [
        ('src.core.config', 'Конфигурация'),
        ('src.core.classifier', 'Классификатор'),
        ('src.core.bot', 'Telegram бот'),
        ('src.web.app', 'Веб-интерфейс'),
        ('src.utils.storage', 'Хранилище'),
    ]
    
    print("\n=== Проверка модулей проекта ===")
    for module, name in project_modules:
        try:
            __import__(module)
            print(f"✓ {name}: OK")
        except Exception as e:
            print(f"✗ {name}: {e}")
            traceback.print_exc()

def check_config():
    """Проверка конфигурации"""
    print("\n=== Проверка конфигурации ===")
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'GROQ_API_KEY',
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: установлен")
        else:
            print(f"✗ {var}: не установлен")

def check_directories():
    """Проверка структуры директорий"""
    print("\n=== Проверка структуры директорий ===")
    
    required_dirs = [
        'src',
        'src/core',
        'src/web',
        'src/utils',
        'src/handlers',
        'tests',
        'data',
    ]
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✓ {dir_path}: существует")
        else:
            print(f"✗ {dir_path}: отсутствует")

def check_files():
    """Проверка ключевых файлов"""
    print("\n=== Проверка ключевых файлов ===")
    
    required_files = [
        'main.py',
        'requirements.txt',
        'src/core/bot.py',
        'src/core/classifier.py',
        'src/core/config.py',
        'src/web/app.py',
        '.env.example',
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}: существует")
        else:
            print(f"✗ {file_path}: отсутствует")

def main():
    """Основная функция проверки"""
    print("DevDataSorter - Проверка работоспособности")
    print("=" * 50)
    
    check_directories()
    check_files()
    check_config()
    check_imports()
    
    print("\n=== Завершение проверки ===")
    print("Проверьте результаты выше для выявления проблем.")

if __name__ == "__main__":
    main()