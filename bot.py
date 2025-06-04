"""
Telegram bot implementation with AI-powered content classification.
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from classifier import ContentClassifier
from storage import ResourceStorage
from utils import extract_urls, format_resource_list

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, bot_token, openai_api_key):
        """Initialize the Telegram bot with AI classifier and storage."""
        self.bot_token = bot_token
        self.classifier = ContentClassifier(openai_api_key)
        self.storage = ResourceStorage()
        self.app = Application.builder().token(bot_token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up command and message handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("add", self.add_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("categories", self.categories_command))
        self.app.add_handler(CommandHandler("list", self.list_command))
        
        # Message handler for content classification
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = """
🤖 Добро пожаловать в AI Classification Bot! / Welcome to AI Classification Bot!

Этот бот поможет вам сортировать ресурсы для разработчиков с помощью ИИ.
This bot helps you sort developer resources using AI.

📝 Доступные команды / Available commands:
• /help - Показать справку / Show help
• /add <content> - Добавить ресурс / Add resource
• /search <query> - Поиск ресурсов / Search resources
• /categories - Показать категории / Show categories
• /list [category] - Список ресурсов / List resources

Просто отправьте мне текст, ссылку или описание ресурса, и я автоматически классифицирую его!
Just send me text, links, or resource descriptions, and I'll automatically classify them!
        """
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
📚 Справка по командам / Command Help:

🔹 /add <content> - Добавить ресурс для классификации
   Пример: /add https://github.com/example/repo

🔹 /search <query> - Поиск по ресурсам
   Пример: /search Python tutorial

🔹 /categories - Показать все доступные категории

🔹 /list [category] - Показать ресурсы по категории
   Пример: /list code_examples

📤 Автоматическая классификация:
Отправьте любой текст или ссылку, и бот автоматически определит тип контента:
• Примеры кода / Code examples
• Туториалы / Tutorials  
• Видео / Videos
• Макеты / Mockups
• Документация / Documentation
• Инструменты / Tools

🌐 Поддерживаются русский и английский языки.
        """
        await update.message.reply_text(help_text)
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command to manually add resources."""
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
        """Handle /search command to search resources."""
        if not context.args:
            await update.message.reply_text(
                "Пожалуйста, укажите поисковый запрос.\n"
                "Please specify search query.\n"
                "Пример/Example: /search Python"
            )
            return
        
        query = " ".join(context.args).lower()
        results = self.storage.search_resources(query)
        
        if not results:
            await update.message.reply_text(
                f"❌ Ресурсы по запросу '{query}' не найдены.\n"
                f"No resources found for query '{query}'."
            )
            return
        
        response = f"🔍 Результаты поиска для '{query}' / Search results for '{query}':\n\n"
        response += format_resource_list(results)
        
        await update.message.reply_text(response)
    
    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /categories command to show available categories."""
        categories = self.storage.get_categories_summary()
        
        if not categories:
            await update.message.reply_text(
                "📂 Пока нет сохраненных ресурсов.\n"
                "No saved resources yet."
            )
            return
        
        response = "📂 Доступные категории / Available categories:\n\n"
        for category, count in categories.items():
            category_emoji = self._get_category_emoji(category)
            response += f"{category_emoji} {category}: {count} ресурсов/resources\n"
        
        await update.message.reply_text(response)
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command to show resources by category."""
        category = context.args[0] if context.args else None
        
        if category:
            resources = self.storage.get_resources_by_category(category)
            if not resources:
                await update.message.reply_text(
                    f"❌ Ресурсы в категории '{category}' не найдены.\n"
                    f"No resources found in category '{category}'."
                )
                return
            
            response = f"📋 Ресурсы в категории '{category}' / Resources in category '{category}':\n\n"
            response += format_resource_list(resources)
        else:
            all_resources = self.storage.get_all_resources()
            if not all_resources:
                await update.message.reply_text(
                    "📂 Пока нет сохраненных ресурсов.\n"
                    "No saved resources yet."
                )
                return
            
            response = "📋 Все ресурсы / All resources:\n\n"
            response += format_resource_list(all_resources)
        
        await update.message.reply_text(response)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages for automatic classification."""
        content = update.message.text
        await self._process_content(update, content, manual=False)
    
    async def _process_content(self, update: Update, content: str, manual: bool = False):
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
            
            # Store the resource
            resource_id = self.storage.add_resource(
                content=content,
                category=classification['category'],
                subcategory=classification.get('subcategory'),
                confidence=classification.get('confidence', 0.0),
                description=classification.get('description', ''),
                urls=urls
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
    
    def run(self):
        """Start the bot."""
        logger.info("Bot is starting...")
        self.app.run_polling()
