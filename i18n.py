#!/usr/bin/env python3
"""
Internationalization (i18n) support for DevDataSorter.
Provides multi-language support for the Telegram bot.
"""

import json
import os
from typing import Dict, Optional

class I18nManager:
    """Manages internationalization for the bot."""
    
    def __init__(self, default_language='en'):
        self.default_language = default_language
        self.current_language = default_language
        self.translations = {}
        self.user_languages = {}  # user_id -> language_code
        self._load_translations()
    
    def _load_translations(self):
        """Load translation files."""
        translations_dir = 'translations'
        if not os.path.exists(translations_dir):
            os.makedirs(translations_dir)
            self._create_default_translations()
        
        # Load all translation files
        for filename in os.listdir(translations_dir):
            if filename.endswith('.json'):
                lang_code = filename[:-5]  # Remove .json extension
                filepath = os.path.join(translations_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Error loading translation file {filename}: {e}")
    
    def _create_default_translations(self):
        """Create default translation files."""
        translations_dir = 'translations'
        
        # English translations
        en_translations = {
            "welcome": {
                "title": "🤖 Welcome to DevDataSorter!",
                "description": "I'll help you automatically classify and organize your development resources.",
                "features": {
                    "classify": "• Classify links and content",
                    "sort": "• Sort by categories",
                    "search": "• Search through resources",
                    "save": "• Save descriptions",
                    "files": "• Process files and images",
                    "backup": "• Create backups"
                },
                "start_help": "Start with /help command to get assistance.",
                "instruction": "Just send me text, links, files, or resource descriptions, and I'll automatically classify them!"
            },
            "commands": {
                "help": {
                    "title": "📚 Available Commands:",
                    "basic": {
                        "title": "🔧 Basic Commands:",
                        "start": "/start - Start the bot",
                        "help": "/help - Show this help message",
                        "add": "/add <content> - Manually add content",
                        "search": "/search <query> - Search resources",
                        "categories": "/categories - List all categories",
                        "list": "/list [category] - List resources"
                    },
                    "management": {
                        "title": "⚙️ Management Commands:",
                        "stats": "/stats - Show bot statistics",
                        "backup": "/backup - Create manual backup",
                        "cache": "/cache [clear] - Manage cache",
                        "limits": "/limits - Show rate limits",
                        "export": "/export - Export data",
                        "import": "/import - Import data instructions",
                        "clear": "/clear - Clear all data",
                        "security": "/security - Security report",
                        "language": "/language <code> - Change language"
                    },
                    "files": {
                        "title": "📁 File Support:",
                        "images": "• Send images for analysis",
                        "documents": "• Send documents for processing",
                        "formats": "• Supports: PDF, TXT, DOCX, images"
                    },
                    "auto": "🤖 Automatic classification for any text or links you send!"
                }
            },
            "errors": {
                "rate_limit": "⚠️ Rate limit exceeded. Please wait before trying again.",
                "no_content": "❌ Please provide content to classify.",
                "classification_failed": "❌ Failed to classify content. Please try again.",
                "not_found": "❌ No resources found.",
                "invalid_command": "❌ Invalid command. Use /help for available commands.",
                "file_too_large": "❌ File is too large. Maximum size: {max_size}MB",
                "unsupported_format": "❌ Unsupported file format: {format}",
                "backup_failed": "❌ Backup creation failed: {error}",
                "import_failed": "❌ Import failed: {error}"
            },
            "success": {
                "added": "✅ Resource added successfully!",
                "backup_created": "✅ Backup created: {filename}",
                "cache_cleared": "✅ Cache cleared successfully!",
                "data_cleared": "✅ All data cleared successfully!",
                "language_changed": "✅ Language changed to {language}",
                "file_processed": "✅ File processed successfully!"
            },
            "categories": {
                "title": "📂 Available Categories:",
                "total": "Total: {count} categories",
                "empty": "No categories found."
            },
            "search": {
                "title": "🔍 Search Results:",
                "found": "Found {count} results for '{query}':",
                "no_results": "No results found for '{query}'.",
                "showing": "Showing {shown} of {total} results"
            },
            "stats": {
                "title": "📊 Bot Statistics:",
                "resources": "📚 Resources: {count}",
                "categories": "📂 Categories: {count}",
                "cache_items": "💾 Cache items: {count}",
                "files_processed": "📁 Files processed: {count}",
                "uptime": "⏱️ Uptime: {time}"
            },
            "languages": {
                "available": "🌐 Available languages:",
                "current": "Current language: {language}",
                "usage": "Usage: /language <code>\nExample: /language ru"
            }
        }
        
        # Russian translations
        ru_translations = {
            "welcome": {
                "title": "🤖 Добро пожаловать в DevDataSorter!",
                "description": "Я помогу вам автоматически классифицировать и организовать ваши ресурсы для разработки.",
                "features": {
                    "classify": "• Классифицировать ссылки и контент",
                    "sort": "• Сортировать по категориям",
                    "search": "• Искать по ресурсам",
                    "save": "• Сохранять описания",
                    "files": "• Обрабатывать файлы и изображения",
                    "backup": "• Создавать резервные копии"
                },
                "start_help": "Начните с команды /help для получения справки.",
                "instruction": "Просто отправьте мне текст, ссылки, файлы или описания ресурсов, и я автоматически их классифицирую!"
            },
            "commands": {
                "help": {
                    "title": "📚 Доступные команды:",
                    "basic": {
                        "title": "🔧 Основные команды:",
                        "start": "/start - Запустить бота",
                        "help": "/help - Показать эту справку",
                        "add": "/add <контент> - Добавить контент вручную",
                        "search": "/search <запрос> - Поиск ресурсов",
                        "categories": "/categories - Список всех категорий",
                        "list": "/list [категория] - Список ресурсов"
                    },
                    "management": {
                        "title": "⚙️ Команды управления:",
                        "stats": "/stats - Показать статистику бота",
                        "backup": "/backup - Создать резервную копию",
                        "cache": "/cache [clear] - Управление кэшем",
                        "limits": "/limits - Показать лимиты",
                        "export": "/export - Экспорт данных",
                        "import": "/import - Инструкции по импорту",
                        "clear": "/clear - Очистить все данные",
                        "security": "/security - Отчет по безопасности",
                        "language": "/language <код> - Изменить язык"
                    },
                    "files": {
                        "title": "📁 Поддержка файлов:",
                        "images": "• Отправляйте изображения для анализа",
                        "documents": "• Отправляйте документы для обработки",
                        "formats": "• Поддерживаются: PDF, TXT, DOCX, изображения"
                    },
                    "auto": "🤖 Автоматическая классификация любого текста или ссылок, которые вы отправите!"
                }
            },
            "errors": {
                "rate_limit": "⚠️ Превышен лимит запросов. Пожалуйста, подождите перед повторной попыткой.",
                "no_content": "❌ Пожалуйста, предоставьте контент для классификации.",
                "classification_failed": "❌ Не удалось классифицировать контент. Попробуйте еще раз.",
                "not_found": "❌ Ресурсы не найдены.",
                "invalid_command": "❌ Неверная команда. Используйте /help для просмотра доступных команд.",
                "file_too_large": "❌ Файл слишком большой. Максимальный размер: {max_size}МБ",
                "unsupported_format": "❌ Неподдерживаемый формат файла: {format}",
                "backup_failed": "❌ Создание резервной копии не удалось: {error}",
                "import_failed": "❌ Импорт не удался: {error}"
            },
            "success": {
                "added": "✅ Ресурс успешно добавлен!",
                "backup_created": "✅ Резервная копия создана: {filename}",
                "cache_cleared": "✅ Кэш успешно очищен!",
                "data_cleared": "✅ Все данные успешно очищены!",
                "language_changed": "✅ Язык изменен на {language}",
                "file_processed": "✅ Файл успешно обработан!"
            },
            "categories": {
                "title": "📂 Доступные категории:",
                "total": "Всего: {count} категорий",
                "empty": "Категории не найдены."
            },
            "search": {
                "title": "🔍 Результаты поиска:",
                "found": "Найдено {count} результатов для '{query}':",
                "no_results": "Результаты для '{query}' не найдены.",
                "showing": "Показано {shown} из {total} результатов"
            },
            "stats": {
                "title": "📊 Статистика бота:",
                "resources": "📚 Ресурсы: {count}",
                "categories": "📂 Категории: {count}",
                "cache_items": "💾 Элементы кэша: {count}",
                "files_processed": "📁 Обработано файлов: {count}",
                "uptime": "⏱️ Время работы: {time}"
            },
            "languages": {
                "available": "🌐 Доступные языки:",
                "current": "Текущий язык: {language}",
                "usage": "Использование: /language <код>\nПример: /language en"
            }
        }
        
        # Save translation files
        with open(os.path.join(translations_dir, 'en.json'), 'w', encoding='utf-8') as f:
            json.dump(en_translations, f, ensure_ascii=False, indent=2)
        
        with open(os.path.join(translations_dir, 'ru.json'), 'w', encoding='utf-8') as f:
            json.dump(ru_translations, f, ensure_ascii=False, indent=2)
    
    def set_user_language(self, user_id: int, language_code: str) -> bool:
        """Set language for a specific user."""
        if language_code in self.translations:
            self.user_languages[user_id] = language_code
            return True
        return False
    
    def get_user_language(self, user_id: int) -> str:
        """Get language for a specific user."""
        return self.user_languages.get(user_id, self.default_language)
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get list of available languages."""
        return {
            'en': 'English',
            'ru': 'Русский'
        }
    
    def t(self, key: str, user_id: int = None, **kwargs) -> str:
        """Translate a key for a specific user or default language."""
        lang = self.get_user_language(user_id) if user_id else self.default_language
        
        # Navigate through nested keys (e.g., "errors.not_found")
        keys = key.split('.')
        value = self.translations.get(lang, {})
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # Fallback to default language
                value = self.translations.get(self.default_language, {})
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return key  # Return key if translation not found
                break
        
        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value
        
        return key
    

    
    def get_welcome_message(self, user_id: Optional[int] = None) -> str:
        """Get formatted welcome message."""
        lang = self.get_user_language(user_id) if user_id else self.default_language
        welcome = self.translations.get(lang, {}).get('welcome', {})
        
        if not welcome:
            return "Welcome to DevDataSorter!"
        
        message_parts = [
            welcome.get('title', ''),
            '',
            welcome.get('description', ''),
            '',
            "📝 " + ("What I can do:" if lang == 'en' else "Что я умею:"),
        ]
        
        features = welcome.get('features', {})
        for feature in features.values():
            message_parts.append(feature)
        
        message_parts.extend([
            '',
            "🚀 " + welcome.get('start_help', ''),
            '',
            welcome.get('instruction', '')
        ])
        
        return '\n'.join(message_parts)
    
    def get_help_message(self, user_id: Optional[int] = None) -> str:
        """Get formatted help message."""
        lang = self.get_user_language(user_id) if user_id else self.default_language
        commands = self.translations.get(lang, {}).get('commands', {}).get('help', {})
        
        if not commands:
            return "Help information not available."
        
        message_parts = [commands.get('title', '')]
        
        # Basic commands
        basic = commands.get('basic', {})
        if basic:
            message_parts.extend([
                '',
                basic.get('title', ''),
                basic.get('start', ''),
                basic.get('help', ''),
                basic.get('add', ''),
                basic.get('search', ''),
                basic.get('categories', ''),
                basic.get('list', '')
            ])
        
        # Management commands
        management = commands.get('management', {})
        if management:
            message_parts.extend([
                '',
                management.get('title', ''),
                management.get('stats', ''),
                management.get('backup', ''),
                management.get('cache', ''),
                management.get('limits', ''),
                management.get('export', ''),
                management.get('import', ''),
                management.get('clear', ''),
                management.get('security', ''),
                management.get('language', '')
            ])
        
        # File support
        files = commands.get('files', {})
        if files:
            message_parts.extend([
                '',
                files.get('title', ''),
                files.get('images', ''),
                files.get('documents', ''),
                files.get('formats', '')
            ])
        
        message_parts.extend([
            '',
            commands.get('auto', '')
        ])
        
        return '\n'.join(filter(None, message_parts))

# Global instance
_i18n_manager = None

def get_i18n_manager() -> I18nManager:
    """Get global i18n manager instance."""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager

def t(key: str, user_id: Optional[int] = None, **kwargs) -> str:
    """Shortcut function for translation."""
    return get_i18n_manager().t(key, user_id, **kwargs)