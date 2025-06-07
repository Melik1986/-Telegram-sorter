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

logger = logging.getLogger(__name__)

class DevDataSorterBot:
    """Main bot class for DevDataSorter."""
    
    def __init__(self, token: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.ai_config = get_ai_config()
        self.storage = ResourceStorage()
        self.classifier = ContentClassifier()
        self.rate_limiter = RateLimiter()
        self.i18n = I18nManager()
        self.file_handler = FileHandler()
        self.message_sorter = MessageSorter(self.classifier)
        
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
        self.app.add_handler(CommandHandler("export", self.export_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        # Callback query handler
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = (
            "🤖 **DevDataSorter Bot** / Бот для сортировки данных\n\n"
            "📝 **What I can do / Что я умею:**\n"
            "• Classify and store your content / Классифицировать и сохранять контент\n"
            "• Answer questions intelligently / Отвечать на вопросы\n"
            "• Search through saved resources / Искать по сохраненным ресурсам\n"
            "• Export your data / Экспортировать данные\n\n"
            "📋 **Commands / Команды:**\n"
            "• `/help` - Show help / Показать справку\n"
            "• `/list [category]` - List resources / Список ресурсов\n"
            "• `/search <query>` - Search resources / Поиск ресурсов\n"
            "• `/export` - Export data / Экспорт данных\n"
            "• `/stats` - Show statistics / Показать статистику\n\n"
            "💡 **Just send me any content and I'll help organize it!**\n"
            "💡 **Просто отправьте мне любой контент, и я помогу его организовать!**"
        )
        
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "🆘 **Help / Справка**\n\n"
            "**📤 Sending Content / Отправка контента:**\n"
            "• Text messages / Текстовые сообщения\n"
            "• Images with descriptions / Изображения с описаниями\n"
            "• Documents (PDF, DOC, etc.) / Документы\n"
            "• URLs and links / URL и ссылки\n\n"
            "**🔍 Searching / Поиск:**\n"
            "• `/search python tutorial` - Find Python tutorials\n"
            "• `/search категория:код` - Search in specific category\n\n"
            "**📋 Listing / Просмотр:**\n"
            "• `/list` - Show all resources / Показать все ресурсы\n"
            "• `/list code` - Show code resources / Показать код\n\n"
            "**📊 Other / Другое:**\n"
            "• `/stats` - View statistics / Статистика\n"
            "• `/export` - Download your data / Скачать данные\n\n"
            "**🤖 AI Features / ИИ функции:**\n"
            "• Ask questions / Задавайте вопросы\n"
            "• Get explanations / Получайте объяснения\n"
            "• Request help / Просите помощь"
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
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
        
        # Determine if this is a question/request or content to classify
        if await self._is_question_or_request(content):
            await self._handle_intelligent_response(update, context, content)
        else:
            await self._process_content(update, context, content)
    
    async def _is_question_or_request(self, content: str) -> bool:
        """Determine if content is a question or request for AI response."""
        content_lower = content.lower()
        
        # Question indicators
        question_words = [
            'что', 'как', 'где', 'когда', 'почему', 'зачем', 'какой', 'какая', 'какое', 'какие',
            'what', 'how', 'where', 'when', 'why', 'which', 'who', 'whom', 'whose'
        ]
        
        # Request indicators
        request_words = [
            'помоги', 'помощь', 'объясни', 'расскажи', 'покажи', 'найди', 'ищи',
            'help', 'explain', 'tell', 'show', 'find', 'search', 'look'
        ]
        
        # Check for question marks
        if '?' in content:
            return True
        
        # Check for question/request words
        words = content_lower.split()
        if any(word in question_words + request_words for word in words):
            return True
        
        # Check for question patterns
        question_patterns = [
            r'^(что|как|где|когда|почему|зачем)',
            r'^(what|how|where|when|why|which)',
            r'(можешь|можете|could you|can you)',
            r'(помоги|help me|помощь|assistance)'
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, content_lower):
                return True
        
        return False
    
    async def _handle_intelligent_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, content: str):
        """Handle intelligent AI responses to questions and requests."""
        try:
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Determine response type
            response_type = await self._determine_response_type(content)
            
            # Show appropriate indicator based on type
            if response_type == 'search':
                status_msg = await update.message.reply_text("🔍 Searching / Поиск...")
            elif response_type == 'help':
                status_msg = await update.message.reply_text("💡 Thinking / Думаю...")
            elif response_type == 'technical':
                status_msg = await update.message.reply_text("🔧 Analyzing / Анализирую...")
            else:
                status_msg = await update.message.reply_text("🤖 Processing / Обрабатываю...")
            
            # Check if this is a search request
            if await self._is_search_request(content):
                await self._handle_search_from_message(update, context, content)
                await status_msg.delete()
                return
            
            # Generate AI response
            ai_response = await self.classifier.generate_response(content)
            
            if ai_response:
                # Format response based on type
                formatted_response = await self._format_intelligent_response(ai_response, response_type, content)
                
                # Delete status message and send response
                await status_msg.delete()
                await update.message.reply_text(formatted_response, parse_mode=ParseMode.MARKDOWN)
            else:
                # Fallback response
                fallback_response = await self._generate_fallback_response(content, response_type)
                await status_msg.delete()
                await update.message.reply_text(fallback_response, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Error in intelligent response: {e}")
            await update.message.reply_text(
                "❌ Sorry, I couldn't process your request right now.\n"
                "❌ Извините, не могу обработать ваш запрос прямо сейчас."
            )
    
    async def _determine_response_type(self, content: str) -> str:
        """Determine the type of response needed based on content analysis."""
        content_lower = content.lower()
        
        # Search indicators
        if await self._is_search_request(content):
            return 'search'
        
        # Help/guidance indicators
        help_indicators = [
            'помоги', 'помощь', 'как', 'что делать', 'не знаю', 'объясни', 'расскажи',
            'help', 'how to', 'what should', 'explain', 'tell me', 'guide', 'tutorial'
        ]
        if any(indicator in content_lower for indicator in help_indicators):
            return 'help'
        
        # Technical/programming indicators
        tech_indicators = [
            'код', 'программирование', 'алгоритм', 'функция', 'класс', 'библиотека', 'фреймворк',
            'code', 'programming', 'algorithm', 'function', 'class', 'library', 'framework',
            'python', 'javascript', 'java', 'c++', 'react', 'node', 'api', 'database'
        ]
        if any(indicator in content_lower for indicator in tech_indicators):
            return 'technical'
        
        # Default to general
        return 'general'
    
    async def _format_intelligent_response(self, ai_response: str, response_type: str, original_content: str) -> str:
        """Format AI response based on response type and content."""
        # Choose appropriate emoji and title based on type
        type_config = {
            'search': {'emoji': '🔍', 'title': 'Результат поиска / Search Result'},
            'help': {'emoji': '💡', 'title': 'Справка / Help'},
            'technical': {'emoji': '🔧', 'title': 'Техническая информация / Technical Info'},
            'general': {'emoji': '🤖', 'title': 'AI Ответ / AI Response'}
        }
        
        config = type_config.get(response_type, type_config['general'])
        
        # Format the main response
        formatted_response = f"{config['emoji']} **{config['title']}:**\n\n{ai_response}\n\n"
        
        # Add contextual footer based on response type
        if response_type == 'technical':
            formatted_response += "💾 *Хотите сохранить этот код/информацию? Отправьте его отдельным сообщением*\n"
            formatted_response += "💾 *Want to save this code/info? Send it as a separate message*"
        elif response_type == 'help':
            formatted_response += "📚 *Нужна дополнительная помощь? Задайте уточняющий вопрос*\n"
            formatted_response += "📚 *Need more help? Ask a follow-up question*"
        else:
            formatted_response += "💡 *Если вы хотели сохранить этот контент, отправьте его еще раз*\n"
            formatted_response += "💡 *If you wanted to save this content, send it again*"
        
        return formatted_response
    
    async def _generate_fallback_response(self, content: str, response_type: str) -> str:
        """Generate fallback response when AI is unavailable."""
        fallback_responses = {
            'search': (
                "🔍 **Search functionality temporarily unavailable**\n\n"
                "Try using `/search <your query>` command instead.\n\n"
                "🔍 **Поиск временно недоступен**\n\n"
                "Попробуйте команду `/search <ваш запрос>`."
            ),
            'help': (
                "💡 **Help system temporarily unavailable**\n\n"
                "Please check `/help` command for basic information.\n\n"
                "💡 **Система помощи временно недоступна**\n\n"
                "Используйте команду `/help` для базовой информации."
            ),
            'technical': (
                "🔧 **Technical analysis temporarily unavailable**\n\n"
                "You can still save your content by sending it again.\n\n"
                "🔧 **Технический анализ временно недоступен**\n\n"
                "Вы можете сохранить контент, отправив его еще раз."
            ),
            'general': (
                "🤖 **AI response temporarily unavailable**\n\n"
                "I can still help you organize and save content!\n\n"
                "🤖 **ИИ ответ временно недоступен**\n\n"
                "Я все еще могу помочь организовать и сохранить контент!"
            )
        }
        
        return fallback_responses.get(response_type, fallback_responses['general'])
    
    async def _process_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE, content: str):
        """Process and classify content for storage."""
        try:
            # Preprocess content
            processed_content = await self._preprocess_content(content)
            
            # Extract URLs
            urls = self._extract_urls(processed_content)
            
            # Classify content with enhanced logic
            classification = await self.classifier.classify_content(processed_content)
            
            if not classification:
                # Enhanced fallback classification
                classification = await self._enhanced_fallback_classification(processed_content)
            
            if classification:
                # Prepare additional data
                additional_data = {
                    'urls': urls,
                    'timestamp': datetime.now().isoformat(),
                    'user_id': update.effective_user.id,
                    'message_id': update.message.message_id
                }
                
                # Add resource to storage
                resource_id = self.storage.add_resource(
                    content=processed_content,
                    category=classification['category'],
                    user_id=update.effective_user.id,
                    username=update.effective_user.username,
                    description=classification['description'],
                    urls=urls
                )
                
                # Format success message
                success_message = (
                    f"✅ **Content classified and saved!**\n\n"
                    f"📂 **Category:** {classification['category']}\n"
                    f"📝 **Description:** {classification['description']}\n"
                    f"🆔 **ID:** {resource_id}\n"
                )
                
                if urls:
                    success_message += f"🔗 **URLs found:** {len(urls)}\n"
                
                success_message += (
                    f"\n✅ **Контент классифицирован и сохранен!**\n"
                    f"📂 **Категория:** {classification['category']}\n"
                    f"📝 **Описание:** {classification['description']}"
                )
                
                await update.message.reply_text(success_message, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    "❌ Unable to classify content. Please try rephrasing or adding more context.\n"
                    "❌ Не удалось классифицировать контент. Попробуйте переформулировать или добавить больше контекста."
                )
                
        except Exception as e:
            logger.error(f"Error processing content: {e}")
            await update.message.reply_text(
                "❌ Error processing content. Please try again.\n"
                "❌ Ошибка обработки контента. Попробуйте еще раз."
            )
    
    async def _preprocess_content(self, content: str) -> str:
        """Preprocess content before classification."""
        # Remove extra whitespace
        content = ' '.join(content.split())
        
        # Add URL context if URLs are present
        urls = self._extract_urls(content)
        if urls:
            url_context = f"\n\nURLs: {', '.join(urls)}"
            content += url_context
        
        # Detect and add technical content context
        if self._is_technical_content(content):
            content = f"[TECHNICAL CONTENT] {content}"
        
        return content
    
    def _is_technical_content(self, content: str) -> bool:
        """Detect if content is technical/programming related."""
        technical_indicators = [
            'function', 'class', 'import', 'export', 'const', 'let', 'var',
            'def', 'return', 'if', 'else', 'for', 'while', 'try', 'catch',
            'async', 'await', 'promise', 'callback', 'api', 'endpoint',
            'database', 'sql', 'query', 'select', 'insert', 'update',
            'git', 'commit', 'push', 'pull', 'merge', 'branch',
            'docker', 'kubernetes', 'deployment', 'server', 'client'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in technical_indicators)
    
    async def _enhanced_fallback_classification(self, content: str) -> Optional[Dict[str, Any]]:
        """Enhanced fallback classification with AI assistance."""
        try:
            # Try AI-assisted classification
            ai_classification = await self.classifier.classify_with_ai(content)
            if ai_classification:
                return ai_classification
        except Exception as e:
            logger.warning(f"AI classification failed: {e}")
        
        # Fallback to pattern-based classification
        return self._pattern_based_classification(content)
    
    def _pattern_based_classification(self, content: str) -> Optional[Dict[str, Any]]:
        """Pattern-based classification as final fallback."""
        content_lower = content.lower()
        
        # Define patterns for different categories
        patterns = {
            'code': ['function', 'class', 'import', 'def', 'return', 'var', 'const', 'let'],
            'documentation': ['readme', 'docs', 'documentation', 'guide', 'tutorial', 'how to'],
            'link': ['http', 'https', 'www.', '.com', '.org', '.net'],
            'note': ['note', 'remember', 'important', 'todo', 'task'],
            'question': ['?', 'how', 'what', 'why', 'when', 'where']
        }
        
        # Score each category
        scores = {}
        for category, keywords in patterns.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                scores[category] = score
        
        if scores:
            # Get category with highest score
            best_category = max(scores, key=scores.get)
            return {
                'category': best_category,
                'description': f"Auto-classified as {best_category} based on content patterns",
                'confidence': min(scores[best_category] / len(patterns[best_category]), 1.0)
            }
        
        return None
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, text)
    
    async def _is_search_request(self, content: str) -> bool:
        """Determine if content is a search request."""
        content_lower = content.lower()
        
        # Extended search keywords
        search_keywords = [
            'найди', 'найти', 'поиск', 'ищи', 'искать', 'покажи', 'показать',
            'find', 'search', 'look', 'show', 'get', 'retrieve', 'fetch',
            'где', 'where', 'есть ли', 'is there', 'do you have'
        ]
        
        # Question patterns that indicate search
        search_patterns = [
            r'(найди|find|search)\s+',
            r'(где|where)\s+.*\?',
            r'(есть ли|is there|do you have)\s+',
            r'(покажи|show me)\s+'
        ]
        
        # Check for search keywords
        words = content_lower.split()
        if any(keyword in words for keyword in search_keywords):
            return True
        
        # Check for search patterns
        for pattern in search_patterns:
            if re.search(pattern, content_lower):
                return True
        
        return False
    
    async def _handle_search_from_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, content: str):
        """Handle search request from a message."""
        # Extract search terms
        search_terms = self._extract_search_terms(content)
        
        if search_terms:
            # Perform search
            results = self.storage.search_resources(' '.join(search_terms))
            
            if results:
                response = f"🔍 **Search Results for '{' '.join(search_terms)}':**\n\n"
                
                for i, result in enumerate(results[:5], 1):
                    response += (
                        f"{i}. **{result['category']}** - {result['description'][:100]}...\n"
                        f"   🆔 ID: {result['id']}\n\n"
                    )
                
                if len(results) > 5:
                    response += f"... and {len(results) - 5} more results\n\n"
                
                response += "🔍 **Результаты поиска:**\n"
                response += f"Найдено {len(results)} результатов"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    f"❌ No results found for '{' '.join(search_terms)}'.\n"
                    f"❌ Ничего не найдено по запросу '{' '.join(search_terms)}'."
                )
        else:
            await update.message.reply_text(
                "❌ Couldn't understand what to search for. Please clarify.\n"
                "❌ Не понял, что искать. Уточните запрос."
            )
    
    def _extract_search_terms(self, content: str) -> List[str]:
        """Extract search terms from content."""
        # Remove common search words
        stop_words = {
            'найди', 'найти', 'поиск', 'ищи', 'искать', 'покажи', 'показать',
            'find', 'search', 'look', 'show', 'get', 'retrieve', 'fetch',
            'где', 'where', 'есть', 'ли', 'is', 'there', 'do', 'you', 'have',
            'мне', 'me', 'для', 'for', 'по', 'about', 'про', 'о'
        }
        
        words = content.lower().split()
        search_terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        return search_terms
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command."""
        try:
            # Get category filter if provided
            category_filter = None
            if context.args:
                category_filter = ' '.join(context.args).lower()
            
            # Get resources
            if category_filter:
                resources = self.storage.get_resources_by_category(category_filter)
            else:
                resources = self.storage.get_all_resources()
            
            if resources:
                if category_filter:
                    response = f"📂 **Resources in category '{category_filter}':**\n\n"
                else:
                    response = "📂 **All saved resources:**\n\n"
                
                for i, resource in enumerate(resources[:10], 1):
                    response += (
                        f"{i}. **{resource['category']}** - {resource['description'][:80]}...\n"
                        f"   🆔 ID: {resource['id']} | 📅 {resource['created_at'][:10]}\n\n"
                    )
                
                if len(resources) > 10:
                    response += f"... and {len(resources) - 10} more resources\n\n"
                
                response += f"📊 Total: {len(resources)} resources"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                if category_filter:
                    await update.message.reply_text(
                        f"📂 No resources in category '{category_filter}'.\n"
                        f"📂 Нет ресурсов в категории '{category_filter}'."
                    )
                else:
                    await update.message.reply_text(
                        "📂 No saved resources yet.\n"
                        "📂 Пока нет сохраненных ресурсов."
                    )
                    
        except Exception as e:
            logger.error(f"Error in list command: {e}")
            await update.message.reply_text(
                "❌ Error retrieving resources.\n"
                "❌ Ошибка получения ресурсов."
            )
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        if not context.args:
            await update.message.reply_text(
                "🔍 **Usage:** `/search <query>`\n"
                "🔍 **Использование:** `/search <запрос>`\n\n"
                "**Examples / Примеры:**\n"
                "• `/search python tutorial`\n"
                "• `/search категория:код`"
            )
            return
        
        query = ' '.join(context.args)
        
        try:
            results = self.storage.search_resources(query)
            
            if results:
                response = f"🔍 **Search Results for '{query}':**\n\n"
                
                for i, result in enumerate(results[:10], 1):
                    response += (
                        f"{i}. **{result['category']}** - {result['description'][:100]}...\n"
                        f"   🆔 ID: {result['id']} | 📅 {result['created_at'][:10]}\n\n"
                    )
                
                if len(results) > 10:
                    response += f"... and {len(results) - 10} more results\n\n"
                
                response += f"📊 Found {len(results)} results"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    f"❌ No results found for '{query}'.\n"
                    f"❌ Ничего не найдено по запросу '{query}'."
                )
                
        except Exception as e:
            logger.error(f"Error in search command: {e}")
            await update.message.reply_text(
                "❌ Search error. Please try again.\n"
                "❌ Ошибка поиска. Попробуйте еще раз."
            )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        try:
            stats = self.storage.get_statistics()
            
            response = (
                "📊 **Statistics / Статистика:**\n\n"
                f"📂 **Total resources / Всего ресурсов:** {stats.get('total_resources', 0)}\n"
                f"🏷️ **Categories / Категорий:** {stats.get('total_categories', 0)}\n"
                f"📅 **This week / За неделю:** {stats.get('resources_this_week', 0)}\n"
                f"📈 **This month / За месяц:** {stats.get('resources_this_month', 0)}\n\n"
            )
            
            # Top categories
            if 'top_categories' in stats:
                response += "🔝 **Top categories / Топ категории:**\n"
                for category, count in stats['top_categories'][:5]:
                    response += f"• {category}: {count}\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text(
                "❌ Error retrieving statistics.\n"
                "❌ Ошибка получения статистики."
            )
    
    async def export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export command."""
        try:
            # Get all resources
            all_resources = self.storage.get_all_resources()
            
            if not all_resources:
                await update.message.reply_text(
                    "📂 No data to export.\n"
                    "📂 Нет данных для экспорта."
                )
                return
            
            # Create export data
            export_data = {
                'export_date': datetime.now().isoformat(),
                'total_resources': len(all_resources),
                'resources': all_resources
            }
            
            # Convert to JSON
            import json
            json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            # Create file
            filename = f"devdatasorter_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Send as document
            from io import BytesIO
            file_buffer = BytesIO(json_data.encode('utf-8'))
            file_buffer.name = filename
            
            # Get categories for summary
            categories = set(resource['category'] for resource in all_resources)
            
            await update.message.reply_document(
                document=file_buffer,
                caption=f"📤 Data export / Экспорт данных\n📊 Resources: {len(all_resources)}\n📂 Categories: {len(categories)}"
            )
            
        except Exception as e:
            logger.error(f"Error in export command: {e}")
            await update.message.reply_text(
                "❌ Export error. Please try again.\n"
                "❌ Ошибка экспорта. Попробуйте еще раз."
            )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages."""
        try:
            # Get photo and caption
            photo = update.message.photo[-1]  # Get highest resolution
            caption = update.message.caption or "Image without description"
            
            # Download photo
            file = await context.bot.get_file(photo.file_id)
            file_path = f"temp_image_{photo.file_id}.jpg"
            await file.download_to_drive(file_path)
            
            try:
                # Process image with file handler
                image_analysis = await self.file_handler.process_image(file_path, caption)
                
                # Combine caption and analysis
                content = f"{caption}\n\nImage analysis: {image_analysis}"
                
                # Process as regular content
                await self._process_content(update, context, content)
                
            finally:
                # Clean up
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await update.message.reply_text(
                "❌ Failed to process image / Не удалось обработать изображение"
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document messages."""
        try:
            document = update.message.document
            caption = update.message.caption or "Document without description"
            
            # Check file size (limit to 20MB)
            if document.file_size > 20 * 1024 * 1024:
                await update.message.reply_text(
                    "❌ File too large (max 20MB) / Файл слишком большой (макс 20МБ)"
                )
                return
            
            # Download document
            file = await context.bot.get_file(document.file_id)
            file_path = f"temp_doc_{document.file_id}_{document.file_name}"
            await file.download_to_drive(file_path)
            
            try:
                # Process document with file handler
                doc_analysis = await self.file_handler.process_document(file_path, caption)
                
                # Combine caption and analysis
                content = f"{caption}\n\nDocument: {document.file_name}\nSize: {document.file_size} bytes\nAnalysis: {doc_analysis}"
                
                # Process as regular content
                await self._process_content(update, context, content)
                
            finally:
                # Clean up
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text(
                "❌ Failed to process document / Не удалось обработать документ"
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        # Handle different callback types
        if query.data.startswith('view_'):
            resource_id = query.data.split('_')[1]
            await self._show_resource_details(query, resource_id)
        elif query.data.startswith('delete_'):
            resource_id = query.data.split('_')[1]
            await self._delete_resource(query, resource_id)
    
    async def _show_resource_details(self, query, resource_id: str):
        """Show detailed information about a resource."""
        try:
            resource = self.storage.get_resource(resource_id)
            if resource:
                response = (
                    f"📄 **Resource Details:**\n\n"
                    f"🆔 **ID:** {resource['id']}\n"
                    f"📂 **Category:** {resource['category']}\n"
                    f"📝 **Description:** {resource['description']}\n"
                    f"📅 **Created:** {resource['created_at']}\n\n"
                    f"📄 **Content:**\n{resource['content'][:500]}..."
                )
                
                await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await query.edit_message_text("❌ Resource not found")
                
        except Exception as e:
            logger.error(f"Error showing resource details: {e}")
            await query.edit_message_text("❌ Error retrieving resource")
    
    async def _delete_resource(self, query, resource_id: str):
        """Delete a resource."""
        try:
            success = self.storage.delete_resource(resource_id)
            if success:
                await query.edit_message_text("✅ Resource deleted successfully")
            else:
                await query.edit_message_text("❌ Failed to delete resource")
                
        except Exception as e:
            logger.error(f"Error deleting resource: {e}")
            await query.edit_message_text("❌ Error deleting resource")
    
    def run(self):
        """Start the bot."""
        logger.info("Starting DevDataSorter bot...")
        try:
            # Create event loop if it doesn't exist
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        self.app.run_polling(drop_pending_updates=True)
        logger.info("Bot stopped")