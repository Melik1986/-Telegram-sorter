"""
Минимальная версия Telegram бота для Railway.
"""

import asyncio
import logging
import os
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from .classifier_minimal import ContentClassifier
from .config_minimal import get_ai_config, TELEGRAM_BOT_TOKEN
from ..utils.storage_minimal import ResourceStorage

logger = logging.getLogger(__name__)

class DevDataSorterBot:
    """Минимальная версия бота для Railway."""
    
    def __init__(self, token: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.ai_config = get_ai_config()
        self.storage = ResourceStorage()
        self.classifier = ContentClassifier()
        
        # Initialize Telegram application
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup bot handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("list", self.list_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = """🤖 Добро пожаловать в DevDataSorter!

Я помогу вам автоматически классифицировать и организовать ваши ресурсы для разработки.

🔧 Основные команды:
/help - Справка по командам
/search <запрос> - Поиск ресурсов
/list - Список всех ресурсов
/stats - Статистика

🚀 Просто отправьте мне текст, ссылки или описания ресурсов, и я автоматически их классифицирую!

💡 Версия: Railway Minimal"""
        
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """📚 Справка по командам:

🔧 Основные команды:
/start - Запустить бота
/help - Показать эту справку
/search <запрос> - Поиск ресурсов
/list - Список всех ресурсов
/stats - Статистика бота

🤖 Автоматическая классификация:
Просто отправьте мне любой текст, ссылку или описание ресурса, и я автоматически определю категорию и сохраню его.

Примеры:
• "React hooks tutorial"
• "https://github.com/user/repo"
• "CSS Grid complete guide"

💡 Поддерживаемые категории:
• Frontend (React, Vue, Angular)
• Backend (Node.js, Python, PHP)
• Database (SQL, MongoDB)
• Tools (Docker, Git)
• Documentation
• Code examples"""
        
        await update.message.reply_text(help_text)
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        if not context.args:
            await update.message.reply_text(
                "🔍 Использование: /search <запрос>\n"
                "Пример: /search React hooks"
            )
            return
        
        query = ' '.join(context.args)
        results = self.storage.search_resources(query)
        
        if not results:
            await update.message.reply_text(f"🔍 По запросу '{query}' ничего не найдено")
            return
        
        response = f"🔍 Найдено {len(results)} результатов по запросу '{query}':\n\n"
        
        for i, result in enumerate(results[:10], 1):
            response += f"{i}. 📁 {result.get('category', 'Unknown')}\n"
            response += f"   📝 {result['content'][:100]}...\n"
            if result.get('description'):
                response += f"   💬 {result['description'][:50]}...\n"
            response += "\n"
        
        if len(results) > 10:
            response += f"... и еще {len(results) - 10} результатов"
        
        await update.message.reply_text(response)
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command."""
        resources = self.storage.get_all_resources()
        
        if not resources:
            await update.message.reply_text("📋 Пока нет сохраненных ресурсов")
            return
        
        response = f"📋 Всего ресурсов: {len(resources)}\n\n"
        
        # Show last 10 resources
        for i, resource in enumerate(resources[:10], 1):
            response += f"{i}. 📁 {resource.get('category', 'Unknown')}\n"
            response += f"   📝 {resource['content'][:80]}...\n"
            response += f"   🕒 {resource['timestamp'][:10]}\n\n"
        
        if len(resources) > 10:
            response += f"... и еще {len(resources) - 10} ресурсов\n"
            response += "Используйте /search для поиска конкретных ресурсов"
        
        await update.message.reply_text(response)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        stats = self.storage.get_statistics()
        categories = self.storage.get_categories()
        
        response = f"""📊 Статистика DevDataSorter:

📚 Всего ресурсов: {stats['total_resources']}
📂 Категорий: {stats['categories_count']}

📈 Популярные категории:"""
        
        # Show top 5 categories
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        for category, count in sorted_categories[:5]:
            response += f"\n  • {category}: {count}"
        
        if stats.get('popular_category'):
            response += f"\n\n🏆 Самая популярная: {stats['popular_category']}"
        
        response += f"\n\n💡 Версия: Railway Minimal"
        
        await update.message.reply_text(response)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        content = update.message.text
        
        # Show processing message
        status_msg = await update.message.reply_text("🤖 Анализирую контент...")
        
        try:
            # Classify content
            classification = await self.classifier.classify_content(content)
            
            # Extract URLs if present
            urls = self._extract_urls(content)
            
            # Add to storage
            resource_id = self.storage.add_resource(
                content=content,
                category=classification['category'],
                user_id=user_id,
                username=username,
                confidence=classification['confidence'],
                description=classification['description'],
                urls=urls
            )
            
            # Prepare response
            response = f"✅ Ресурс сохранен!\n\n"
            response += f"📁 Категория: {classification['category']}\n"
            response += f"🎯 Уверенность: {classification['confidence']:.1%}\n"
            response += f"📝 Описание: {classification['description']}\n"
            response += f"🆔 ID: {resource_id}"
            
            if urls:
                response += f"\n🔗 Найдено URL: {len(urls)}"
            
            # Delete status message and send result
            await status_msg.delete()
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await status_msg.edit_text("❌ Произошла ошибка при обработке контента")
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        return list(set(urls))
    
    def run(self):
        """Run the bot."""
        logger.info("🚀 Starting DevDataSorter bot...")
        logger.info(f"🤖 AI Provider: {self.ai_config['provider']}")
        
        try:
            self.app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise