"""
Оптимизированная версия бота для Render.
Включает полную функциональность с улучшениями производительности.
"""

import asyncio
import logging
import os
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

from .classifier_render import ContentClassifier
from .config_render import get_ai_config, TELEGRAM_BOT_TOKEN
from ..utils.storage_render import ResourceStorage
from ..utils.rate_limiter_render import RateLimiter
from ..handlers.command_interpreter_render import NaturalLanguageCommandInterpreter, CommandType

logger = logging.getLogger(__name__)

class DevDataSorterBot:
    """Оптимизированная версия бота для Render."""
    
    def __init__(self, token: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.ai_config = get_ai_config()
        self.storage = ResourceStorage(enable_semantic_search=True)
        self.classifier = ContentClassifier()
        self.rate_limiter = RateLimiter()
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
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        self.app.add_handler(CommandHandler("categories", self.categories_command))
        self.app.add_handler(CommandHandler("export", self.export_command))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_file))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Callback query handler
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = """🤖 Добро пожаловать в DevDataSorter!

Я помогу вам автоматически классифицировать и организовать ваши ресурсы для разработки.

🔧 Основные возможности:
• Автоматическая классификация контента
• Семантический поиск по ресурсам
• Обработка файлов и изображений
• Интеллектуальные команды на естественном языке
• Экспорт и резервное копирование

🚀 Команды:
/help - Полная справка
/search <запрос> - Поиск ресурсов
/semantic_search <запрос> - Семантический поиск
/list - Список ресурсов
/stats - Статистика
/categories - Категории

💡 Просто отправьте мне текст, ссылки, файлы или используйте естественные команды:
• "найди все про React"
• "покажи статистику"
• "создай папку для проектов"

🌟 Версия: Render Full"""
        
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """📚 Полная справка DevDataSorter:

🔧 Основные команды:
/start - Запустить бота
/help - Показать эту справку
/search <запрос> - Поиск ресурсов
/semantic_search <запрос> - Семантический поиск
/list [категория] - Список ресурсов
/stats - Статистика бота
/categories - Все категории
/export - Экспорт данных

🤖 Интеллектуальные команды:
Используйте естественный язык:
• "найди код на Python"
• "покажи все документацию"
• "семантический поиск алгоритмы"
• "статистика по категориям"
• "создай папку для React проектов"

📁 Поддержка файлов:
• Отправляйте изображения для анализа
• Загружайте документы (PDF, TXT, DOCX)
• Автоматическая классификация файлов

🔍 Типы поиска:
• Текстовый поиск - быстрый поиск по ключевым словам
• Семантический поиск - поиск по смыслу и контексту

📊 Категории:
• Frontend (React, Vue, Angular)
• Backend (Node.js, Python, PHP)
• Database (SQL, MongoDB)
• Tools (Docker, Git, Webpack)
• Documentation
• Code examples
• И многие другие...

💡 Автоматическая классификация:
Просто отправьте любой контент, и я автоматически определю категорию!"""
        
        await update.message.reply_text(help_text)
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        if not context.args:
            await update.message.reply_text(
                "🔍 Использование: /search <запрос>\n"
                "Пример: /search React hooks\n\n"
                "Для семантического поиска используйте:\n"
                "/semantic_search <запрос>"
            )
            return
        
        user_id = update.effective_user.id
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(user_id):
            await update.message.reply_text(
                "⏰ Слишком много запросов. Подождите немного."
            )
            return
        
        query = ' '.join(context.args)
        
        # Show processing message
        status_msg = await update.message.reply_text("🔍 Поиск...")
        
        try:
            results = self.storage.search_resources(query, use_semantic=False)
            
            if not results:
                response = f"🔍 По запросу '{query}' ничего не найдено"
            else:
                response = f"🔍 Найдено {len(results)} результатов по запросу '{query}':\n\n"
                
                for i, result in enumerate(results[:10], 1):
                    response += f"{i}. 📁 {result.get('category', 'Unknown')}\n"
                    response += f"   📝 {result['content'][:100]}...\n"
                    if result.get('description'):
                        response += f"   💬 {result['description'][:50]}...\n"
                    response += f"   🆔 {result['id']}\n\n"
                
                if len(results) > 10:
                    response += f"... и еще {len(results) - 10} результатов"
            
            await status_msg.edit_text(response)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await status_msg.edit_text("❌ Ошибка поиска")
    
    async def semantic_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /semantic_search command."""
        if not context.args:
            await update.message.reply_text(
                "🧠 Использование: /semantic_search <запрос>\n"
                "Пример: /semantic_search алгоритмы сортировки\n\n"
                "Семантический поиск находит ресурсы по смыслу, а не только по ключевым словам."
            )
            return
        
        user_id = update.effective_user.id
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(user_id):
            await update.message.reply_text(
                "⏰ Слишком много запросов. Подождите немного."
            )
            return
        
        query = ' '.join(context.args)
        
        # Show processing message
        status_msg = await update.message.reply_text("🧠 Семантический поиск...")
        
        try:
            # Check if semantic search is available
            if not hasattr(self.storage, 'semantic_search_engine') or self.storage.semantic_search_engine is None:
                await status_msg.edit_text(
                    "🧠 Семантический поиск недоступен. Используется обычный поиск."
                )
                results = self.storage.search_resources(query, use_semantic=False)
            else:
                results = await self.storage.semantic_search_resources(query, limit=10)
            
            if not results:
                response = f"🧠 По семантическому запросу '{query}' ничего не найдено"
            else:
                response = f"🧠 Найдено {len(results)} семантических результатов по запросу '{query}':\n\n"
                
                for i, result in enumerate(results, 1):
                    if isinstance(result, dict) and 'resource' in result:
                        # Semantic search result format
                        resource = result['resource']
                        score = result.get('score', 0.0)
                        response += f"{i}. 📁 {resource.get('category', 'Unknown')}\n"
                        response += f"   📝 {resource['content'][:100]}...\n"
                        response += f"   🎯 Релевантность: {score:.2f}\n"
                        response += f"   🆔 {resource['id']}\n\n"
                    else:
                        # Regular search result format
                        response += f"{i}. 📁 {result.get('category', 'Unknown')}\n"
                        response += f"   📝 {result['content'][:100]}...\n"
                        if result.get('similarity_score'):
                            response += f"   🎯 Релевантность: {result['similarity_score']:.2f}\n"
                        response += f"   🆔 {result['id']}\n\n"
            
            await status_msg.edit_text(response)
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            await status_msg.edit_text("❌ Ошибка семантического поиска")
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command."""
        category_filter = context.args[0] if context.args else None
        
        if category_filter:
            resources = self.storage.get_resources_by_category(category_filter)
            title = f"📋 Ресурсы в категории '{category_filter}'"
        else:
            resources = self.storage.get_all_resources()
            title = "📋 Все ресурсы"
        
        if not resources:
            await update.message.reply_text(f"{title}: пусто")
            return
        
        response = f"{title} ({len(resources)}):\n\n"
        
        # Show first 15 resources
        for i, resource in enumerate(resources[:15], 1):
            response += f"{i}. 📁 {resource.get('category', 'Unknown')}\n"
            response += f"   📝 {resource['content'][:80]}...\n"
            response += f"   🕒 {resource['timestamp'][:10]}\n"
            response += f"   🆔 {resource['id']}\n\n"
        
        if len(resources) > 15:
            response += f"... и еще {len(resources) - 15} ресурсов\n"
            response += "Используйте /search для поиска конкретных ресурсов"
        
        await update.message.reply_text(response)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        try:
            stats = self.storage.get_statistics()
            categories = self.storage.get_categories()
            
            response = f"""📊 Статистика DevDataSorter:

📚 Всего ресурсов: {stats['total_resources']}
📂 Категорий: {stats['categories_count']}
🎯 Средняя уверенность: {stats.get('average_confidence', 0):.1%}
🔗 Всего URL: {stats.get('total_urls', 0)}
📁 Файловых ресурсов: {stats.get('file_resources', 0)}

📈 Топ-5 категорий:"""
            
            # Show top 5 categories
            sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            for i, (category, count) in enumerate(sorted_categories[:5], 1):
                response += f"\n  {i}. {category}: {count}"
            
            if stats.get('popular_category'):
                response += f"\n\n🏆 Самая популярная: {stats['popular_category']}"
            
            # Semantic search info
            if stats.get('semantic_search_enabled'):
                response += f"\n\n🧠 Семантический поиск: включен"
                if 'semantic_search' in stats:
                    sem_stats = stats['semantic_search']
                    response += f"\n   📊 Индексированных ресурсов: {sem_stats.get('indexed_resources', 0)}"
            else:
                response += f"\n\n🧠 Семантический поиск: отключен"
            
            response += f"\n\n💡 Версия: Render Full"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики")
    
    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /categories command."""
        try:
            categories = self.storage.get_categories()
            
            if not categories:
                await update.message.reply_text("📂 Пока нет категорий")
                return
            
            response = f"📂 Все категории ({len(categories)}):\n\n"
            
            # Sort categories by count
            sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            
            for category, count in sorted_categories:
                response += f"📁 {category}: {count}\n"
            
            response += f"\nИспользуйте /list <категория> для просмотра ресурсов"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Categories error: {e}")
            await update.message.reply_text("❌ Ошибка получения категорий")
    
    async def export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export command."""
        try:
            # Show processing message
            status_msg = await update.message.reply_text("📤 Подготовка экспорта...")
            
            # Export data
            export_data = self.storage.export_data()
            
            # Create file
            filename = f"devdatasorter_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Send as document
            from io import BytesIO
            file_buffer = BytesIO(export_data.encode('utf-8'))
            file_buffer.name = filename
            
            await status_msg.delete()
            await update.message.reply_document(
                document=file_buffer,
                filename=filename,
                caption=f"📤 Экспорт данных DevDataSorter\n"
                       f"📊 Ресурсов: {len(self.storage.resources)}\n"
                       f"📂 Категорий: {len(self.storage.categories)}\n"
                       f"🕒 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            await update.message.reply_text("❌ Ошибка экспорта данных")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        content = update.message.text
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(user_id):
            await update.message.reply_text(
                "⏰ Слишком много запросов. Подождите немного."
            )
            return
        
        # Try to interpret as natural language command
        command_intent = await self.command_interpreter.interpret_command(content)
        
        if command_intent.command_type != CommandType.UNKNOWN and command_intent.confidence > 0.6:
            await self._handle_command_intent(update, context, command_intent)
            return
        
        # Process as regular content
        await self._process_content(update, context, content, user_id, username)
    
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
                    results = self.storage.search_resources(query, use_semantic=False)
                    await self._send_search_results(update, query, results, language)
                else:
                    await self._send_search_help(update, language)
            
            elif command_type == CommandType.SEMANTIC_SEARCH:
                query = parameters.get('query', '')
                if query:
                    if hasattr(self.storage, 'semantic_search_engine') and self.storage.semantic_search_engine:
                        results = await self.storage.semantic_search_resources(query, limit=10)
                    else:
                        results = self.storage.search_resources(query, use_semantic=False)
                    await self._send_semantic_search_results(update, query, results, language)
                else:
                    await self._send_semantic_search_help(update, language)
            
            elif command_type == CommandType.LIST:
                category = parameters.get('category', 'all')
                await self._execute_list_command(update, context, category, language)
            
            elif command_type == CommandType.HELP:
                await self.help_command(update, context)
            
            elif command_type == CommandType.STATS:
                await self.stats_command(update, context)
            
            # Delete status message
            try:
                await status_msg.delete()
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error handling command intent: {e}")
            error_msg = "❌ Произошла ошибка при выполнении команды" if command_intent.language == 'ru' else "❌ Error executing command"
            await update.message.reply_text(error_msg)
    
    async def _process_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE, content: str, user_id: int, username: str):
        """Process regular content for classification."""
        # Show processing message
        status_msg = await update.message.reply_text("🤖 Анализирую контент...")
        
        try:
            # Extract URLs if present
            urls = self._extract_urls(content)
            
            # Classify content
            classification = await self.classifier.classify_content(content, urls)
            
            # Add to storage
            resource_id = self.storage.add_resource(
                content=content,
                category=classification['category'],
                user_id=user_id,
                username=username,
                confidence=classification['confidence'],
                description=classification['description'],
                urls=urls,
                subcategory=classification.get('subcategory'),
                programming_languages=classification.get('programming_languages', []),
                technology_stack=classification.get('technology_stack', [])
            )
            
            # Prepare response
            response = f"✅ Ресурс сохранен!\n\n"
            response += f"📁 Категория: {classification['category']}\n"
            
            if classification.get('subcategory'):
                response += f"📂 Подкатегория: {classification['subcategory']}\n"
            
            response += f"🎯 Уверенность: {classification['confidence']:.1%}\n"
            response += f"📝 Описание: {classification['description']}\n"
            response += f"🆔 ID: {resource_id}"
            
            if urls:
                response += f"\n🔗 Найдено URL: {len(urls)}"
            
            if classification.get('programming_languages'):
                langs = ', '.join(classification['programming_languages'][:3])
                response += f"\n💻 Языки: {langs}"
            
            if classification.get('technology_stack'):
                tech = ', '.join(classification['technology_stack'][:3])
                response += f"\n🛠️ Технологии: {tech}"
            
            # Delete status message and send result
            await status_msg.delete()
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error processing content: {e}")
            await status_msg.edit_text("❌ Произошла ошибка при обработке контента")
    
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file uploads."""
        await update.message.reply_text("📁 Обработка файлов временно недоступна в этой версии")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads."""
        await update.message.reply_text("🖼️ Обработка изображений временно недоступна в этой версии")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries."""
        query = update.callback_query
        await query.answer()
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        return list(set(urls))
    
    async def _send_search_results(self, update: Update, query: str, results: List[Dict], language: str):
        """Send search results."""
        if not results:
            if language == 'ru':
                response = f"🔍 По запросу '{query}' ничего не найдено"
            else:
                response = f"🔍 No results found for '{query}'"
        else:
            if language == 'ru':
                response = f"🔍 Найдено {len(results)} результатов по запросу '{query}':\n\n"
            else:
                response = f"🔍 Found {len(results)} results for '{query}':\n\n"
            
            for i, result in enumerate(results[:10], 1):
                response += f"{i}. 📁 {result.get('category', 'Unknown')}\n"
                response += f"   📝 {result['content'][:100]}...\n"
                if result.get('description'):
                    response += f"   💬 {result['description'][:50]}...\n"
                response += f"   🆔 {result['id']}\n\n"
            
            if len(results) > 10:
                if language == 'ru':
                    response += f"... и еще {len(results) - 10} результатов"
                else:
                    response += f"... and {len(results) - 10} more results"
        
        await update.message.reply_text(response)
    
    async def _send_semantic_search_results(self, update: Update, query: str, results: List[Dict], language: str):
        """Send semantic search results."""
        if not results:
            if language == 'ru':
                response = f"🧠 По семантическому запросу '{query}' ничего не найдено"
            else:
                response = f"🧠 No semantic results found for '{query}'"
        else:
            if language == 'ru':
                response = f"🧠 Найдено {len(results)} семантических результатов по запросу '{query}':\n\n"
            else:
                response = f"🧠 Found {len(results)} semantic results for '{query}':\n\n"
            
            for i, result in enumerate(results, 1):
                if isinstance(result, dict) and 'resource' in result:
                    resource = result['resource']
                    score = result.get('score', 0.0)
                    response += f"{i}. 📁 {resource.get('category', 'Unknown')}\n"
                    response += f"   📝 {resource['content'][:100]}...\n"
                    response += f"   🎯 Релевантность: {score:.2f}\n"
                    response += f"   🆔 {resource['id']}\n\n"
                else:
                    response += f"{i}. 📁 {result.get('category', 'Unknown')}\n"
                    response += f"   📝 {result['content'][:100]}...\n"
                    if result.get('similarity_score'):
                        response += f"   🎯 Релевантность: {result['similarity_score']:.2f}\n"
                    response += f"   🆔 {result['id']}\n\n"
        
        await update.message.reply_text(response)
    
    async def _send_search_help(self, update: Update, language: str):
        """Send search help."""
        if language == 'ru':
            response = "🔍 Укажите что искать. Например: 'найди код на Python'"
        else:
            response = "🔍 Please specify what to search for. Example: 'find Python code'"
        await update.message.reply_text(response)
    
    async def _send_semantic_search_help(self, update: Update, language: str):
        """Send semantic search help."""
        if language == 'ru':
            response = "🧠 Укажите запрос для семантического поиска. Например: 'семантический поиск алгоритмы сортировки'"
        else:
            response = "🧠 Please specify query for semantic search. Example: 'semantic search sorting algorithms'"
        await update.message.reply_text(response)
    
    async def _execute_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, language: str):
        """Execute list command."""
        try:
            if category == 'all':
                resources = self.storage.get_all_resources()
                if language == 'ru':
                    title = "📋 Все ресурсы"
                else:
                    title = "📋 All resources"
            else:
                resources = self.storage.get_resources_by_category(category)
                if language == 'ru':
                    title = f"📋 Ресурсы в категории '{category}'"
                else:
                    title = f"📋 Resources in category '{category}'"
            
            if not resources:
                if language == 'ru':
                    response = f"{title}: пусто"
                else:
                    response = f"{title}: empty"
            else:
                response = f"{title} ({len(resources)}):\n\n"
                
                for i, resource in enumerate(resources[:10], 1):
                    response += f"{i}. 📁 {resource.get('category', 'Unknown')}\n"
                    response += f"   📝 {resource['content'][:80]}...\n"
                    response += f"   🆔 {resource['id']}\n\n"
                
                if len(resources) > 10:
                    if language == 'ru':
                        response += f"... и еще {len(resources) - 10} ресурсов"
                    else:
                        response += f"... and {len(resources) - 10} more resources"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"List command error: {e}")
            error_msg = "❌ Ошибка получения списка" if language == 'ru' else "❌ List error"
            await update.message.reply_text(error_msg)
    
    def run(self):
        """Run the bot in polling mode."""
        logger.info("🚀 Starting DevDataSorter bot (polling mode)...")
        logger.info(f"🤖 AI Provider: {self.ai_config['provider']}")
        
        try:
            self.app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise
    
    async def run_async(self):
        """Run the bot in async mode for better performance."""
        logger.info("🚀 Starting DevDataSorter bot (async mode)...")
        logger.info(f"🤖 AI Provider: {self.ai_config['provider']}")
        
        try:
            async with self.app:
                await self.app.start()
                await self.app.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True
                )
                
                # Keep running
                await asyncio.Event().wait()
                
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise
        finally:
            await self.app.stop()