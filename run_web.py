#!/usr/bin/env python3
"""
DevDataSorter - Web Interface Runner

Этот скрипт запускает веб-интерфейс для управления ботом.
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

try:
    from web_interface import app
    from config import get_security_report
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
            logging.FileHandler('web.log', encoding='utf-8')
        ]
    )

def check_environment():
    """Проверка окружения и конфигурации."""
    print("🔍 Проверка конфигурации веб-интерфейса...")
    
    # Проверка секретного ключа Flask
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if not secret_key:
        print("⚠️  FLASK_SECRET_KEY не найден, будет использован случайный ключ")
        print("   Для продакшена добавьте в .env: FLASK_SECRET_KEY=your_secret_key")
    else:
        print("✅ Flask секретный ключ найден")
    
    # Проверка порта
    port = int(os.getenv('WEB_INTERFACE_PORT', 5000))
    print(f"🌐 Веб-интерфейс будет запущен на порту: {port}")
    
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
    
    return True, port

def main():
    """Основная функция запуска."""
    print("🌐 DevDataSorter - Web Interface")
    print("=" * 40)
    
    # Настройка логирования
    setup_logging()
    
    # Проверка окружения
    success, port = check_environment()
    if not success:
        print("\n❌ Проверка конфигурации не пройдена. Исправьте ошибки и попробуйте снова.")
        sys.exit(1)
    
    print("\n🚀 Запуск веб-интерфейса...")
    
    try:
        # Настройка Flask приложения
        if not app.secret_key:
            import secrets
            app.secret_key = secrets.token_hex(16)
            print("🔑 Сгенерирован временный секретный ключ")
        
        print("✅ Веб-интерфейс успешно инициализирован")
        print(f"🌐 Откройте в браузере: http://localhost:{port}")
        print("📊 Доступные разделы:")
        print("   - Dashboard: общая статистика")
        print("   - Resources: управление ресурсами")
        print("   - Cache: управление кэшем")
        print("   - Backups: резервные копии")
        print("   - Security: мониторинг безопасности")
        print("\n⏹️  Для остановки нажмите Ctrl+C")
        print("-" * 40)
        
        # Запуск веб-сервера
        app.run(
            host='0.0.0.0',
            port=port,
            debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        )
        
    except KeyboardInterrupt:
        print("\n⏹️  Получен сигнал остановки")
        print("👋 Веб-интерфейс остановлен")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n❌ Критическая ошибка: {e}")
        print("📋 Подробности в файле web.log")
        sys.exit(1)

if __name__ == '__main__':
    main()