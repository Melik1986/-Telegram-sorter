#!/usr/bin/env python3
"""
Telegram bot for DevDataSorter.
Handles user interactions and content classification.
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from src.core.classifier import ContentClassifier
from src.utils.storage import ResourceStorage
from src.utils.utils import extract_urls, format_resource_list
from src.core.config import get_telegram_token
from src.utils.cache import get_cache_manager
from scripts.backup import get_backup_manager
from src.utils.rate_limiter import get_rate_limiter, get_command_rate_limiter
from src.handlers.file_handler import get_file_handler
from src.utils.i18n import get_i18n_manager, t
from src.core.config import get_security_report

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, bot_token):
        """Initialize the Telegram bot with AI classifier and storage."""
        self.bot_token = bot_token
        self.classifier = ContentClassifier()
        self.storage = ResourceStorage()
        self.cache = get_cache_manager()
        self.backup = get_backup_manager()
        self.rate_limiter = get_rate_limiter()
        self.command_rate_limiter = get_command_rate_limiter()
        self.file_handler = get_file_handler()
        self.i18n = get_i18n_manager()
        self.app = Application.builder().token(bot_token).build()
        self._setup_handlers()
        
        # Start automatic backup
        self.backup.start_automatic_backup(self._get_storage_data)
        
        logger.info("Telegram bot initialized with all systems")
    
    def _get_storage_data(self):
        """Get current storage data for backup."""
        return self.storage.get_all_resources()
    
    def _setup_handlers(self):
        """Set up command and message handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("add", self.add_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("categories", self.categories_command))
        self.app.add_handler(CommandHandler("list", self.list_command))
        
        # New commands
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        self.app.add_handler(CommandHandler("backup", self.backup_command))
        self.app.add_handler(CommandHandler("cache", self.cache_command))
        self.app.add_handler(CommandHandler("limits", self.limits_command))
        self.app.add_handler(CommandHandler("export", self.export_command))
        self.app.add_handler(CommandHandler("import", self.import_command))
        self.app.add_handler(CommandHandler("clear", self.clear_command))
        # self.app.add_handler(CommandHandler("security", self.security_command))
        # self.app.add_handler(CommandHandler("language", self.language_command))
        
        # File handlers
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        # Message handler for content classification
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'start')
        if not allowed:
            await update.message.reply_text(t('errors.rate_limit', user_id))
            return
        
        welcome_text = self.i18n.get_welcome_message(user_id)
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'help')
        if not allowed:
            await update.message.reply_text(t('errors.rate_limit', user_id))
            return
        
        help_text = self.i18n.get_help_message(user_id)
        await update.message.reply_text(help_text)
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command to manually add resources."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'add')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        if not context.args:
            await update.message.reply_text(
                "Пожалуйста, укажите контент для добавления.\n"
                "Please specify content to add.\n"
                "Пример/Example: /add https://example.com"
            )
            return
        
        content = " ".join(context.args)
        await self._process_content(update, content, manual=True)
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command to search for resources."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'search')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите поисковый запрос.\n"
                "Пример: /search Python tutorial\n\n"
                "❌ Please provide a search query.\n"
                "Example: /search Python tutorial"
            )
            return
        
        query = " ".join(context.args)
        
        # Check cache first
        cache_key = f"search:{query}"
        cached_results = self.cache.get(cache_key)
        
        if cached_results:
            results = cached_results
        else:
            results = self.storage.search_resources(query)
            # Cache results for 5 minutes
            self.cache.set(cache_key, results, ttl=300)
        
        if not results:
            await update.message.reply_text(
                f"🔍 По запросу '{query}' ничего не найдено.\n"
                f"🔍 No results found for '{query}'."
            )
            return
        
        response = f"🔍 Результаты поиска для '{query}' / Search results for '{query}':\n\n"
        
        for resource_id, resource in results[:10]:  # Limit to 10 results
            category_emoji = self._get_category_emoji(resource['category'])
            response += f"{category_emoji} **{resource['category']}**\n"
            response += f"📝 {resource['description'][:100]}{'...' if len(resource['description']) > 100 else ''}\n"
            if resource.get('url'):
                response += f"🔗 {resource['url']}\n"
            response += f"🆔 ID: `{resource_id}`\n\n"
        
        if len(results) > 10:
            response += f"... и еще {len(results) - 10} результатов / ... and {len(results) - 10} more results"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /categories command to show all categories."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'categories')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        # Check cache first
        cache_key = "categories"
        cached_categories = self.cache.get(cache_key)
        
        if cached_categories:
            categories = cached_categories
        else:
            categories = self.storage.get_categories_summary()
            # Cache categories for 2 minutes
            self.cache.set(cache_key, categories, ttl=120)
        
        if not categories:
            await update.message.reply_text(
                "📂 Пока нет сохраненных категорий.\n"
                "📂 No saved categories yet."
            )
            return
        
        response = "📂 Доступные категории / Available categories:\n\n"
        
        for category, count in categories.items():
            emoji = self._get_category_emoji(category)
            response += f"{emoji} **{category}** ({count} ресурсов/resources)\n"
        
        response += "\n💡 Используйте /list [category] для просмотра ресурсов категории\n"
        response += "💡 Use /list [category] to view category resources"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command to show resources, optionally filtered by category."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'list')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        category_filter = None
        if context.args:
            category_filter = " ".join(context.args).lower()
        
        # Check cache first
        cache_key = f"list:{category_filter or 'all'}"
        cached_resources = self.cache.get(cache_key)
        
        if cached_resources:
            resources = cached_resources
        else:
            resources = self.storage.get_all_resources()
            
            if category_filter:
                resources = {rid: res for rid, res in resources.items() 
                            if res['category'].lower() == category_filter}
            
            # Cache results for 2 minutes
            self.cache.set(cache_key, resources, ttl=120)
        
        if not resources:
            if category_filter:
                await update.message.reply_text(
                    f"📂 В категории '{category_filter}' нет ресурсов.\n"
                    f"📂 No resources in category '{category_filter}'."
                )
            else:
                await update.message.reply_text(
                    "📂 Пока нет сохраненных ресурсов.\n"
                    "📂 No saved resources yet."
                )
            return
        
        # Limit to 20 resources to avoid message length issues
        resource_items = list(resources.items())[:20]
        
        if category_filter:
            response = f"📂 Ресурсы в категории '{category_filter}' / Resources in category '{category_filter}':\n\n"
        else:
            response = "📂 Все ресурсы / All resources:\n\n"
        
        for resource_id, resource in resource_items:
            category_emoji = self._get_category_emoji(resource['category'])
            response += f"{category_emoji} **{resource['category']}**\n"
            response += f"📝 {resource['description'][:100]}{'...' if len(resource['description']) > 100 else ''}\n"
            if resource.get('url'):
                response += f"🔗 {resource['url']}\n"
            response += f"🆔 ID: `{resource_id}`\n\n"
        
        if len(resources) > 20:
            response += f"... и еще {len(resources) - 20} ресурсов / ... and {len(resources) - 20} more resources\n"
            response += "💡 Используйте /search для поиска конкретных ресурсов / Use /search to find specific resources"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages for automatic classification."""
        content = update.message.text
        await self._process_content(update, content, manual=False)
    
    async def _process_content(self, update: Update, content: str, manual: bool = False, file_info=None):
        """Process and classify content."""
        try:
            # Show typing indicator
            await update.message.reply_text("🔄 Анализирую контент... / Analyzing content...")
            
            # Extract URLs if present
            urls = extract_urls(content)
            
            # Classify the content
            classification = await self.classifier.classify_content(content, urls)
            
            if not classification:
                await update.message.reply_text(
                    "❌ Не удалось классифицировать контент.\n"
                    "Failed to classify content."
                )
                return
            
            # Prepare additional data for file resources
            additional_data = {}
            if file_info:
                additional_data.update({
                    'file_type': file_info.get('file_type'),
                    'file_size': file_info.get('file_size'),
                    'mime_type': file_info.get('mime_type'),
                    'file_path': file_info.get('file_path')
                })
            
            # Store the resource
            resource_id = self.storage.add_resource(
                content=content,
                category=classification['category'],
                user_id=update.effective_user.id,
                username=update.effective_user.username,
                subcategory=classification.get('subcategory'),
                confidence=classification.get('confidence', 0.0),
                description=classification.get('description', ''),
                urls=urls,
                **additional_data
            )
            
            # Format response
            category_emoji = self._get_category_emoji(classification['category'])
            confidence_text = f" ({classification.get('confidence', 0):.1%} уверенности)" if classification.get('confidence') else ""
            
            response = f"""
✅ Контент успешно классифицирован! / Content successfully classified!

{category_emoji} Категория / Category: {classification['category']}{confidence_text}
📝 Описание / Description: {classification.get('description', 'Нет описания / No description')}
🆔 ID: {resource_id}

{f"🔗 URLs найдены / URLs found: {len(urls)}" if urls else ""}
            """
            
            if file_info:
                response += f"\n📁 Тип файла / File type: {file_info.get('file_type', 'Unknown')}"
                if file_info.get('file_size'):
                    size_mb = file_info['file_size'] / (1024 * 1024)
                    response += f"\n📏 Размер / Size: {size_mb:.2f} MB"
            
            if classification.get('subcategory'):
                response += f"\n📂 Подкатегория / Subcategory: {classification['subcategory']}"
            
            await update.message.reply_text(response.strip())
            
        except Exception as e:
            logger.error(f"Error processing content: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке контента.\n"
                "An error occurred while processing content."
            )
    
    def _get_category_emoji(self, category: str) -> str:
        """Get emoji for category."""
        emoji_map = {
            'code_examples': '💻',
            'tutorials': '📚',
            'videos': '🎥',
            'mockups': '🎨',
            'documentation': '📖',
            'tools': '🔧',
            'articles': '📰',
            'libraries': '📦',
            'frameworks': '🏗️',
            'other': '📄'
        }
        return emoji_map.get(category, '📄')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command to show bot statistics."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'stats')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        # Get statistics
        all_resources = self.storage.get_all_resources()
        categories = self.storage.get_categories()
        cache_stats = self.cache.get_stats()
        file_stats = self.file_handler.get_stats()
        
        response = "📊 Статистика бота / Bot Statistics:\n\n"
        response += f"📚 Всего ресурсов / Total resources: {len(all_resources)}\n"
        response += f"📂 Категорий / Categories: {len(categories)}\n\n"
        
        response += "📁 Файлы / Files:\n"
        response += f"• Обработано изображений / Images processed: {file_stats.get('images_processed', 0)}\n"
        response += f"• Обработано документов / Documents processed: {file_stats.get('documents_processed', 0)}\n"
        response += f"• Размер кэша файлов / File cache size: {file_stats.get('cache_size_mb', 0):.1f} MB\n\n"
        
        response += "💾 Кэш / Cache:\n"
        response += f"• Записей в кэше / Cache entries: {cache_stats.get('entries', 0)}\n"
        response += f"• Попаданий / Hits: {cache_stats.get('hits', 0)}\n"
        response += f"• Промахов / Misses: {cache_stats.get('misses', 0)}\n"
        if cache_stats.get('hits', 0) + cache_stats.get('misses', 0) > 0:
            hit_rate = cache_stats.get('hits', 0) / (cache_stats.get('hits', 0) + cache_stats.get('misses', 0)) * 100
            response += f"• Эффективность / Hit rate: {hit_rate:.1f}%\n"
        
        await update.message.reply_text(response)
    
    async def backup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /backup command to create manual backup."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'backup')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        try:
            backup_file = self.backup_manager.create_backup()
            backups = self.backup_manager.list_backups()
            
            response = f"✅ Резервная копия создана / Backup created:\n"
            response += f"📁 Файл / File: {backup_file}\n\n"
            response += f"📊 Всего резервных копий / Total backups: {len(backups)}\n"
            
            if len(backups) > 5:
                response += "\n💡 Рекомендуется очистить старые копии / Consider cleaning old backups"
            
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка создания резервной копии / Backup creation error:\n{str(e)}"
            )
    
    async def cache_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cache command for cache management."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'cache')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        if context.args and context.args[0].lower() == 'clear':
            self.cache.clear()
            await update.message.reply_text(
                "✅ Кэш очищен / Cache cleared"
            )
            return
        
        stats = self.cache.get_stats()
        response = "💾 Управление кэшем / Cache Management:\n\n"
        response += f"📊 Записей / Entries: {stats.get('entries', 0)}\n"
        response += f"📈 Попаданий / Hits: {stats.get('hits', 0)}\n"
        response += f"📉 Промахов / Misses: {stats.get('misses', 0)}\n"
        
        if stats.get('hits', 0) + stats.get('misses', 0) > 0:
            hit_rate = stats.get('hits', 0) / (stats.get('hits', 0) + stats.get('misses', 0)) * 100
            response += f"🎯 Эффективность / Hit rate: {hit_rate:.1f}%\n"
        
        response += "\n💡 Используйте /cache clear для очистки\n"
        response += "💡 Use /cache clear to clear cache"
        
        await update.message.reply_text(response)
    
    async def limits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /limits command to show rate limit information."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'limits')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        response = "⚡ Лимиты запросов / Rate Limits:\n\n"
        response += "📊 Общие лимиты / General limits:\n"
        response += "• 30 запросов в минуту / 30 requests per minute\n"
        response += "• 500 запросов в час / 500 requests per hour\n"
        response += "• Burst: 5 запросов / 5 requests\n\n"
        
        response += "🔧 Лимиты команд / Command limits:\n"
        response += "• /search: 10 в минуту / 10 per minute\n"
        response += "• /add: 20 в минуту / 20 per minute\n"
        response += "• /backup: 3 в час / 3 per hour\n"
        response += "• Файлы / Files: 5 в минуту / 5 per minute\n\n"
        
        response += "💡 При превышении лимитов действует кулдаун\n"
        response += "💡 Cooldown applies when limits are exceeded"
        
        await update.message.reply_text(response)
    
    async def export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export command to export data."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'export')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        try:
            import json
            from datetime import datetime
            
            all_resources = self.storage.get_all_resources()
            categories = self.storage.get_categories()
            
            export_data = {
                'export_date': datetime.now().isoformat(),
                'total_resources': len(all_resources),
                'categories': categories,
                'resources': all_resources
            }
            
            # Create export file
            export_filename = f"devdatasorter_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(export_filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            # Send file to user
            with open(export_filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=export_filename,
                    caption=f"📤 Экспорт данных / Data export\n📊 Ресурсов: {len(all_resources)}\n📂 Категорий: {len(categories)}"
                )
            
            # Clean up
            import os
            os.remove(export_filename)
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка экспорта / Export error:\n{str(e)}"
            )
    
    async def import_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /import command to import data."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'import')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        await update.message.reply_text(
            "📥 Импорт данных / Data Import:\n\n"
            "Отправьте JSON файл с экспортированными данными для импорта.\n"
            "Send a JSON file with exported data to import.\n\n"
            "⚠️ Внимание: это добавит данные к существующим\n"
            "⚠️ Warning: this will add data to existing resources"
        )
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command to clear data."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.rate_limiter.is_allowed(user_id, 'clear')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        if not context.args or context.args[0].lower() != 'confirm':
            await update.message.reply_text(
                "⚠️ Подтверждение очистки / Clear Confirmation:\n\n"
                "Это действие удалит ВСЕ сохраненные ресурсы!\n"
                "This action will delete ALL saved resources!\n\n"
                "Для подтверждения используйте: /clear confirm\n"
                "To confirm use: /clear confirm"
            )
            return
        
        # Clear all data
        self.storage.resources.clear()
        self.storage.categories.clear()
        self.storage.search_index.clear()
        self.cache.clear()
        
        await update.message.reply_text(
            "✅ Все данные очищены / All data cleared\n\n"
            "🔄 Бот готов к новой работе / Bot ready for new work"
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.command_rate_limiter.is_allowed(user_id, 'file')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        try:
            await update.message.reply_text("📸 Обрабатываю изображение... / Processing image...")
            
            result = await self.file_handler.handle_photo(update.message.photo[-1], update.message.caption)
            
            if result:
                # Process the result through classification
                content = f"Image: {result['description']}"
                if result.get('text_content'):
                    content += f"\nText found: {result['text_content']}"
                
                await self._process_content(update, content, file_info=result)
            else:
                await update.message.reply_text(
                    "❌ Не удалось обработать изображение / Failed to process image"
                )
                
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await update.message.reply_text(
                f"❌ Ошибка обработки изображения / Image processing error:\n{str(e)}"
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads."""
        user_id = update.effective_user.id
        
        # Check rate limits
        allowed, reason = self.command_rate_limiter.is_allowed(user_id, 'file')
        if not allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return
        
        try:
            await update.message.reply_text("📄 Обрабатываю документ... / Processing document...")
            
            result = await self.file_handler.handle_document(update.message.document, update.message.caption)
            
            if result:
                # Process the result through classification
                content = f"Document: {result['description']}"
                if result.get('text_content'):
                    content += f"\nContent: {result['text_content'][:500]}..."
                
                await self._process_content(update, content, file_info=result)
            else:
                await update.message.reply_text(
                    "❌ Не удалось обработать документ / Failed to process document"
                )
                
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text(
                f"❌ Ошибка обработки документа / Document processing error:\n{str(e)}"
            )
    
    def run(self):
        """Start the bot."""
        import asyncio
        logger.info("Starting DevDataSorter bot...")
        try:
            # Create event loop if it doesn't exist
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        self.app.run_polling(drop_pending_updates=True)
        logger.info("Bot stopped")
