"""
Минимальная версия Telegram бота с основным функционалом.
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from .classifier_minimal import ContentClassifier
from .config_minimal import get_telegram_token
from ..utils.storage_minimal import ResourceStorage

logger = logging.getLogger(__name__)

class DevDataSorterBot:
    """Минимальная версия бота."""
    
    def __init__(self, token: str = None):
        self.token = token or get_telegram_token()
        self.storage = ResourceStorage()
        self.classifier = ContentClassifier()
        
        # Инициализация Telegram приложения
        self.app = Application.builder().token(self.token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков."""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("list", self.list_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # Обработчик текстовых сообщений
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start."""
        welcome_text = """
🤖 Добро пожаловать в DevDataSorter!

Я помогу вам организовать и найти ваши ресурсы для разработки.

Основные команды:
/help - справка
/search <запрос> - поиск ресурсов
/list - список всех ресурсов
/stats - статистика

Просто отправьте мне текст, ссылку или описание ресурса, и я автоматически его классифицирую!
        """
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help."""
        help_text = """
📚 Справка по командам:

🔧 Основные команды:
/start - начать работу
/help - эта справка
/search <запрос> - поиск ресурсов
/list - показать все ресурсы
/stats - статистика

🤖 Автоматическая классификация:
Просто отправьте мне любой текст, и я определю его категорию:
• Frontend (HTML, CSS, JS, React, Vue)
• Backend (API, Node.js, Python, PHP)
• Database (SQL, MongoDB)
• Tools (Docker, Git, npm)
• Documentation (туториалы, гайды)
• Code (примеры кода)

Примеры:
"React hooks tutorial"
"Python Flask API example"
"MongoDB query optimization"
        """
        await update.message.reply_text(help_text)
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /search."""
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
        
        response = f"🔍 Найдено {len(results)} результатов для '{query}':\n\n"
        
        for i, result in enumerate(results[:10], 1):
            response += f"{i}. 📁 {result['category']}\n"
            response += f"   📝 {result['content'][:100]}...\n"
            if result.get('description'):
                response += f"   💬 {result['description'][:50]}...\n"
            response += f"   🆔 {result['id']}\n\n"
        
        if len(results) > 10:
            response += f"... и еще {len(results) - 10} результатов"
        
        await update.message.reply_text(response)
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /list."""
        resources = self.storage.get_all_resources()
        
        if not resources:
            await update.message.reply_text("📋 У вас пока нет сохраненных ресурсов")
            return
        
        response = f"📋 Всего ресурсов: {len(resources)}\n\n"
        
        for i, resource in enumerate(resources[:10], 1):
            response += f"{i}. 📁 {resource['category']}\n"
            response += f"   📝 {resource['content'][:80]}...\n"
            response += f"   🆔 {resource['id']}\n\n"
        
        if len(resources) > 10:
            response += f"... и еще {len(resources) - 10} ресурсов"
        
        await update.message.reply_text(response)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats."""
        stats = self.storage.get_statistics()
        categories = self.storage.get_categories()
        
        response = f"""📊 Статистика:

📚 Всего ресурсов: {stats['total_resources']}
📂 Категорий: {stats['categories_count']}
⭐ Популярная категория: {stats.get('popular_category', 'Нет')}

📋 По категориям:
"""
        
        for category, count in categories.items():
            response += f"• {category}: {count}\n"
        
        await update.message.reply_text(response)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений."""
        user_id = update.effective_user.id
        username = update.effective_user.username
        content = update.message.text
        
        try:
            # Классификация контента
            classification = await self.classifier.classify_content(content)
            
            # Сохранение ресурса
            resource_id = self.storage.add_resource(
                content=content,
                category=classification['category'],
                user_id=user_id,
                username=username,
                confidence=classification['confidence'],
                description=classification['description']
            )
            
            # Ответ пользователю
            response = f"""✅ Ресурс сохранен!

📁 Категория: {classification['category']}
📝 Описание: {classification['description']}
🎯 Уверенность: {classification['confidence']:.0%}
🆔 ID: {resource_id}

Используйте /search для поиска или /list для просмотра всех ресурсов."""
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке сообщения. Попробуйте еще раз."
            )
    
    def run(self):
        """Запуск бота."""
        logger.info("Запуск DevDataSorter бота...")
        self.app.run_polling()