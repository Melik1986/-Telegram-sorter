import logging
import asyncio
import os
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

from .classifier import ContentClassifier
from .config import get_ai_config, TELEGRAM_BOT_TOKEN
from ..utils.storage import ResourceStorage
from ..utils.rate_limiter import RateLimiter
from ..utils.i18n import I18nManager
from ..handlers.file_handler import FileHandler
from ..handlers.message_sorter import MessageSorter
from ..handlers.command_interpreter import NaturalLanguageCommandInterpreter, CommandType

logger = logging.getLogger(__name__)

class DevDataSorterBot:
    """Main bot class for DevDataSorter."""
    
    def __init__(self, token: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.ai_config = get_ai_config()
        self.storage = ResourceStorage(enable_semantic_search=True)
        self.classifier = ContentClassifier()
        self.rate_limiter = RateLimiter()
        self.i18n = I18nManager()
        self.file_handler = FileHandler()
        self.message_sorter = MessageSorter(self.classifier)
        self.command_interpreter = NaturalLanguageCommandInterpreter(self.classifier)
        
        # Initialize Telegram application
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all bot handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("list", self.list_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("semantic_search", self.semantic_search_command))
        self.app.add_handler(CommandHandler("filter", self.filter_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        self.app.add_handler(CommandHandler("export", self.export_command))
        self.app.add_handler(CommandHandler("settings", self.settings_command))
        self.app.add_handler(CommandHandler("analyze", self.analyze_command))
        self.app.add_handler(CommandHandler("delete", self.delete_command))
        self.app.add_handler(CommandHandler("archive", self.archive_command))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_file))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.app.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
        self.app.add_handler(MessageHandler(filters.AUDIO, self.handle_audio))
        
        # Callback query handler
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        user_id = update.effective_user.id
        content = update.message.text
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(user_id):
            await update.message.reply_text(
                "⏰ Too many requests. Please wait a moment.\n"
                "⏰ Слишком много запросов. Подождите немного."
            )
            return
        
        # First, try to interpret as a natural language command
        command_intent = await self.command_interpreter.interpret_command(content)
        
        if command_intent.command_type != CommandType.UNKNOWN and command_intent.confidence > 0.6:
            await self._handle_command_intent(update, context, command_intent)
            return
        
        # Determine if this is a question/request or content to classify
        if await self._is_question_or_request(content):
            await self._handle_intelligent_response(update, context, content)
        else:
            await self._process_content(update, context, content)
    
    async def _handle_command_intent(self, update: Update, context: ContextTypes.DEFAULT_TYPE, command_intent):
        """Handle interpreted natural language commands."""
        try:
            command_type = command_intent.command_type
            parameters = command_intent.parameters
            language = command_intent.language
            
            # Show processing message
            if language == 'ru':
                status_msg = await update.message.reply_text("🤖 Выполняю команду...")
            else:
                status_msg = await update.message.reply_text("🤖 Executing command...")
            
            if command_type == CommandType.SEARCH:
                query = parameters.get('query', '')
                if query:
                    await self._execute_search_command(update, context, query, language, parameters)
                else:
                    await self._send_search_help(update, language)
            
            elif command_type == CommandType.SEMANTIC_SEARCH:
                query = parameters.get('query', '')
                if query:
                    await self._execute_semantic_search_command(update, context, query, language, parameters)
                else:
                    await self._send_semantic_search_help(update, language)
            
            elif command_type == CommandType.CREATE_FOLDER:
                folder_name = parameters.get('name', '')
                if folder_name:
                    await self._execute_create_folder_command(update, context, folder_name, language)
                else:
                    await self._send_folder_help(update, language)
            
            elif command_type == CommandType.CREATE_ARCHIVE:
                archive_name = parameters.get('name', '')
                if archive_name:
                    await self._execute_create_archive_command(update, context, archive_name, language)
                else:
                    await self._send_archive_help(update, language)
            
            elif command_type == CommandType.LIST:
                category = parameters.get('category', 'all')
                await self._execute_list_command(update, context, category, language)
            
            elif command_type == CommandType.HELP:
                await self._execute_help_command(update, context, language)
            
            elif command_type == CommandType.STATS:
                await self._execute_stats_command(update, context, language)
            
            elif command_type == CommandType.EXPORT:
                format_type = parameters.get('format', 'json')
                await self._execute_export_command(update, context, format_type, language)
            
            elif command_type == CommandType.ANALYZE:
                await self._execute_analyze_command(update, context, language)
            
            elif command_type == CommandType.DELETE:
                item_id = parameters.get('id')
                if item_id:
                    await self._execute_delete_command(update, context, item_id, language)
                else:
                    await self._send_delete_help(update, language)
            
            # Delete status message
            try:
                await status_msg.delete()
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error handling command intent: {e}")
            error_msg = "❌ Произошла ошибка при выполнении команды" if command_intent.language == 'ru' else "❌ Error executing command"
            await update.message.reply_text(error_msg)
    
    # Command execution methods
    async def _execute_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, language: str, parameters: dict = None):
        """Execute search command with optional filters."""
        try:
            # Use parameters from command interpreter if available
            if parameters:
                final_query = parameters.get('query', query)
                category_filter = parameters.get('category')
                date_from = parameters.get('date_from')
                date_to = parameters.get('date_to')
                time_period = parameters.get('time_period')
                
                # Handle time period shortcuts
                if time_period and not (date_from or date_to):
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    
                    if time_period == 'today':
                        date_from = now.strftime('%Y-%m-%d')
                        date_to = now.strftime('%Y-%m-%d')
                    elif time_period == 'week':
                        date_from = (now - timedelta(days=7)).strftime('%Y-%m-%d')
                        date_to = now.strftime('%Y-%m-%d')
                    elif time_period == 'month':
                        date_from = (now - timedelta(days=30)).strftime('%Y-%m-%d')
                        date_to = now.strftime('%Y-%m-%d')
                    elif time_period == 'year':
                        date_from = (now - timedelta(days=365)).strftime('%Y-%m-%d')
                        date_to = now.strftime('%Y-%m-%d')
            else:
                # Fallback to old parsing method
                parts = query.split()
                search_query = []
                category_filter = None
                date_from = None
                date_to = None
                
                for part in parts:
                    if part.startswith('category:'):
                        category_filter = part.split(':', 1)[1]
                    elif part.startswith('date_from:'):
                        date_from = part.split(':', 1)[1]
                    elif part.startswith('date_to:'):
                        date_to = part.split(':', 1)[1]
                    else:
                        search_query.append(part)
                
                final_query = ' '.join(search_query)
            
            if not final_query:
                if language == 'ru':
                    help_msg = "🔍 Использование: найди <запрос> [в категории <категория>] [за <период>]\nПример: 'найди React туториалы за последний месяц'"
                else:
                    help_msg = "🔍 Usage: find <query> [in category <category>] [for <period>]\nExample: 'find React tutorials for last month'"
                await update.message.reply_text(help_msg)
                return
            
            results = self.storage.search_resources(
                final_query,
                category_filter=category_filter,
                date_from=date_from,
                date_to=date_to
            )
            
            if not results:
                if language == 'ru':
                    response = f"🔍 По запросу '{final_query}' ничего не найдено"
                else:
                    response = f"🔍 No results found for '{final_query}'"
            else:
                if language == 'ru':
                    response = f"🔍 Найдено {len(results)} результатов по запросу '{final_query}':\n\n"
                else:
                    response = f"🔍 Found {len(results)} results for '{final_query}':\n\n"
                
                for i, result in enumerate(results[:10], 1):
                    response += f"{i}. {result.get('title', 'Untitled')}\n"
                    response += f"   📁 {result.get('category', 'Unknown')}\n"
                    if result.get('description'):
                        response += f"   📝 {result['description'][:100]}...\n"
                    response += "\n"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Search command error: {e}")
            error_msg = "❌ Ошибка поиска" if language == 'ru' else "❌ Search error"
            await update.message.reply_text(error_msg)
    
    async def _execute_semantic_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, language: str, parameters: dict = None):
        """Execute semantic search command."""
        try:
            # Check if semantic search is available
            if not hasattr(self.storage, 'semantic_search_engine') or self.storage.semantic_search_engine is None:
                if language == 'ru':
                    response = "🧠 Семантический поиск недоступен. Убедитесь, что установлены зависимости: sentence-transformers и faiss-cpu"
                else:
                    response = "🧠 Semantic search is not available. Make sure dependencies are installed: sentence-transformers and faiss-cpu"
                await update.message.reply_text(response)
                return
            
            # Extract filters from parameters if available
            category_filter = None
            date_from = None
            date_to = None
            time_period = None
            
            if parameters:
                category_filter = parameters.get('category')
                date_from = parameters.get('date_from')
                date_to = parameters.get('date_to')
                time_period = parameters.get('time_period')
                
                # Handle time period shortcuts
                if time_period and not (date_from or date_to):
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    
                    if time_period == 'today':
                        date_from = now.strftime('%Y-%m-%d')
                        date_to = now.strftime('%Y-%m-%d')
                    elif time_period == 'week':
                        date_from = (now - timedelta(days=7)).strftime('%Y-%m-%d')
                        date_to = now.strftime('%Y-%m-%d')
                    elif time_period == 'month':
                        date_from = (now - timedelta(days=30)).strftime('%Y-%m-%d')
                        date_to = now.strftime('%Y-%m-%d')
                    elif time_period == 'year':
                        date_from = (now - timedelta(days=365)).strftime('%Y-%m-%d')
                        date_to = now.strftime('%Y-%m-%d')
            
            # Check if storage supports filtered semantic search
            if hasattr(self.storage, 'semantic_search_resources_filtered'):
                results = await self.storage.semantic_search_resources_filtered(
                    query, 
                    limit=10,
                    category_filter=category_filter,
                    date_from=date_from,
                    date_to=date_to
                )
            else:
                results = await self.storage.semantic_search_resources(query, limit=10)
            
            if not results:
                if language == 'ru':
                    response = f"🧠 По семантическому запросу '{query}' ничего не найдено"
                    if category_filter:
                        response += f" в категории '{category_filter}'"
                    if time_period:
                        response += f" за {time_period}"
                else:
                    response = f"🧠 No semantic results found for '{query}'"
                    if category_filter:
                        response += f" in category '{category_filter}'"
                    if time_period:
                        response += f" for {time_period}"
            else:
                if language == 'ru':
                    response = f"🧠 Найдено {len(results)} семантических результатов по запросу '{query}'"
                    if category_filter:
                        response += f" в категории '{category_filter}'"
                    if time_period:
                        response += f" за {time_period}"
                    response += ":\n\n"
                else:
                    response = f"🧠 Found {len(results)} semantic results for '{query}'"
                    if category_filter:
                        response += f" in category '{category_filter}'"
                    if time_period:
                        response += f" for {time_period}"
                    response += ":\n\n"
                
                for i, result in enumerate(results, 1):
                    resource = result.get('resource', {})
                    score = result.get('score', 0.0)
                    response += f"{i}. {resource.get('title', 'Untitled')}\n"
                    response += f"   📁 {resource.get('category', 'Unknown')}\n"
                    response += f"   🎯 Релевантность: {score:.2f}\n"
                    if resource.get('description'):
                        response += f"   📝 {resource['description'][:100]}...\n"
                    response += "\n"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Semantic search command error: {e}")
            error_msg = "❌ Ошибка семантического поиска" if language == 'ru' else "❌ Semantic search error"
            await update.message.reply_text(error_msg)
    
    async def _execute_create_folder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, folder_name: str, language: str):
        """Execute create folder command."""
        try:
            # Create folder logic here
            if language == 'ru':
                response = f"📁 Папка '{folder_name}' создана успешно"
            else:
                response = f"📁 Folder '{folder_name}' created successfully"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Create folder error: {e}")
            error_msg = "❌ Ошибка создания папки" if language == 'ru' else "❌ Folder creation error"
            await update.message.reply_text(error_msg)
    
    async def _execute_create_archive_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, archive_name: str, language: str):
        """Execute create archive command."""
        try:
            # Create archive logic here
            if language == 'ru':
                response = f"📦 Архив '{archive_name}' создан успешно"
            else:
                response = f"📦 Archive '{archive_name}' created successfully"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Create archive error: {e}")
            error_msg = "❌ Ошибка создания архива" if language == 'ru' else "❌ Archive creation error"
            await update.message.reply_text(error_msg)
    
    async def _execute_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, language: str):
        """Execute list command."""
        try:
            resources = await self.storage.get_resources_by_category(category)
            
            if not resources:
                if language == 'ru':
                    response = f"📋 В категории '{category}' нет ресурсов"
                else:
                    response = f"📋 No resources in category '{category}'"
            else:
                if language == 'ru':
                    response = f"📋 Ресурсы в категории '{category}' ({len(resources)}):\n\n"
                else:
                    response = f"📋 Resources in category '{category}' ({len(resources)}):\n\n"
                
                for i, resource in enumerate(resources[:20], 1):
                    response += f"{i}. {resource.get('title', 'Untitled')}\n"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"List command error: {e}")
            error_msg = "❌ Ошибка получения списка" if language == 'ru' else "❌ List error"
            await update.message.reply_text(error_msg)
    
    async def _execute_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute help command."""
        if language == 'ru':
            response = """🤖 Помощь по командам:

🔍 Поиск: "найди код Python" или "поиск по React"
🧠 Семантический поиск: "семантический поиск алгоритмы" или "умный поиск машинное обучение"
📁 Создание папки: "создай папку для проектов"
📦 Создание архива: "создай архив старых файлов"
📋 Список: "покажи все ресурсы" или "список кода"
📊 Статистика: "покажи статистику"
📤 Экспорт: "экспорт в JSON"
🔬 Анализ: "анализ данных"
🗑️ Удаление: "удали ресурс 123"

Просто пишите команды естественным языком!"""
        else:
            response = """🤖 Command Help:

🔍 Search: "find Python code" or "search React"
🧠 Semantic search: "semantic search algorithms" or "smart search machine learning"
📁 Create folder: "create folder for projects"
📦 Create archive: "create archive for old files"
📋 List: "show all resources" or "list code"
📊 Statistics: "show statistics"
📤 Export: "export to JSON"
🔬 Analysis: "analyze data"
🗑️ Delete: "delete resource 123"

Just write commands in natural language!"""
        
        await update.message.reply_text(response)
    
    async def _execute_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute statistics command."""
        try:
            stats = await self.storage.get_statistics()
            
            if language == 'ru':
                response = f"""📊 Статистика:

📁 Всего ресурсов: {stats.get('total', 0)}
🔗 Ссылки: {stats.get('links', 0)}
📝 Заметки: {stats.get('notes', 0)}
💻 Код: {stats.get('code', 0)}
📄 Документы: {stats.get('documents', 0)}
🖼️ Изображения: {stats.get('images', 0)}"""
            else:
                response = f"""📊 Statistics:

📁 Total resources: {stats.get('total', 0)}
🔗 Links: {stats.get('links', 0)}
📝 Notes: {stats.get('notes', 0)}
💻 Code: {stats.get('code', 0)}
📄 Documents: {stats.get('documents', 0)}
🖼️ Images: {stats.get('images', 0)}"""
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Stats command error: {e}")
            error_msg = "❌ Ошибка получения статистики" if language == 'ru' else "❌ Statistics error"
            await update.message.reply_text(error_msg)
    
    async def _execute_export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, format_type: str, language: str):
        """Execute export command."""
        try:
            # Export logic here
            if language == 'ru':
                response = f"📤 Экспорт в формате {format_type} начат"
            else:
                response = f"📤 Export in {format_type} format started"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Export command error: {e}")
            error_msg = "❌ Ошибка экспорта" if language == 'ru' else "❌ Export error"
            await update.message.reply_text(error_msg)
    
    async def _execute_analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute analysis command."""
        try:
            # Analysis logic here
            if language == 'ru':
                response = "🔬 Анализ данных запущен"
            else:
                response = "🔬 Data analysis started"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Analysis command error: {e}")
            error_msg = "❌ Ошибка анализа" if language == 'ru' else "❌ Analysis error"
            await update.message.reply_text(error_msg)
    
    async def _execute_delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str, language: str):
        """Execute delete command."""
        try:
            success = self.storage.delete_resource(item_id)
            
            if success:
                if language == 'ru':
                    response = f"🗑️ Ресурс {item_id} успешно удален"
                else:
                    response = f"🗑️ Resource {item_id} deleted successfully"
            else:
                if language == 'ru':
                    response = f"❌ Ресурс {item_id} не найден"
                else:
                    response = f"❌ Resource {item_id} not found"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Delete command error: {e}")
            error_msg = "❌ Ошибка удаления" if language == 'ru' else "❌ Delete error"
            await update.message.reply_text(error_msg)
    
    # Help methods
    async def _send_search_help(self, update: Update, language: str):
        """Send search help message."""
        if language == 'ru':
            response = "🔍 Укажите что искать. Например: 'найди код на Python'"
        else:
            response = "🔍 Please specify what to search for. Example: 'find Python code'"
        await update.message.reply_text(response)
    
    async def _send_semantic_search_help(self, update: Update, language: str):
        """Send semantic search help message."""
        if language == 'ru':
            response = "🧠 Укажите запрос для семантического поиска. Например: 'семантический поиск алгоритмы сортировки'"
        else:
            response = "🧠 Please specify query for semantic search. Example: 'semantic search sorting algorithms'"
        await update.message.reply_text(response)
    
    async def _send_folder_help(self, update: Update, language: str):
        """Send folder creation help message."""
        if language == 'ru':
            response = "📁 Укажите название папки. Например: 'создай папку для React проектов'"
        else:
            response = "📁 Please specify folder name. Example: 'create folder for React projects'"
        await update.message.reply_text(response)
    
    async def _send_archive_help(self, update: Update, language: str):
        """Send archive creation help message."""
        if language == 'ru':
            response = "📦 Укажите название архива. Например: 'создай архив старых проектов'"
        else:
            response = "📦 Please specify archive name. Example: 'create archive for old projects'"
        await update.message.reply_text(response)
    
    async def _send_delete_help(self, update: Update, language: str):
        """Send delete help message."""
        if language == 'ru':
            response = "🗑️ Укажите ID ресурса для удаления. Например: 'удали ресурс 123'"
        else:
            response = "🗑️ Please specify resource ID to delete. Example: 'delete resource 123'"
        await update.message.reply_text(response)
    
    async def semantic_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /semantic_search command."""
        try:
            query = ' '.join(context.args) if context.args else ''
            
            if not query:
                await update.message.reply_text(
                    "🧠 Укажите запрос для семантического поиска.\n"
                    "Пример: /semantic_search алгоритмы сортировки\n\n"
                    "🧠 Please specify a query for semantic search.\n"
                    "Example: /semantic_search sorting algorithms"
                )
                return
            
            # Check if semantic search is available
            if not hasattr(self.storage, 'semantic_search_engine') or self.storage.semantic_search_engine is None:
                await update.message.reply_text(
                    "🧠 Семантический поиск недоступен. Убедитесь, что установлены зависимости: sentence-transformers и faiss-cpu\n\n"
                    "🧠 Semantic search is not available. Make sure dependencies are installed: sentence-transformers and faiss-cpu"
                )
                return
            
            # Show processing message
            status_msg = await update.message.reply_text("🧠 Выполняю семантический поиск... / Performing semantic search...")
            
            results = await self.storage.semantic_search_resources(query, limit=10)
            
            if not results:
                response = f"🧠 По семантическому запросу '{query}' ничего не найдено\n\n🧠 No semantic results found for '{query}'"
            else:
                response = f"🧠 Найдено {len(results)} семантических результатов по запросу '{query}': / Found {len(results)} semantic results for '{query}':\n\n"
                
                for i, result in enumerate(results, 1):
                    resource = result.get('resource', {})
                    score = result.get('score', 0.0)
                    response += f"{i}. {resource.get('title', 'Untitled')}\n"
                    response += f"   📁 {resource.get('category', 'Unknown')}\n"
                    response += f"   🎯 Релевантность / Relevance: {score:.2f}\n"
                    if resource.get('description'):
                        response += f"   📝 {resource['description'][:100]}...\n"
                    response += "\n"
            
            # Delete status message and send results
            try:
                await status_msg.delete()
            except:
                pass
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Semantic search command error: {e}")
            await update.message.reply_text(
                "❌ Ошибка семантического поиска / Semantic search error"
            )
    
    async def filter_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /filter command for filtering resources."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "🔧 Фильтрация ресурсов:\n"
                    "Использование: /filter category:<категория> [date_from:YYYY-MM-DD] [date_to:YYYY-MM-DD]\n\n"
                    "Примеры:\n"
                    "• /filter category:code\n"
                    "• /filter date_from:2024-01-01\n"
                    "• /filter category:docs date_from:2024-01-01 date_to:2024-12-31\n\n"
                    "🔧 Resource filtering:\n"
                    "Usage: /filter category:<category> [date_from:YYYY-MM-DD] [date_to:YYYY-MM-DD]\n\n"
                    "Examples:\n"
                    "• /filter category:code\n"
                    "• /filter date_from:2024-01-01\n"
                    "• /filter category:docs date_from:2024-01-01 date_to:2024-12-31"
                )
                return
            
            # Parse filter parameters
            category_filter = None
            date_from = None
            date_to = None
            
            for arg in context.args:
                if arg.startswith('category:'):
                    category_filter = arg.split(':', 1)[1]
                elif arg.startswith('date_from:'):
                    date_from = arg.split(':', 1)[1]
                elif arg.startswith('date_to:'):
                    date_to = arg.split(':', 1)[1]
            
            if not any([category_filter, date_from, date_to]):
                await update.message.reply_text(
                    "❌ Укажите хотя бы один фильтр\n\n"
                    "❌ Please specify at least one filter"
                )
                return
            
            # Get all resources and apply filters
            all_resources = self.storage.get_all_resources()
            filtered_resources = self.storage._apply_filters(
                all_resources,
                category_filter=category_filter,
                date_from=date_from,
                date_to=date_to
            )
            
            if not filtered_resources:
                await update.message.reply_text(
                    "🔧 По указанным фильтрам ничего не найдено\n\n"
                    "🔧 No resources found with specified filters"
                )
            else:
                response = f"🔧 Найдено {len(filtered_resources)} ресурсов:\n\n"
                response += f"🔧 Found {len(filtered_resources)} resources:\n\n"
                
                for i, resource in enumerate(filtered_resources[:10], 1):
                    response += f"{i}. {resource.get('title', 'Untitled')}\n"
                    response += f"   📁 {resource.get('category', 'Unknown')}\n"
                    if resource.get('description'):
                        response += f"   📝 {resource['description'][:100]}...\n"
                    response += "\n"
                
                if len(filtered_resources) > 10:
                    response += f"... и еще {len(filtered_resources) - 10} ресурсов\n"
                    response += f"... and {len(filtered_resources) - 10} more resources"
                
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Filter command error: {e}")
            await update.message.reply_text(
                "❌ Ошибка фильтрации\n\n"
                "❌ Filter error"
            )
    
    # Other existing methods would go here...
    # (start_command, help_command, etc.)