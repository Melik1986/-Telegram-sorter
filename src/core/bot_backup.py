import asyncio
import logging
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
    """Enhanced bot class for DevDataSorter with improved Russian language support."""
    
    def __init__(self, token: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.ai_config = get_ai_config()
        self.storage = ResourceStorage()
        self.classifier = ContentClassifier()
        self.rate_limiter = RateLimiter()
        self.i18n = I18nManager()
        self.file_handler = FileHandler()
        self.message_sorter = MessageSorter(self.classifier)
        self.command_interpreter = NaturalLanguageCommandInterpreter(self.classifier)
        
        # Enhanced Russian language patterns
        self._init_enhanced_language_patterns()
        
        # Initialize Telegram application
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self._setup_handlers()
    
    def _init_enhanced_language_patterns(self):
        """Initialize enhanced patterns for better Russian language understanding."""
        # Расширенные паттерны для русского языка
        self.russian_question_patterns = [
            r'\b(что|как|где|когда|почему|зачем|какой|какая|какое|какие|кто|кому|чей|чья|чьё|чьи)\b',
            r'\b(можешь|можете|умеешь|умеете|знаешь|знаете)\b',
            r'\b(помоги|помогите|объясни|объясните|расскажи|расскажите|покажи|покажите)\b',
            r'\b(найди|найдите|ищи|ищите|поищи|поищите)\b'
        ]
        
        self.russian_command_synonyms = {
            'поиск': ['найди', 'найти', 'ищи', 'искать', 'поищи', 'поискать', 'покажи', 'показать'],
            'создать': ['создай', 'сделай', 'сделать', 'построй', 'построить', 'организуй', 'организовать'],
            'папка': ['директория', 'каталог', 'folder', 'dir', 'directory'],
            'архив': ['архивчик', 'backup', 'бэкап', 'резерв', 'резервная копия'],
            'список': ['покажи', 'показать', 'вывести', 'отобразить', 'list', 'листинг'],
            'помощь': ['справка', 'help', 'хелп', 'инфо', 'информация', 'подсказка'],
            'статистика': ['стата', 'stats', 'статы', 'данные', 'информация'],
            'экспорт': ['выгрузить', 'скачать', 'сохранить', 'export', 'download'],
            'анализ': ['проанализировать', 'разобрать', 'изучить', 'analyze', 'analysis'],
            'удалить': ['убрать', 'стереть', 'delete', 'remove', 'del']
        }
        
        self.context_enhancers = {
            'код': ['программирование', 'разработка', 'coding', 'programming', 'development'],
            'дизайн': ['ui', 'ux', 'интерфейс', 'макет', 'layout', 'design'],
            'документация': ['docs', 'readme', 'мануал', 'руководство', 'инструкция'],
            'ссылка': ['url', 'link', 'линк', 'адрес', 'сайт', 'website']
        }
    
    def _setup_handlers(self):
        """Setup all bot handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("list", self.list_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("export", self.export_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # New enhanced commands
        self.app.add_handler(CommandHandler("create_folder", self.create_folder_command))
        self.app.add_handler(CommandHandler("create_archive", self.create_archive_command))
        self.app.add_handler(CommandHandler("find_folder", self.find_folder_command))
        self.app.add_handler(CommandHandler("smart_search", self.smart_search_command))
        self.app.add_handler(CommandHandler("analyze", self.analyze_command))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        # Callback query handler
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with enhanced multilingual support."""
        welcome_text = (
            "🤖 **DevDataSorter Bot** / Бот для сортировки данных\n\n"
            "📝 **What I can do / Что я умею:**\n"
            "• Classify and store your content / Классифицировать и сохранять контент\n"
            "• Answer questions intelligently / Отвечать на вопросы\n"
            "• Search through saved resources / Искать по сохраненным ресурсам\n"
            "• Export your data / Экспортировать данные\n"
            "• Understand natural language commands / Понимать команды на естественном языке\n\n"
            "📋 **Commands / Команды:**\n"
            "• `/help` - Show help / Показать справку\n"
            "• `/list [category]` - List resources / Список ресурсов\n"
            "• `/search <query>` - Search resources / Поиск ресурсов\n"
            "• `/export` - Export data / Экспорт данных\n"
            "• `/stats` - Show statistics / Показать статистику\n\n"
            "💡 **Natural Language Examples / Примеры на естественном языке:**\n"
            "• \"Найди все про Python\" / \"Find everything about Python\"\n"
            "• \"Создай папку для проектов\" / \"Create a folder for projects\"\n"
            "• \"Покажи статистику\" / \"Show statistics\"\n\n"
            "💡 **Just send me any content and I'll help organize it!**\n"
            "💡 **Просто отправьте мне любой контент, и я помогу его организовать!**"
        )
        
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command with enhanced examples."""
        help_text = (
            "🆘 **Help / Справка**\n\n"
            "**📤 Sending Content / Отправка контента:**\n"
            "• Text messages / Текстовые сообщения\n"
            "• Images with descriptions / Изображения с описаниями\n"
            "• Documents (PDF, DOC, etc.) / Документы\n"
            "• URLs and links / URL и ссылки\n\n"
            "**🔍 Natural Language Search / Поиск на естественном языке:**\n"
            "• \"Найди код на Python\" - Find Python code\n"
            "• \"Покажи все ссылки\" - Show all links\n"
            "• \"Где документация по React?\" - Where is React documentation?\n\n"
            "**📁 Folder Management / Управление папками:**\n"
            "• \"Создай папку веб-разработка\" - Create web development folder\n"
            "• \"Сделай архив проектов\" - Create projects archive\n\n"
            "**📊 Information / Информация:**\n"
            "• \"Покажи статистику\" - Show statistics\n"
            "• \"Экспортируй данные\" - Export data\n"
            "• \"Проанализируй контент\" - Analyze content\n\n"
            "**🔍 Traditional Search / Традиционный поиск:**\n"
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
        """Enhanced message handler with improved Russian language understanding."""
        user_id = update.effective_user.id
        content = update.message.text
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(user_id):
            await update.message.reply_text(
                "⏰ Too many requests. Please wait a moment.\n"
                "⏰ Слишком много запросов. Подождите немного."
            )
            return
        
        # Enhanced natural language command interpretation
        command_intent = await self._enhanced_command_interpretation(content)
        
        if command_intent.command_type != CommandType.UNKNOWN and command_intent.confidence > 0.5:
            await self._handle_command_intent(update, context, command_intent)
            return
        
        # Enhanced question/request detection
        if await self._is_enhanced_question_or_request(content):
            await self._handle_intelligent_response(update, context, content)
        else:
            await self._process_content(update, context, content)
    
    async def _enhanced_command_interpretation(self, content: str):
        """Enhanced command interpretation with better Russian support."""
        # First try the existing command interpreter
        command_intent = await self.command_interpreter.interpret_command(content)
        
        # If confidence is low, try enhanced interpretation
        if command_intent.confidence < 0.7:
            enhanced_intent = await self._try_enhanced_interpretation(content)
            if enhanced_intent and enhanced_intent.confidence > command_intent.confidence:
                return enhanced_intent
        
        return command_intent
    
    async def _try_enhanced_interpretation(self, content: str):
        """Try enhanced interpretation using expanded patterns and AI."""
        content_lower = content.lower()
        
        # Enhanced pattern matching with synonyms
        for command, synonyms in self.russian_command_synonyms.items():
            for synonym in synonyms:
                if synonym in content_lower:
                    # Extract parameters based on command type
                    parameters = await self._extract_enhanced_parameters(content, command, synonym)
                    
                    # Determine command type
                    command_type = self._map_to_command_type(command)
                    
                    if command_type != CommandType.UNKNOWN:
                        from ..handlers.command_interpreter import CommandIntent
                        return CommandIntent(
                            command_type=command_type,
                            parameters=parameters,
                            confidence=0.8,
                            language='ru' if any(ord(c) > 127 for c in content) else 'en'
                        )
        
        # Try AI-enhanced interpretation if available
        if self.classifier.groq_client:
            return await self._ai_enhanced_interpretation(content)
        
        return None
    
    def _map_to_command_type(self, command: str) -> CommandType:
        """Map Russian command to CommandType enum."""
        mapping = {
            'поиск': CommandType.SEARCH,
            'создать': CommandType.CREATE_FOLDER,
            'папка': CommandType.CREATE_FOLDER,
            'архив': CommandType.CREATE_ARCHIVE,
            'список': CommandType.LIST,
            'помощь': CommandType.HELP,
            'статистика': CommandType.STATS,
            'экспорт': CommandType.EXPORT,
            'анализ': CommandType.ANALYZE,
            'удалить': CommandType.DELETE
        }
        return mapping.get(command, CommandType.UNKNOWN)
    
    async def _extract_enhanced_parameters(self, content: str, command: str, synonym: str) -> Dict[str, Any]:
        """Extract parameters from content using enhanced patterns with improved Russian support."""
        parameters = {}
        content_lower = content.lower()
        
        if command in ['поиск']:
            # Enhanced search query extraction
            # First try to find query after the synonym
            query_start = content_lower.find(synonym.lower())
            if query_start != -1:
                query_start += len(synonym)
                query = content[query_start:].strip()
            else:
                # Fallback to pattern matching
                search_patterns = [
                    r'(?:найди|найти|поищи|поискать|отыщи)\s+(.+)',
                    r'(?:покажи|показать|отобрази)\s+(?:мне\s+)?(.+)',
                    r'где\s+(?:находится\s+|есть\s+)?(.+)',
                    r'ищи\s+(.+)',
                    r'хочу\s+(?:найти|посмотреть)\s+(.+)',
                    r'что\s+(?:у\s+(?:тебя|меня)\s+)?(?:есть\s+)?(?:по\s+|про\s+|о\s+)?(.+?)\??$',
                    r'какие\s+(?:у\s+(?:тебя|меня)\s+)?(?:есть\s+)?(.+?)\??$'
                ]
                
                query = None
                for pattern in search_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        query = match.group(1).strip()
                        break
            
            if query:
                # Clean up the query
                query = re.sub(r'^(все|всё|про|о|об|about|for|on|мне|для\s+меня)\s+', '', query, flags=re.IGNORECASE)
                query = re.sub(r'[?!.,;]+$', '', query).strip()
                
                if query and len(query) > 1:
                    parameters['query'] = query
        
        elif command in ['создать', 'папка', 'архив']:
            # Enhanced name extraction for folders/archives
            name_patterns = [
                # Для папок
                r'(?:создай|сделай|новая)\s+(?:папку|директорию|каталог)\s+(?:с\s+названием\s+)?["\']?([^"\'\.]+)["\']?',
                r'(?:папку|директорию)\s+["\']?([^"\'\.]+)["\']?',
                # Для архивов
                r'(?:создай|сделай)\s+(?:архив|бэкап)\s+(?:с\s+названием\s+)?["\']?([^"\'\.]+)["\']?',
                r'(?:архив|бэкап)\s+["\']?([^"\'\.]+)["\']?',
                # Общие паттерны
                r'(?:создай|сделай|построй)\s+(?:папку|архив|folder|archive)?\s*["\']?([^"\'\.]+)["\']?',
                r'["\']([^"\'\.]+)["\']',
                # Паттерн для случаев типа "папка проекты"
                r'(?:папка|архив|folder|archive)\s+([а-яёa-z0-9\s_-]+?)(?:\s|$)',
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    # Очищаем от лишних слов
                    name = re.sub(r'\b(с|названием|called|named)\b', '', name, flags=re.IGNORECASE).strip()
                    if name and len(name) > 1 and name.lower() not in ['папку', 'архив', 'folder', 'archive']:
                        parameters['name'] = name
                        break
        
        elif command == 'список':
            # Enhanced category extraction
            category_patterns = [
                r'(?:покажи|показать|список|отобрази)\s+(?:все|всё|мне)?\s*([а-яё\w]+)(?:\s+(?:файлы|документы|ссылки|данные))?',
                r'(?:в|из)\s+категории\s+([а-яё\w]+)',
                r'категория\s+([а-яё\w]+)',
                r'что\s+(?:есть\s+)?(?:в|по)\s+([а-яё\w]+)',
                r'([а-яё\w]+)\s+(?:файлы|документы|ссылки|данные)',
                # Вопросительные формы
                r'какие\s+(?:у\s+(?:тебя|меня)\s+)?(?:есть\s+)?([а-яё\w]+)',
                r'что\s+(?:у\s+(?:тебя|меня)\s+)?(?:есть\s+)?(?:по\s+)?([а-яё\w]+)'
            ]
            
            for pattern in category_patterns:
                match = re.search(pattern, content_lower)
                if match:
                    category = match.group(1).strip()
                    if category not in ['все', 'всё', 'all', 'мне', 'me', 'есть', 'have']:
                        parameters['category'] = category
                        break
        
        elif command == 'удалить':
            # Enhanced target extraction for deletion
            target_patterns = [
                r'(?:удали|убери|стереть|очисти|снеси)\s+(?:папку\s+|файл\s+|архив\s+)?["\']?([^"\'\.]+)["\']?',
                r'(?:delete|remove|clear|erase)\s+(?:folder\s+|file\s+|archive\s+)?["\']?([^"\'\.]+)["\']?',
                # ID или индекс
                r'(?:удали|убери|delete|remove)\s+(?:номер\s+|#)?(\d+)',
                # По категории
                r'(?:удали|убери)\s+(?:все\s+)?(?:из\s+)?(?:категории\s+)?([а-яё\w]+)'
            ]
            
            for pattern in target_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    target = match.group(1).strip()
                    if target:
                        # Определяем тип цели
                        if target.isdigit():
                            parameters['target_id'] = int(target)
                        else:
                            parameters['target'] = target
                        break
        
        # Извлекаем дополнительные параметры
        self._extract_additional_parameters(content, parameters)
        
        return parameters
    
    def _extract_additional_parameters(self, content: str, parameters: Dict[str, Any]):
        """Extract additional parameters like file types, categories, etc."""
        content_lower = content.lower()
        
        # Извлекаем типы файлов
        file_type_patterns = [
            r'\b(pdf|doc|docx|txt|md|html|css|js|py|java|cpp|c|php|rb|go|rs)\b',
            r'\b(изображения|картинки|фото|видео|аудио|документы|код|ссылки)\b'
        ]
        
        for pattern in file_type_patterns:
            matches = re.findall(pattern, content_lower)
            if matches:
                parameters['file_types'] = list(set(matches))
                break
        
        # Извлекаем временные рамки
        time_patterns = [
            r'за\s+(последний|прошлый)\s+(день|неделю|месяц|год)',
            r'(сегодня|вчера|на\s+этой\s+неделе|в\s+этом\s+месяце)',
            r'(today|yesterday|this\s+week|this\s+month|last\s+week)'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, content_lower)
            if match:
                parameters['time_filter'] = match.group(0)
                break
        
        # Извлекаем количественные ограничения
        limit_patterns = [
            r'(?:покажи|показать|найди)\s+(?:первые\s+|последние\s+)?(\d+)',
            r'(?:show|find)\s+(?:first\s+|last\s+)?(\d+)'
        ]
        
        for pattern in limit_patterns:
            match = re.search(pattern, content_lower)
            if match:
                parameters['limit'] = int(match.group(1))
                break
    
    async def _ai_enhanced_interpretation(self, content: str):
        """Use AI for enhanced command interpretation with improved Russian language support."""
        try:
            prompt = f"""
Ты - эксперт по анализу команд для бота управления данными. Проанализируй сообщение и определи тип команды.

Сообщение: "{content}"

Типы команд и их варианты:

1. SEARCH (поиск/найти):
   - Русский: найди, найти, поищи, поискать, покажи, показать, где, ищи, искать, отыщи
   - Английский: find, search, look for, show me, where is, locate
   - Примеры: "найди код на Python", "покажи все ссылки", "где документация?"

2. CREATE_FOLDER (создать папку):
   - Русский: создай папку, сделай папку, новая папка, директория, каталог
   - Английский: create folder, make folder, new folder, directory
   - Примеры: "создай папку для проектов", "сделай директорию веб-разработка"

3. CREATE_ARCHIVE (создать архив):
   - Русский: создай архив, сделай архив, бэкап, резервная копия, архивировать
   - Английский: create archive, make backup, archive, backup
   - Примеры: "создай архив проектов", "сделай бэкап данных"

4. LIST (показать список):
   - Русский: список, покажи список, отобрази, вывести, все, что есть
   - Английский: list, show list, display, show all, what do you have
   - Примеры: "покажи все", "список документов", "что у меня есть?"

5. HELP (помощь):
   - Русский: помощь, помоги, справка, как, что умеешь, инструкция
   - Английский: help, how to, what can you do, instructions
   - Примеры: "помоги", "что ты умеешь?", "как работать?"

6. STATS (статистика):
   - Русский: статистика, стата, данные, сколько, количество, информация
   - Английский: statistics, stats, data, how many, count, info
   - Примеры: "покажи статистику", "сколько у меня файлов?"

7. EXPORT (экспорт):
   - Русский: экспорт, выгрузить, скачать, сохранить, экспортировать
   - Английский: export, download, save, extract
   - Примеры: "экспортируй данные", "скачай все"

8. ANALYZE (анализ):
   - Русский: анализ, проанализируй, разбери, изучи, проверь
   - Английский: analyze, analysis, examine, study, check
   - Примеры: "проанализируй контент", "разбери данные"

9. DELETE (удалить):
   - Русский: удали, убери, стереть, удалить, очистить, снести
   - Английский: delete, remove, clear, erase
   - Примеры: "удали папку", "убери этот файл"

10. UNKNOWN (неизвестно):
    - Если сообщение не является командой или просто информация

Важно:
- Учитывай контекст и смысл сообщения
- Обращай внимание на ключевые слова и их синонимы
- Определи язык сообщения (ru/en)
- Извлеки параметры из сообщения (что искать, название папки и т.д.)
- Оцени уверенность в классификации

Ответь ТОЛЬКО в JSON формате:
{{
    "command_type": "тип_команды",
    "parameters": {{"query": "что искать", "name": "название", "category": "категория", "target": "цель"}},
    "confidence": 0.0-1.0,
    "language": "ru/en",
    "reasoning": "краткое объяснение"
}}
"""
            
            response = await self.classifier._call_groq_api(prompt)
            if response:
                try:
                    # Parse JSON response
                    import json
                    result = json.loads(response)
                    
                    command_type_str = result.get('command_type', 'UNKNOWN')
                    
                    # Map string to enum
                    command_type = getattr(CommandType, command_type_str, CommandType.UNKNOWN)
                    
                    from ..handlers.command_interpreter import CommandIntent
                    return CommandIntent(
                        command_type=command_type,
                        parameters=result.get('parameters', {}),
                        confidence=result.get('confidence', 0.5),
                        language=result.get('language', 'ru')
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI response as JSON: {e}")
                    logger.error(f"Response was: {response}")
        
        except Exception as e:
            logger.error(f"AI enhanced interpretation error: {e}")
        
        return None
    
    async def _is_enhanced_question_or_request(self, content: str) -> bool:
        """Enhanced detection of questions and requests with better Russian support."""
        content_lower = content.lower()
        
        # Check for question marks
        if '?' in content or '？' in content:
            return True
        
        # Enhanced Russian question patterns
        for pattern in self.russian_question_patterns:
            if re.search(pattern, content_lower):
                return True
        
        # English question patterns
        english_patterns = [
            r'\b(what|how|where|when|why|which|who|whom|whose)\b',
            r'\b(can you|could you|would you|will you)\b',
            r'\b(help me|explain|tell me|show me)\b'
        ]
        
        for pattern in english_patterns:
            if re.search(pattern, content_lower):
                return True
        
        # Context-based detection
        question_indicators = [
            'объясни', 'расскажи', 'помоги', 'подскажи', 'покажи',
            'explain', 'tell', 'help', 'show', 'guide', 'how to'
        ]
        
        words = content_lower.split()
        if any(indicator in words for indicator in question_indicators):
            return True
        
        # AI-based question detection if available
        if self.classifier.groq_client and len(content) > 10:
            return await self._ai_question_detection(content)
        
        return False
    
    async def _ai_question_detection(self, content: str) -> bool:
        """Use AI to detect if content is a question or request."""
        try:
            prompt = f"""
Определи, является ли это сообщение вопросом или запросом помощи:

"{content}"

Ответь только "true" или "false".
"""
            
            response = await self.classifier._call_groq_api(prompt)
            if isinstance(response, str):
                return response.lower().strip() == 'true'
            elif isinstance(response, dict) and 'answer' in response:
                return response['answer'].lower().strip() == 'true'
        
        except Exception as e:
            logger.error(f"AI question detection error: {e}")
        
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
        """Determine the type of response needed based on enhanced content analysis."""
        content_lower = content.lower()
        
        # Search indicators - check first as it's most specific
        if await self._is_search_request(content):
            return 'search'
        
        # Enhanced help/guidance indicators
        help_indicators = [
            # Russian help indicators
            'помоги', 'помощь', 'помогите', 'как', 'что делать', 'не знаю', 'объясни', 'расскажи',
            'подскажи', 'подскажите', 'научи', 'научите', 'покажи как', 'покажите как',
            'инструкция', 'руководство', 'гайд', 'туториал', 'обучение', 'изучение',
            'начинающий', 'новичок', 'с чего начать', 'первые шаги', 'основы',
            'не понимаю', 'не получается', 'проблема', 'ошибка', 'затрудняюсь',
            
            # English help indicators
            'help', 'how to', 'what should', 'explain', 'tell me', 'guide', 'tutorial',
            'teach', 'show me', 'instruction', 'manual', 'beginner', 'newbie',
            'getting started', 'first steps', 'basics', 'fundamentals',
            'dont understand', 'having trouble', 'problem', 'issue', 'stuck'
        ]
        if any(indicator in content_lower for indicator in help_indicators):
            return 'help'
        
        # Enhanced technical/programming indicators
        tech_indicators = [
            # Russian technical terms
            'код', 'программирование', 'алгоритм', 'функция', 'класс', 'библиотека', 'фреймворк',
            'разработка', 'программа', 'приложение', 'скрипт', 'модуль', 'пакет', 'зависимость',
            'компиляция', 'отладка', 'тестирование', 'деплой', 'развертывание', 'сборка',
            'база данных', 'сервер', 'клиент', 'апи', 'интерфейс', 'протокол',
            'переменная', 'константа', 'массив', 'объект', 'метод', 'свойство',
            'наследование', 'полиморфизм', 'инкапсуляция', 'абстракция',
            'синтаксис', 'семантика', 'парсинг', 'компилятор', 'интерпретатор',
            
            # English technical terms
            'code', 'programming', 'algorithm', 'function', 'class', 'library', 'framework',
            'development', 'application', 'script', 'module', 'package', 'dependency',
            'compilation', 'debugging', 'testing', 'deployment', 'build', 'compile',
            'database', 'server', 'client', 'api', 'interface', 'protocol',
            'variable', 'constant', 'array', 'object', 'method', 'property',
            'inheritance', 'polymorphism', 'encapsulation', 'abstraction',
            'syntax', 'semantics', 'parsing', 'compiler', 'interpreter',
            
            # Programming languages and technologies
            'python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
            'react', 'vue', 'angular', 'node', 'express', 'django', 'flask',
            'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git', 'github',
            'html', 'css', 'sass', 'less', 'webpack', 'babel', 'typescript',
            'json', 'xml', 'yaml', 'sql', 'nosql', 'orm', 'mvc', 'rest', 'graphql'
        ]
        if any(indicator in content_lower for indicator in tech_indicators):
            return 'technical'
        
        # Organization/management indicators
        org_indicators = [
            # Russian organization terms
            'организация', 'структура', 'папка', 'каталог', 'архив', 'сортировка',
            'категория', 'группировка', 'классификация', 'упорядочивание',
            'управление', 'менеджмент', 'планирование', 'систематизация',
            
            # English organization terms
            'organization', 'structure', 'folder', 'directory', 'archive', 'sorting',
            'category', 'grouping', 'classification', 'ordering', 'arrangement',
            'management', 'planning', 'systematization', 'organize'
        ]
        if any(indicator in content_lower for indicator in org_indicators):
            return 'organization'
        
        # Default to general
        return 'general'
    
    async def _format_intelligent_response(self, ai_response: str, response_type: str, original_content: str) -> str:
        """Format AI response based on response type and content with enhanced Russian support."""
        # Choose appropriate emoji and title based on type
        type_config = {
            'search': {'emoji': '🔍', 'title': 'Результат поиска / Search Result'},
            'help': {'emoji': '💡', 'title': 'Справка / Help'},
            'technical': {'emoji': '🔧', 'title': 'Техническая информация / Technical Info'},
            'organization': {'emoji': '📁', 'title': 'Организация данных / Data Organization'},
            'general': {'emoji': '🤖', 'title': 'AI Ответ / AI Response'}
        }
        
        config = type_config.get(response_type, type_config['general'])
        
        # Format the main response with better structure
        formatted_response = f"{config['emoji']} **{config['title']}:**\n\n{ai_response}\n\n"
        
        # Add contextual footer based on response type
        if response_type == 'technical':
            formatted_response += "💾 *Хотите сохранить этот код/информацию? Отправьте его отдельным сообщением*\n"
            formatted_response += "💾 *Want to save this code/info? Send it as a separate message*\n\n"
            formatted_response += "🔧 *Доступные команды: /list, /search, /help*"
        elif response_type == 'help':
            formatted_response += "📚 *Нужна дополнительная помощь? Задайте уточняющий вопрос*\n"
            formatted_response += "📚 *Need more help? Ask a follow-up question*\n\n"
            formatted_response += "💡 *Команды: /help, /list, /search <запрос>*"
        elif response_type == 'organization':
            formatted_response += "📁 *Хотите создать папку или архив? Используйте команды создания*\n"
            formatted_response += "📁 *Want to create folder or archive? Use creation commands*\n\n"
            formatted_response += "📂 *Команды: /list, создать папку <название>, создать архив <название>*"
        elif response_type == 'search':
            formatted_response += "🔍 *Для более точного поиска используйте: /search <ваш запрос>*\n"
            formatted_response += "🔍 *For more precise search use: /search <your query>*\n\n"
            formatted_response += "📋 *Также доступно: /list для просмотра всех ресурсов*"
        else:
            formatted_response += "💡 *Если вы хотели сохранить этот контент, отправьте его еще раз*\n"
            formatted_response += "💡 *If you wanted to save this content, send it again*\n\n"
            formatted_response += "🤖 *Доступные команды: /help, /list, /search*"
        
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
    
    async def _handle_command_intent(self, update: Update, context: ContextTypes.DEFAULT_TYPE, command_intent):
        """Handle recognized command intents with enhanced Russian support."""
        try:
            command_type = command_intent.command_type
            parameters = command_intent.parameters
            language = command_intent.language
            
            # Show processing message
            if language == 'ru':
                processing_msg = await update.message.reply_text("⚙️ Обрабатываю команду...")
            else:
                processing_msg = await update.message.reply_text("⚙️ Processing command...")
            
            # Execute command based on type
            if command_type == CommandType.SEARCH:
                await self._execute_search_command(update, context, parameters, language)
            elif command_type == CommandType.CREATE_FOLDER:
                await self._execute_create_folder_command(update, context, parameters, language)
            elif command_type == CommandType.CREATE_ARCHIVE:
                await self._execute_create_archive_command(update, context, parameters, language)
            elif command_type == CommandType.LIST:
                await self._execute_list_command(update, context, parameters, language)
            elif command_type == CommandType.HELP:
                await self._execute_help_command(update, context, parameters, language)
            elif command_type == CommandType.STATS:
                await self._execute_stats_command(update, context, parameters, language)
            elif command_type == CommandType.EXPORT:
                await self._execute_export_command(update, context, parameters, language)
            elif command_type == CommandType.ANALYZE:
                await self._execute_analyze_command(update, context, parameters, language)
            elif command_type == CommandType.DELETE:
                await self._execute_delete_command(update, context, parameters, language)
            else:
                # Unknown command
                if language == 'ru':
                    await update.message.reply_text("❌ Неизвестная команда. Попробуйте /help для списка команд.")
                else:
                    await update.message.reply_text("❌ Unknown command. Try /help for available commands.")
            
            # Delete processing message
            await processing_msg.delete()
            
        except Exception as e:
            logger.error(f"Error handling command intent: {e}")
            if language == 'ru':
                await update.message.reply_text("❌ Ошибка при выполнении команды.")
            else:
                await update.message.reply_text("❌ Error executing command.")
    
    async def _execute_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parameters: Dict[str, Any], language: str):
        """Execute search command with enhanced parameters."""
        query = parameters.get('query', '')
        if not query:
            if language == 'ru':
                await update.message.reply_text("❌ Укажите что искать. Например: 'найди все фото'")
            else:
                await update.message.reply_text("❌ Please specify what to search for. Example: 'find all photos'")
            return
        
        # Perform search using existing search functionality
        await self._handle_search_from_message(update, context, query)
    
    async def _execute_create_folder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parameters: Dict[str, Any], language: str):
        """Execute create folder command."""
        folder_name = parameters.get('name', '')
        if not folder_name:
            if language == 'ru':
                await update.message.reply_text("❌ Укажите название папки. Например: 'создай папку Документы'")
            else:
                await update.message.reply_text("❌ Please specify folder name. Example: 'create folder Documents'")
            return
        
        try:
            # Create folder using storage
            folder_path = await self.storage.create_folder(folder_name)
            if language == 'ru':
                await update.message.reply_text(f"✅ Папка '{folder_name}' создана успешно!\n📁 Путь: {folder_path}")
            else:
                await update.message.reply_text(f"✅ Folder '{folder_name}' created successfully!\n📁 Path: {folder_path}")
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            if language == 'ru':
                await update.message.reply_text(f"❌ Ошибка при создании папки: {str(e)}")
            else:
                await update.message.reply_text(f"❌ Error creating folder: {str(e)}")
    
    async def _execute_create_archive_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parameters: Dict[str, Any], language: str):
        """Execute create archive command."""
        archive_name = parameters.get('name', '')
        if not archive_name:
            if language == 'ru':
                await update.message.reply_text("❌ Укажите название архива. Например: 'создай архив Бэкап'")
            else:
                await update.message.reply_text("❌ Please specify archive name. Example: 'create archive Backup'")
            return
        
        try:
            # Create archive using storage
            archive_path = await self.storage.create_archive(archive_name)
            if language == 'ru':
                await update.message.reply_text(f"✅ Архив '{archive_name}' создан успешно!\n📦 Путь: {archive_path}")
            else:
                await update.message.reply_text(f"✅ Archive '{archive_name}' created successfully!\n📦 Path: {archive_path}")
        except Exception as e:
            logger.error(f"Error creating archive: {e}")
            if language == 'ru':
                await update.message.reply_text(f"❌ Ошибка при создании архива: {str(e)}")
            else:
                await update.message.reply_text(f"❌ Error creating archive: {str(e)}")
    
    async def _execute_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parameters: Dict[str, Any], language: str):
        """Execute list command."""
        category = parameters.get('category', 'all')
        
        try:
            # Get list of items from storage
            items = await self.storage.list_items(category)
            
            if not items:
                if language == 'ru':
                    await update.message.reply_text("📂 Список пуст или категория не найдена.")
                else:
                    await update.message.reply_text("📂 List is empty or category not found.")
                return
            
            # Format list
            if language == 'ru':
                header = f"📋 **Список ({category}):**\n\n"
            else:
                header = f"📋 **List ({category}):**\n\n"
            
            items_text = "\n".join([f"• {item}" for item in items[:20]])  # Limit to 20 items
            
            if len(items) > 20:
                if language == 'ru':
                    footer = f"\n\n... и еще {len(items) - 20} элементов"
                else:
                    footer = f"\n\n... and {len(items) - 20} more items"
            else:
                footer = ""
            
            await update.message.reply_text(f"{header}{items_text}{footer}", parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error listing items: {e}")
            if language == 'ru':
                await update.message.reply_text(f"❌ Ошибка при получении списка: {str(e)}")
            else:
                await update.message.reply_text(f"❌ Error getting list: {str(e)}")
    
    async def _execute_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parameters: Dict[str, Any], language: str):
        """Execute help command."""
        # Use existing help command
        await self.help_command(update, context)
    
    async def _execute_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parameters: Dict[str, Any], language: str):
        """Execute stats command."""
        try:
            # Get statistics from storage
            stats = await self.storage.get_statistics()
            
            if language == 'ru':
                stats_text = f"""📊 **Статистика:**

📁 Всего папок: {stats.get('folders', 0)}
📄 Всего файлов: {stats.get('files', 0)}
📦 Архивов: {stats.get('archives', 0)}
💾 Общий размер: {stats.get('total_size', '0 MB')}
🕒 Последнее обновление: {stats.get('last_update', 'Неизвестно')}"""
            else:
                stats_text = f"""📊 **Statistics:**

📁 Total folders: {stats.get('folders', 0)}
📄 Total files: {stats.get('files', 0)}
📦 Archives: {stats.get('archives', 0)}
💾 Total size: {stats.get('total_size', '0 MB')}
🕒 Last update: {stats.get('last_update', 'Unknown')}"""
            
            await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            if language == 'ru':
                await update.message.reply_text(f"❌ Ошибка при получении статистики: {str(e)}")
            else:
                await update.message.reply_text(f"❌ Error getting statistics: {str(e)}")
    
    async def _execute_export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parameters: Dict[str, Any], language: str):
        """Execute export command."""
        try:
            # Export data using storage
            export_path = await self.storage.export_data()
            
            if language == 'ru':
                await update.message.reply_text(f"✅ Данные экспортированы успешно!\n📤 Файл: {export_path}")
            else:
                await update.message.reply_text(f"✅ Data exported successfully!\n📤 File: {export_path}")
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            if language == 'ru':
                await update.message.reply_text(f"❌ Ошибка при экспорте: {str(e)}")
            else:
                await update.message.reply_text(f"❌ Error exporting data: {str(e)}")
    
    async def _execute_analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parameters: Dict[str, Any], language: str):
        """Execute analyze command."""
        try:
            # Perform analysis using classifier
            analysis = await self.classifier.analyze_content_distribution()
            
            if language == 'ru':
                analysis_text = f"""🔍 **Анализ содержимого:**

{analysis}"""
            else:
                analysis_text = f"""🔍 **Content Analysis:**

{analysis}"""
            
            await update.message.reply_text(analysis_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            if language == 'ru':
                await update.message.reply_text(f"❌ Ошибка при анализе: {str(e)}")
            else:
                await update.message.reply_text(f"❌ Error analyzing content: {str(e)}")
    
    async def _execute_delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parameters: Dict[str, Any], language: str):
        """Execute delete command with confirmation."""
        target = parameters.get('target', '')
        if not target:
            if language == 'ru':
                await update.message.reply_text("❌ Укажите что удалить. Например: 'удали папку Старые файлы'")
            else:
                await update.message.reply_text("❌ Please specify what to delete. Example: 'delete folder Old files'")
            return
        
        # Create confirmation keyboard
        if language == 'ru':
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_confirm_{target}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="delete_cancel")]
            ]
            confirmation_text = f"⚠️ **Подтверждение удаления**\n\nВы действительно хотите удалить: `{target}`?\n\n⚠️ Это действие нельзя отменить!"
        else:
            keyboard = [
                [InlineKeyboardButton("✅ Yes, delete", callback_data=f"delete_confirm_{target}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="delete_cancel")]
            ]
            confirmation_text = f"⚠️ **Delete Confirmation**\n\nAre you sure you want to delete: `{target}`?\n\n⚠️ This action cannot be undone!"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(confirmation_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
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
        """Enhanced determination if content is a search request with better Russian support."""
        content_lower = content.lower()
        
        # Extended search keywords with more Russian variants
        search_keywords = [
            # Русские варианты
            'найди', 'найти', 'поиск', 'ищи', 'искать', 'поищи', 'поискать',
            'покажи', 'показать', 'отобрази', 'отыщи', 'отыскать',
            'где', 'какие', 'что', 'есть ли', 'имеется ли',
            'хочу найти', 'хочу посмотреть', 'нужно найти',
            # Английские варианты
            'find', 'search', 'look', 'show', 'get', 'retrieve', 'fetch',
            'where', 'what', 'which', 'is there', 'do you have', 'any'
        ]
        
        # Enhanced search patterns
        search_patterns = [
            # Прямые команды поиска
            r'\b(найди|найти|поищи|поискать|отыщи)\s+',
            r'\b(find|search|look\s+for|locate)\s+',
            
            # Вопросительные формы
            r'\b(где|where)\s+.*\??',
            r'\b(есть\s+ли|имеется\s+ли|is\s+there|do\s+you\s+have)\s+',
            r'\b(какие|what|which)\s+.*\??',
            r'\b(что\s+у\s+(?:тебя|меня)|what\s+do\s+you\s+have)\s+.*\??',
            
            # Показательные команды
            r'\b(покажи|показать|отобрази|show\s+me|display)\s+',
            
            # Желательные формы
            r'\b(хочу\s+(?:найти|посмотреть|увидеть)|want\s+to\s+(?:find|see))\s+',
            r'\b(нужно\s+(?:найти|посмотреть)|need\s+to\s+(?:find|see))\s+',
            
            # Вопросы о наличии
            r'\b(у\s+(?:тебя|меня)\s+есть)\s+.*\??',
            r'\b(do\s+you\s+have\s+any)\s+.*\??'
        ]
        
        # Check for direct search keywords
        words = content_lower.split()
        if any(keyword in content_lower for keyword in search_keywords):
            return True
        
        # Check for search patterns
        for pattern in search_patterns:
            if re.search(pattern, content_lower):
                return True
        
        # Check for question marks with potential search context
        if ('?' in content or '？' in content):
            search_context_words = [
                'файл', 'документ', 'код', 'ссылка', 'проект', 'данные',
                'file', 'document', 'code', 'link', 'project', 'data',
                'python', 'javascript', 'html', 'css', 'java', 'php'
            ]
            if any(word in content_lower for word in search_context_words):
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
        """Extract search terms from content with enhanced Russian support."""
        import re
        
        # Extended stop words for Russian and English
        stop_words = {
            # Russian search words
            'найди', 'найти', 'поиск', 'ищи', 'искать', 'покажи', 'показать',
            'найдите', 'поищи', 'поищите', 'отыщи', 'отыщите', 'разыщи',
            'выведи', 'выведите', 'дай', 'дайте', 'предоставь', 'предоставьте',
            'хочу', 'хотел', 'хотела', 'нужно', 'нужен', 'нужна', 'требуется',
            'можешь', 'можете', 'сможешь', 'сможете', 'помоги', 'помогите',
            
            # English search words
            'find', 'search', 'look', 'show', 'get', 'retrieve', 'fetch',
            'display', 'list', 'give', 'provide', 'want', 'need', 'help',
            'can', 'could', 'would', 'please', 'tell', 'show',
            
            # Question words
            'где', 'что', 'как', 'когда', 'почему', 'зачем', 'какой', 'какая', 'какое', 'какие',
            'where', 'what', 'how', 'when', 'why', 'which', 'who', 'whom',
            
            # Common words
            'есть', 'ли', 'is', 'there', 'do', 'you', 'have', 'are', 'was', 'were',
            'мне', 'me', 'для', 'for', 'по', 'about', 'про', 'о', 'на', 'в', 'с',
            'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'this', 'that',
            'у', 'к', 'от', 'до', 'из', 'за', 'под', 'над', 'при', 'без',
            'или', 'и', 'но', 'если', 'то', 'этот', 'эта', 'это', 'эти'
        }
        
        # Clean content - remove punctuation except for file extensions
        content_clean = re.sub(r'[^\w\s\.\-_]', ' ', content.lower())
        
        # Split into words
        words = content_clean.split()
        
        # Filter words
        search_terms = []
        for word in words:
            # Skip stop words
            if word in stop_words:
                continue
            
            # Skip very short words (but keep file extensions)
            if len(word) < 2:
                continue
            
            # Keep meaningful words
            if len(word) >= 2:
                # Special handling for file extensions and technical terms
                if ('.' in word and len(word) > 2) or len(word) >= 3:
                    search_terms.append(word)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in search_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms
    
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
    
    async def _smart_select_resources_for_archive(self, archive_name: str) -> list:
        """Smart selection of resources for archive based on name."""
        try:
            # Extract keywords from archive name
            keywords = archive_name.lower().replace('_', ' ').split()
            
            # Search for relevant resources
            all_resources = self.storage.get_all_resources()
            selected = []
            
            for resource in all_resources:
                score = 0
                content_lower = resource['content'].lower()
                desc_lower = resource['description'].lower()
                category_lower = resource['category'].lower()
                
                # Score based on keyword matches
                for keyword in keywords:
                    if keyword in content_lower:
                        score += 3
                    if keyword in desc_lower:
                        score += 2
                    if keyword in category_lower:
                        score += 4
                
                # Include if score is high enough
                if score >= 2:
                    selected.append(resource['id'])
            
            # Limit to 20 most recent if too many
            if len(selected) > 20:
                selected = selected[-20:]
            
            return selected
            
        except Exception as e:
            logger.error(f"Error in smart resource selection: {e}")
            return []
    
    async def _enhance_search_query(self, query: str) -> dict:
        """Use AI to enhance and understand search query."""
        try:
            # Create enhanced prompt for query understanding
            prompt = f"""
Analyze this search query and extract key information:
Query: "{query}"

Provide a JSON response with:
{{
    "keywords": ["list", "of", "key", "terms"],
    "categories": ["relevant", "categories"],
    "technologies": ["mentioned", "technologies"],
    "intent": "what user is looking for",
    "language": "detected language (en/ru)",
    "filters": {{
        "file_types": ["if", "specific", "types"],
        "difficulty": "beginner/intermediate/advanced or null",
        "recency": "recent/old or null"
    }}
}}

Focus on web development, design, programming topics.
"""
            
            # Try to get AI enhancement
            if self.classifier.groq_client:
                response = await self.classifier._call_groq_api(prompt)
                if response and 'keywords' in response:
                    return response
            
            # Fallback to simple keyword extraction
            return {
                "keywords": query.lower().split(),
                "categories": [],
                "technologies": self._extract_technologies_from_text(query),
                "intent": "search",
                "language": "ru" if any(ord(c) > 127 for c in query) else "en",
                "filters": {}
            }
            
        except Exception as e:
            logger.error(f"Error enhancing search query: {e}")
            return {"keywords": query.lower().split(), "categories": [], "technologies": [], "intent": "search", "language": "en", "filters": {}}
    
    async def _perform_smart_search(self, enhanced_query: dict) -> list:
        """Perform enhanced search using AI-processed query."""
        try:
            all_resources = self.storage.get_all_resources()
            scored_results = []
            
            keywords = enhanced_query.get('keywords', [])
            categories = enhanced_query.get('categories', [])
            technologies = enhanced_query.get('technologies', [])
            
            for resource in all_resources:
                score = 0
                content_lower = resource['content'].lower()
                desc_lower = resource['description'].lower()
                category_lower = resource['category'].lower()
                
                # Keyword matching
                for keyword in keywords:
                    if keyword in content_lower:
                        score += 2
                    if keyword in desc_lower:
                        score += 3
                    if keyword in category_lower:
                        score += 4
                
                # Category matching
                for category in categories:
                    if category.lower() in category_lower:
                        score += 5
                
                # Technology matching
                for tech in technologies:
                    if tech.lower() in content_lower or tech.lower() in desc_lower:
                        score += 3
                
                # URL bonus for web development content
                if any(url_indicator in content_lower for url_indicator in ['http', 'www', '.com', '.org', 'github']):
                    score += 1
                
                if score > 0:
                    # Calculate relevance score (0-10)
                    relevance = min(10, score)
                    
                    result = resource.copy()
                    result['relevance_score'] = relevance
                    scored_results.append(result)
            
            # Sort by relevance score
            scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return scored_results
            
        except Exception as e:
            logger.error(f"Error in smart search: {e}")
            return []
    
    async def _perform_content_analysis(self) -> dict:
        """Perform comprehensive analysis of stored content."""
        try:
            all_resources = self.storage.get_all_resources()
            folders = self.storage.get_all_folders()
            archives = self.storage.get_all_archives()
            
            # Basic statistics
            analysis = {
                'total_resources': len(all_resources),
                'total_categories': len(set(r['category'] for r in all_resources)),
                'total_folders': len(folders),
                'total_archives': len(archives)
            }
            
            # Category analysis
            category_counts = {}
            for resource in all_resources:
                category = resource['category']
                category_counts[category] = category_counts.get(category, 0) + 1
            
            analysis['top_categories'] = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Technology analysis
            tech_counts = {}
            tech_patterns = {
                'React': ['react', 'jsx', 'hooks'],
                'Vue': ['vue', 'vuejs'],
                'Angular': ['angular', 'typescript'],
                'Python': ['python', 'django', 'flask'],
                'JavaScript': ['javascript', 'js', 'node'],
                'CSS': ['css', 'sass', 'scss'],
                'HTML': ['html', 'html5'],
                'Docker': ['docker', 'container'],
                'Git': ['git', 'github', 'gitlab'],
                'API': ['api', 'rest', 'graphql'],
                'Database': ['sql', 'mongodb', 'postgres'],
                'Design': ['figma', 'sketch', 'ui', 'ux']
            }
            
            for resource in all_resources:
                content_lower = resource['content'].lower()
                for tech, patterns in tech_patterns.items():
                    if any(pattern in content_lower for pattern in patterns):
                        tech_counts[tech] = tech_counts.get(tech, 0) + 1
            
            analysis['technologies'] = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Generate recommendations
            recommendations = []
            
            if analysis['total_resources'] > 50:
                recommendations.append("Consider creating more specific folders to organize your resources")
            
            if len(analysis['top_categories']) > 10:
                recommendations.append("You have many categories - consider consolidating similar ones")
            
            if any(count > 20 for _, count in analysis['top_categories'][:3]):
                recommendations.append("Create archives for your most popular categories")
            
            analysis['recommendations'] = recommendations
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in content analysis: {e}")
            return {'total_resources': 0, 'total_categories': 0, 'total_folders': 0, 'total_archives': 0}
    
    def _extract_technologies_from_text(self, text: str) -> list:
        """Extract technology names from text."""
        technologies = []
        text_lower = text.lower()
        
        tech_keywords = {
            'react', 'vue', 'angular', 'python', 'javascript', 'typescript',
            'css', 'html', 'sass', 'scss', 'node', 'express', 'django',
            'flask', 'docker', 'kubernetes', 'git', 'github', 'api', 'rest',
            'graphql', 'sql', 'mongodb', 'postgres', 'figma', 'sketch',
            'photoshop', 'illustrator', 'ui', 'ux', 'design', 'frontend',
            'backend', 'fullstack', 'mobile', 'ios', 'android', 'swift',
            'kotlin', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust'
        }
        
        for tech in tech_keywords:
            if tech in text_lower:
                technologies.append(tech.capitalize())
        
        return list(set(technologies))
    
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
                    await self._execute_search_command(update, context, query, language)
                else:
                    await self._send_search_help(update, language)
            
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
                category = parameters.get('category', '')
                await self._execute_list_command(update, context, category, language)
            
            elif command_type == CommandType.HELP:
                await self._execute_help_command(update, context, language)
            
            elif command_type == CommandType.STATS:
                await self._execute_stats_command(update, context, language)
            
            elif command_type == CommandType.EXPORT:
                await self._execute_export_command(update, context, language)
            
            elif command_type == CommandType.ANALYZE:
                query = parameters.get('query', '')
                await self._execute_analyze_command(update, context, query, language)
            
            elif command_type == CommandType.DELETE:
                target = parameters.get('target', '')
                await self._execute_delete_command(update, context, target, language)
            
            await status_msg.delete()
            
        except Exception as e:
            logger.error(f"Error handling command intent: {e}")
            error_msg = "❌ Ошибка выполнения команды" if language == 'ru' else "❌ Command execution error"
            await update.message.reply_text(error_msg)
    
    async def _execute_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, language: str):
        """Execute search command."""
        results = self.storage.search_resources(query)
        
        if results:
            if language == 'ru':
                response = f"🔍 **Результаты поиска для '{query}':**\n\n"
            else:
                response = f"🔍 **Search results for '{query}':**\n\n"
            
            for i, result in enumerate(results[:10], 1):
                response += f"{i}. **{result['category']}** - {result['description'][:100]}...\n"
                response += f"   🆔 ID: {result['id']}\n\n"
            
            if len(results) > 10:
                if language == 'ru':
                    response += f"... и еще {len(results) - 10} результатов\n"
                else:
                    response += f"... and {len(results) - 10} more results\n"
        else:
            if language == 'ru':
                response = f"❌ Ничего не найдено по запросу '{query}'"
            else:
                response = f"❌ No results found for '{query}'"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_create_folder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, folder_name: str, language: str):
        """Execute create folder command."""
        try:
            folder_id = self.storage.create_folder(folder_name, update.effective_user.id)
            
            if language == 'ru':
                response = f"✅ Папка '{folder_name}' создана успешно!\n🆔 ID: {folder_id}"
            else:
                response = f"✅ Folder '{folder_name}' created successfully!\n🆔 ID: {folder_id}"
            
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            if language == 'ru':
                response = f"❌ Ошибка создания папки '{folder_name}'"
            else:
                response = f"❌ Error creating folder '{folder_name}'"
            await update.message.reply_text(response)
    
    async def _execute_create_archive_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, archive_name: str, language: str):
        """Execute create archive command."""
        try:
            archive_id = self.storage.create_archive(archive_name, update.effective_user.id)
            
            if language == 'ru':
                response = f"✅ Архив '{archive_name}' создан успешно!\n🆔 ID: {archive_id}"
            else:
                response = f"✅ Archive '{archive_name}' created successfully!\n🆔 ID: {archive_id}"
            
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error creating archive: {e}")
            if language == 'ru':
                response = f"❌ Ошибка создания архива '{archive_name}'"
            else:
                response = f"❌ Error creating archive '{archive_name}'"
            await update.message.reply_text(response)
    
    async def _execute_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, language: str):
        """Execute list command."""
        if category:
            resources = self.storage.get_resources_by_category(category)
            if language == 'ru':
                title = f"📋 Ресурсы в категории '{category}':"
            else:
                title = f"📋 Resources in category '{category}':"
        else:
            resources = self.storage.get_all_resources()
            if language == 'ru':
                title = "📋 Все ресурсы:"
            else:
                title = "📋 All resources:"
        
        if resources:
            response = f"**{title}**\n\n"
            for i, resource in enumerate(resources[:20], 1):
                response += f"{i}. **{resource['category']}** - {resource['description'][:80]}...\n"
            
            if len(resources) > 20:
                if language == 'ru':
                    response += f"\n... и еще {len(resources) - 20} ресурсов"
                else:
                    response += f"\n... and {len(resources) - 20} more resources"
        else:
            if language == 'ru':
                response = "❌ Ресурсы не найдены"
            else:
                response = "❌ No resources found"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute help command."""
        if language == 'ru':
            help_text = (
                "🆘 **Справка по командам**\n\n"
                "**Поиск:**\n"
                "• 'найди Python код'\n"
                "• 'покажи все документы'\n\n"
                "**Создание:**\n"
                "• 'создай папку для проектов'\n"
                "• 'сделай архив старых файлов'\n\n"
                "**Управление:**\n"
                "• 'статистика'\n"
                "• 'экспорт данных'\n"
                "• 'помощь'\n\n"
                "💡 Просто говорите естественным языком!"
            )
        else:
            help_text = (
                "🆘 **Command Help**\n\n"
                "**Search:**\n"
                "• 'find Python code'\n"
                "• 'show all documents'\n\n"
                "**Creation:**\n"
                "• 'create project folder'\n"
                "• 'make archive for old files'\n\n"
                "**Management:**\n"
                "• 'statistics'\n"
                "• 'export data'\n"
                "• 'help'\n\n"
                "💡 Just speak naturally!"
            )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute stats command."""
        analysis = await self._analyze_content()
        
        if language == 'ru':
            response = (
                f"📊 **Статистика**\n\n"
                f"📁 Всего ресурсов: {analysis['total_resources']}\n"
                f"📂 Категорий: {analysis['total_categories']}\n"
                f"🗂 Папок: {analysis['total_folders']}\n"
                f"📦 Архивов: {analysis['total_archives']}\n\n"
            )
            
            if analysis.get('top_categories'):
                response += "**Топ категории:**\n"
                for category, count in analysis['top_categories'][:5]:
                    response += f"• {category}: {count}\n"
        else:
            response = (
                f"📊 **Statistics**\n\n"
                f"📁 Total resources: {analysis['total_resources']}\n"
                f"📂 Categories: {analysis['total_categories']}\n"
                f"🗂 Folders: {analysis['total_folders']}\n"
                f"📦 Archives: {analysis['total_archives']}\n\n"
            )
            
            if analysis.get('top_categories'):
                response += "**Top categories:**\n"
                for category, count in analysis['top_categories'][:5]:
                    response += f"• {category}: {count}\n"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute export command."""
        if language == 'ru':
            response = "📤 Функция экспорта будет доступна в следующем обновлении!"
        else:
            response = "📤 Export functionality will be available in the next update!"
        
        await update.message.reply_text(response)
    
    async def _execute_analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, language: str):
        """Execute analyze command."""
        if query:
            results = self.storage.search_resources(query)
            if results:
                if language == 'ru':
                    response = f"🔍 Найдено {len(results)} ресурсов по запросу '{query}'\n\n"
                    response += "📊 Краткий анализ найденного контента будет добавлен в следующем обновлении."
                else:
                    response = f"🔍 Found {len(results)} resources for '{query}'\n\n"
                    response += "📊 Brief analysis of found content will be added in the next update."
            else:
                if language == 'ru':
                    response = f"❌ Ничего не найдено для анализа по запросу '{query}'"
                else:
                    response = f"❌ Nothing found to analyze for '{query}'"
        else:
            await self._execute_stats_command(update, context, language)
            return
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, target: str, language: str):
        """Execute delete command."""
        if language == 'ru':
            response = f"⚠️ Функция удаления '{target}' будет доступна в следующем обновлении!\n"
            response += "Для безопасности данных эта функция требует дополнительного подтверждения."
        else:
            response = f"⚠️ Delete functionality for '{target}' will be available in the next update!\n"
            response += "For data safety, this function requires additional confirmation."
        
        await update.message.reply_text(response)
    
    async def _send_search_help(self, update: Update, language: str):
        """Send search help message."""
        if language == 'ru':
            response = "🔍 Укажите что искать. Например: 'найди код на Python'"
        else:
            response = "🔍 Please specify what to search for. Example: 'find Python code'"
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
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("delete_confirm_"):
            # Extract target from callback data
            target = data.replace("delete_confirm_", "")
            
            try:
                # Perform actual deletion using storage
                success = await self.storage.delete_item(target)
                
                if success:
                    # Determine language from user context or message
                    language = 'ru' if any(ord(c) > 127 for c in query.message.text) else 'en'
                    
                    if language == 'ru':
                        response = f"✅ '{target}' успешно удален!"
                    else:
                        response = f"✅ '{target}' successfully deleted!"
                else:
                    if language == 'ru':
                        response = f"❌ Не удалось удалить '{target}'. Возможно, элемент не найден."
                    else:
                        response = f"❌ Failed to delete '{target}'. Item might not exist."
                        
            except Exception as e:
                logger.error(f"Error deleting item: {e}")
                language = 'ru' if any(ord(c) > 127 for c in query.message.text) else 'en'
                
                if language == 'ru':
                    response = f"❌ Ошибка при удалении: {str(e)}"
                else:
                    response = f"❌ Error during deletion: {str(e)}"
            
            # Edit the original message
            await query.edit_message_text(response)
            
        elif data == "delete_cancel":
            # Determine language
            language = 'ru' if any(ord(c) > 127 for c in query.message.text) else 'en'
            
            if language == 'ru':
                response = "❌ Удаление отменено."
            else:
                response = "❌ Deletion cancelled."
            
            await query.edit_message_text(response)
        
        else:
            # Handle other callback queries if needed
            logger.warning(f"Unknown callback query data: {data}")
    
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

    async def create_folder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create a virtual folder for organizing resources."""
        if not context.args:
            await update.message.reply_text(
                "📁 **Usage:** `/create_folder <folder_name> [description]`\n"
                "📁 **Использование:** `/create_folder <имя_папки> [описание]`\n\n"
                "**Examples / Примеры:**\n"
                "• `/create_folder react_projects React проекты и компоненты`\n"
                "• `/create_folder design_resources UI/UX дизайн ресурсы`"
            )
            return
        
        folder_name = context.args[0]
        description = ' '.join(context.args[1:]) if len(context.args) > 1 else f"Папка для {folder_name}"
        
        try:
            # Create folder as a special resource
            folder_id = self.storage.create_folder(
                name=folder_name,
                description=description,
                user_id=update.effective_user.id,
                username=update.effective_user.username
            )
            
            await update.message.reply_text(
                f"📁 **Folder created successfully!**\n\n"
                f"📂 **Name:** {folder_name}\n"
                f"📝 **Description:** {description}\n"
                f"🆔 **ID:** {folder_id}\n\n"
                f"📁 **Папка успешно создана!**\n"
                f"Используйте `/add_to_folder {folder_id}` для добавления ресурсов",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            await update.message.reply_text(
                "❌ Error creating folder. Please try again.\n"
                "❌ Ошибка создания папки. Попробуйте еще раз."
            )
    
    async def create_archive_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create an archive from selected resources."""
        if not context.args:
            await update.message.reply_text(
                "📦 **Usage:** `/create_archive <archive_name> [resource_ids...]`\n"
                "📦 **Использование:** `/create_archive <имя_архива> [id_ресурсов...]`\n\n"
                "**Examples / Примеры:**\n"
                "• `/create_archive web_dev_2024 abc123 def456 ghi789`\n"
                "• `/create_archive react_components` (создаст архив из последних React ресурсов)"
            )
            return
        
        archive_name = context.args[0]
        resource_ids = context.args[1:] if len(context.args) > 1 else []
        
        try:
            # If no specific IDs provided, use smart selection
            if not resource_ids:
                resource_ids = await self._smart_select_resources_for_archive(archive_name)
            
            archive_id = self.storage.create_archive(
                name=archive_name,
                resource_ids=resource_ids,
                user_id=update.effective_user.id,
                username=update.effective_user.username
            )
            
            await update.message.reply_text(
                f"📦 **Archive created successfully!**\n\n"
                f"📂 **Name:** {archive_name}\n"
                f"📊 **Resources:** {len(resource_ids)}\n"
                f"🆔 **ID:** {archive_id}\n\n"
                f"📦 **Архив успешно создан!**\n"
                f"Используйте `/export_archive {archive_id}` для скачивания",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error creating archive: {e}")
            await update.message.reply_text(
                "❌ Error creating archive. Please try again.\n"
                "❌ Ошибка создания архива. Попробуйте еще раз."
            )
    
    async def find_folder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Find folders and archives by name or content."""
        if not context.args:
            await update.message.reply_text(
                "🔍 **Usage:** `/find_folder <search_query>`\n"
                "🔍 **Использование:** `/find_folder <поисковый_запрос>`\n\n"
                "**Examples / Примеры:**\n"
                "• `/find_folder react`\n"
                "• `/find_folder дизайн`\n"
                "• `/find_folder web development`"
            )
            return
        
        query = ' '.join(context.args)
        
        try:
            folders = self.storage.find_folders(query)
            archives = self.storage.find_archives(query)
            
            if folders or archives:
                response = f"🔍 **Search Results for '{query}':**\n\n"
                
                if folders:
                    response += "📁 **Folders:**\n"
                    for folder in folders[:5]:
                        response += f"• {folder['name']} - {folder['description'][:50]}...\n"
                        response += f"  🆔 ID: {folder['id']} | 📊 Items: {folder.get('item_count', 0)}\n\n"
                
                if archives:
                    response += "📦 **Archives:**\n"
                    for archive in archives[:5]:
                        response += f"• {archive['name']} - {archive.get('description', 'Archive')[:50]}...\n"
                        response += f"  🆔 ID: {archive['id']} | 📊 Items: {len(archive.get('resource_ids', []))}\n\n"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    f"❌ No folders or archives found for '{query}'.\n"
                    f"❌ Папки или архивы по запросу '{query}' не найдены."
                )
                
        except Exception as e:
            logger.error(f"Error finding folders: {e}")
            await update.message.reply_text(
                "❌ Search error. Please try again.\n"
                "❌ Ошибка поиска. Попробуйте еще раз."
            )
    
    async def smart_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced search with AI-powered understanding."""
        if not context.args:
            await update.message.reply_text(
                "🧠 **Usage:** `/smart_search <natural_language_query>`\n"
                "🧠 **Использование:** `/smart_search <запрос_на_естественном_языке>`\n\n"
                "**Examples / Примеры:**\n"
                "• `/smart_search найди все React компоненты с хуками`\n"
                "• `/smart_search show me Python tutorials for beginners`\n"
                "• `/smart_search дизайн системы для мобильных приложений`"
            )
            return
        
        query = ' '.join(context.args)
        
        try:
            # Show processing indicator
            status_msg = await update.message.reply_text("🧠 Analyzing query / Анализирую запрос...")
            
            # Use AI to understand and enhance the query
            enhanced_query = await self._enhance_search_query(query)
            
            # Perform enhanced search
            results = await self._perform_smart_search(enhanced_query)
            
            await status_msg.delete()
            
            if results:
                response = f"🧠 **Smart Search Results for '{query}':**\n\n"
                
                for i, result in enumerate(results[:8], 1):
                    relevance = result.get('relevance_score', 0.0)
                    response += (
                        f"{i}. **{result['category']}** - {result['description'][:80]}...\n"
                        f"   🎯 Relevance: {relevance:.1f}/10 | 🆔 ID: {result['id']}\n\n"
                    )
                
                if len(results) > 8:
                    response += f"... and {len(results) - 8} more results\n\n"
                
                response += f"📊 Found {len(results)} relevant results"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    f"❌ No relevant results found for '{query}'.\n"
                    f"❌ Релевантные результаты по запросу '{query}' не найдены."
                )
                
        except Exception as e:
            logger.error(f"Error in smart search: {e}")
            await update.message.reply_text(
                "❌ Smart search error. Please try again.\n"
                "❌ Ошибка умного поиска. Попробуйте еще раз."
            )
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analyze and provide insights about stored content."""
        try:
            # Show processing indicator
            status_msg = await update.message.reply_text("📊 Analyzing content / Анализирую контент...")
            
            # Get comprehensive analysis
            analysis = await self._perform_content_analysis()
            
            await status_msg.delete()
            
            response = (
                "📊 **Content Analysis / Анализ контента:**\n\n"
                f"📂 **Total Resources / Всего ресурсов:** {analysis['total_resources']}\n"
                f"🏷️ **Categories / Категорий:** {analysis['total_categories']}\n"
                f"📁 **Folders / Папок:** {analysis['total_folders']}\n"
                f"📦 **Archives / Архивов:** {analysis['total_archives']}\n\n"
            )
            
            # Top categories
            if analysis.get('top_categories'):
                response += "🔝 **Top Categories / Топ категории:**\n"
                for category, count in analysis['top_categories'][:5]:
                    response += f"• {category}: {count}\n"
                response += "\n"
            
            # Technology insights
            if analysis.get('technologies'):
                response += "💻 **Technologies Found / Найденные технологии:**\n"
                for tech, count in analysis['technologies'][:8]:
                    response += f"• {tech}: {count}\n"
                response += "\n"
            
            # Recommendations
            if analysis.get('recommendations'):
                response += "💡 **Recommendations / Рекомендации:**\n"
                for rec in analysis['recommendations'][:3]:
                    response += f"• {rec}\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            await update.message.reply_text(
                "❌ Analysis error. Please try again.\n"
                "❌ Ошибка анализа. Попробуйте еще раз."
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
    
    async def _smart_select_resources_for_archive(self, archive_name: str) -> list:
        """Smart selection of resources for archive based on name."""
        try:
            # Extract keywords from archive name
            keywords = archive_name.lower().replace('_', ' ').split()
            
            # Search for relevant resources
            all_resources = self.storage.get_all_resources()
            selected = []
            
            for resource in all_resources:
                score = 0
                content_lower = resource['content'].lower()
                desc_lower = resource['description'].lower()
                category_lower = resource['category'].lower()
                
                # Score based on keyword matches
                for keyword in keywords:
                    if keyword in content_lower:
                        score += 3
                    if keyword in desc_lower:
                        score += 2
                    if keyword in category_lower:
                        score += 4
                
                # Include if score is high enough
                if score >= 2:
                    selected.append(resource['id'])
            
            # Limit to 20 most recent if too many
            if len(selected) > 20:
                selected = selected[-20:]
            
            return selected
            
        except Exception as e:
            logger.error(f"Error in smart resource selection: {e}")
            return []
    
    async def _enhance_search_query(self, query: str) -> dict:
        """Use AI to enhance and understand search query."""
        try:
            # Create enhanced prompt for query understanding
            prompt = f"""
Analyze this search query and extract key information:
Query: "{query}"

Provide a JSON response with:
{{
    "keywords": ["list", "of", "key", "terms"],
    "categories": ["relevant", "categories"],
    "technologies": ["mentioned", "technologies"],
    "intent": "what user is looking for",
    "language": "detected language (en/ru)",
    "filters": {{
        "file_types": ["if", "specific", "types"],
        "difficulty": "beginner/intermediate/advanced or null",
        "recency": "recent/old or null"
    }}
}}

Focus on web development, design, programming topics.
"""
            
            # Try to get AI enhancement
            if self.classifier.groq_client:
                response = await self.classifier._call_groq_api(prompt)
                if response and 'keywords' in response:
                    return response
            
            # Fallback to simple keyword extraction
            return {
                "keywords": query.lower().split(),
                "categories": [],
                "technologies": self._extract_technologies_from_text(query),
                "intent": "search",
                "language": "ru" if any(ord(c) > 127 for c in query) else "en",
                "filters": {}
            }
            
        except Exception as e:
            logger.error(f"Error enhancing search query: {e}")
            return {"keywords": query.lower().split(), "categories": [], "technologies": [], "intent": "search", "language": "en", "filters": {}}
    
    async def _perform_smart_search(self, enhanced_query: dict) -> list:
        """Perform enhanced search using AI-processed query."""
        try:
            all_resources = self.storage.get_all_resources()
            scored_results = []
            
            keywords = enhanced_query.get('keywords', [])
            categories = enhanced_query.get('categories', [])
            technologies = enhanced_query.get('technologies', [])
            
            for resource in all_resources:
                score = 0
                content_lower = resource['content'].lower()
                desc_lower = resource['description'].lower()
                category_lower = resource['category'].lower()
                
                # Keyword matching
                for keyword in keywords:
                    if keyword in content_lower:
                        score += 2
                    if keyword in desc_lower:
                        score += 3
                    if keyword in category_lower:
                        score += 4
                
                # Category matching
                for category in categories:
                    if category.lower() in category_lower:
                        score += 5
                
                # Technology matching
                for tech in technologies:
                    if tech.lower() in content_lower or tech.lower() in desc_lower:
                        score += 3
                
                # URL bonus for web development content
                if any(url_indicator in content_lower for url_indicator in ['http', 'www', '.com', '.org', 'github']):
                    score += 1
                
                if score > 0:
                    # Calculate relevance score (0-10)
                    relevance = min(10, score)
                    
                    result = resource.copy()
                    result['relevance_score'] = relevance
                    scored_results.append(result)
            
            # Sort by relevance score
            scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return scored_results
            
        except Exception as e:
            logger.error(f"Error in smart search: {e}")
            return []
    
    async def _perform_content_analysis(self) -> dict:
        """Perform comprehensive analysis of stored content."""
        try:
            all_resources = self.storage.get_all_resources()
            folders = self.storage.get_all_folders()
            archives = self.storage.get_all_archives()
            
            # Basic statistics
            analysis = {
                'total_resources': len(all_resources),
                'total_categories': len(set(r['category'] for r in all_resources)),
                'total_folders': len(folders),
                'total_archives': len(archives)
            }
            
            # Category analysis
            category_counts = {}
            for resource in all_resources:
                category = resource['category']
                category_counts[category] = category_counts.get(category, 0) + 1
            
            analysis['top_categories'] = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Technology analysis
            tech_counts = {}
            tech_patterns = {
                'React': ['react', 'jsx', 'hooks'],
                'Vue': ['vue', 'vuejs'],
                'Angular': ['angular', 'typescript'],
                'Python': ['python', 'django', 'flask'],
                'JavaScript': ['javascript', 'js', 'node'],
                'CSS': ['css', 'sass', 'scss'],
                'HTML': ['html', 'html5'],
                'Docker': ['docker', 'container'],
                'Git': ['git', 'github', 'gitlab'],
                'API': ['api', 'rest', 'graphql'],
                'Database': ['sql', 'mongodb', 'postgres'],
                'Design': ['figma', 'sketch', 'ui', 'ux']
            }
            
            for resource in all_resources:
                content_lower = resource['content'].lower()
                for tech, patterns in tech_patterns.items():
                    if any(pattern in content_lower for pattern in patterns):
                        tech_counts[tech] = tech_counts.get(tech, 0) + 1
            
            analysis['technologies'] = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Generate recommendations
            recommendations = []
            
            if analysis['total_resources'] > 50:
                recommendations.append("Consider creating more specific folders to organize your resources")
            
            if len(analysis['top_categories']) > 10:
                recommendations.append("You have many categories - consider consolidating similar ones")
            
            if any(count > 20 for _, count in analysis['top_categories'][:3]):
                recommendations.append("Create archives for your most popular categories")
            
            analysis['recommendations'] = recommendations
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in content analysis: {e}")
            return {'total_resources': 0, 'total_categories': 0, 'total_folders': 0, 'total_archives': 0}
    
    def _extract_technologies_from_text(self, text: str) -> list:
        """Extract technology names from text."""
        technologies = []
        text_lower = text.lower()
        
        tech_keywords = {
            'react', 'vue', 'angular', 'python', 'javascript', 'typescript',
            'css', 'html', 'sass', 'scss', 'node', 'express', 'django',
            'flask', 'docker', 'kubernetes', 'git', 'github', 'api', 'rest',
            'graphql', 'sql', 'mongodb', 'postgres', 'figma', 'sketch',
            'photoshop', 'illustrator', 'ui', 'ux', 'design', 'frontend',
            'backend', 'fullstack', 'mobile', 'ios', 'android', 'swift',
            'kotlin', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust'
        }
        
        for tech in tech_keywords:
            if tech in text_lower:
                technologies.append(tech.capitalize())
        
        return list(set(technologies))
    
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
                    await self._execute_search_command(update, context, query, language)
                else:
                    await self._send_search_help(update, language)
            
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
                category = parameters.get('category', '')
                await self._execute_list_command(update, context, category, language)
            
            elif command_type == CommandType.HELP:
                await self._execute_help_command(update, context, language)
            
            elif command_type == CommandType.STATS:
                await self._execute_stats_command(update, context, language)
            
            elif command_type == CommandType.EXPORT:
                await self._execute_export_command(update, context, language)
            
            elif command_type == CommandType.ANALYZE:
                query = parameters.get('query', '')
                await self._execute_analyze_command(update, context, query, language)
            
            elif command_type == CommandType.DELETE:
                target = parameters.get('target', '')
                await self._execute_delete_command(update, context, target, language)
            
            await status_msg.delete()
            
        except Exception as e:
            logger.error(f"Error handling command intent: {e}")
            error_msg = "❌ Ошибка выполнения команды" if language == 'ru' else "❌ Command execution error"
            await update.message.reply_text(error_msg)
    
    async def _execute_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, language: str):
        """Execute search command."""
        results = self.storage.search_resources(query)
        
        if results:
            if language == 'ru':
                response = f"🔍 **Результаты поиска для '{query}':**\n\n"
            else:
                response = f"🔍 **Search results for '{query}':**\n\n"
            
            for i, result in enumerate(results[:10], 1):
                response += f"{i}. **{result['category']}** - {result['description'][:100]}...\n"
                response += f"   🆔 ID: {result['id']}\n\n"
            
            if len(results) > 10:
                if language == 'ru':
                    response += f"... и еще {len(results) - 10} результатов\n"
                else:
                    response += f"... and {len(results) - 10} more results\n"
        else:
            if language == 'ru':
                response = f"❌ Ничего не найдено по запросу '{query}'"
            else:
                response = f"❌ No results found for '{query}'"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_create_folder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, folder_name: str, language: str):
        """Execute create folder command."""
        try:
            folder_id = self.storage.create_folder(folder_name, update.effective_user.id)
            
            if language == 'ru':
                response = f"✅ Папка '{folder_name}' создана успешно!\n🆔 ID: {folder_id}"
            else:
                response = f"✅ Folder '{folder_name}' created successfully!\n🆔 ID: {folder_id}"
            
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            if language == 'ru':
                response = f"❌ Ошибка создания папки '{folder_name}'"
            else:
                response = f"❌ Error creating folder '{folder_name}'"
            await update.message.reply_text(response)
    
    async def _execute_create_archive_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, archive_name: str, language: str):
        """Execute create archive command."""
        try:
            archive_id = self.storage.create_archive(archive_name, update.effective_user.id)
            
            if language == 'ru':
                response = f"✅ Архив '{archive_name}' создан успешно!\n🆔 ID: {archive_id}"
            else:
                response = f"✅ Archive '{archive_name}' created successfully!\n🆔 ID: {archive_id}"
            
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error creating archive: {e}")
            if language == 'ru':
                response = f"❌ Ошибка создания архива '{archive_name}'"
            else:
                response = f"❌ Error creating archive '{archive_name}'"
            await update.message.reply_text(response)
    
    async def _execute_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, language: str):
        """Execute list command."""
        if category:
            resources = self.storage.get_resources_by_category(category)
            if language == 'ru':
                title = f"📋 Ресурсы в категории '{category}':"
            else:
                title = f"📋 Resources in category '{category}':"
        else:
            resources = self.storage.get_all_resources()
            if language == 'ru':
                title = "📋 Все ресурсы:"
            else:
                title = "📋 All resources:"
        
        if resources:
            response = f"**{title}**\n\n"
            for i, resource in enumerate(resources[:20], 1):
                response += f"{i}. **{resource['category']}** - {resource['description'][:80]}...\n"
            
            if len(resources) > 20:
                if language == 'ru':
                    response += f"\n... и еще {len(resources) - 20} ресурсов"
                else:
                    response += f"\n... and {len(resources) - 20} more resources"
        else:
            if language == 'ru':
                response = "❌ Ресурсы не найдены"
            else:
                response = "❌ No resources found"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute help command."""
        if language == 'ru':
            help_text = (
                "🆘 **Справка по командам**\n\n"
                "**Поиск:**\n"
                "• 'найди Python код'\n"
                "• 'покажи все документы'\n\n"
                "**Создание:**\n"
                "• 'создай папку для проектов'\n"
                "• 'сделай архив старых файлов'\n\n"
                "**Управление:**\n"
                "• 'статистика'\n"
                "• 'экспорт данных'\n"
                "• 'помощь'\n\n"
                "💡 Просто говорите естественным языком!"
            )
        else:
            help_text = (
                "🆘 **Command Help**\n\n"
                "**Search:**\n"
                "• 'find Python code'\n"
                "• 'show all documents'\n\n"
                "**Creation:**\n"
                "• 'create project folder'\n"
                "• 'make archive for old files'\n\n"
                "**Management:**\n"
                "• 'statistics'\n"
                "• 'export data'\n"
                "• 'help'\n\n"
                "💡 Just speak naturally!"
            )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute stats command."""
        analysis = await self._analyze_content()
        
        if language == 'ru':
            response = (
                f"📊 **Статистика**\n\n"
                f"📁 Всего ресурсов: {analysis['total_resources']}\n"
                f"📂 Категорий: {analysis['total_categories']}\n"
                f"🗂 Папок: {analysis['total_folders']}\n"
                f"📦 Архивов: {analysis['total_archives']}\n\n"
            )
            
            if analysis.get('top_categories'):
                response += "**Топ категории:**\n"
                for category, count in analysis['top_categories'][:5]:
                    response += f"• {category}: {count}\n"
        else:
            response = (
                f"📊 **Statistics**\n\n"
                f"📁 Total resources: {analysis['total_resources']}\n"
                f"📂 Categories: {analysis['total_categories']}\n"
                f"🗂 Folders: {analysis['total_folders']}\n"
                f"📦 Archives: {analysis['total_archives']}\n\n"
            )
            
            if analysis.get('top_categories'):
                response += "**Top categories:**\n"
                for category, count in analysis['top_categories'][:5]:
                    response += f"• {category}: {count}\n"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute export command."""
        if language == 'ru':
            response = "📤 Функция экспорта будет доступна в следующем обновлении!"
        else:
            response = "📤 Export functionality will be available in the next update!"
        
        await update.message.reply_text(response)
    
    async def _execute_analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, language: str):
        """Execute analyze command."""
        if query:
            results = self.storage.search_resources(query)
            if results:
                if language == 'ru':
                    response = f"🔍 Найдено {len(results)} ресурсов по запросу '{query}'\n\n"
                    response += "📊 Краткий анализ найденного контента будет добавлен в следующем обновлении."
                else:
                    response = f"🔍 Found {len(results)} resources for '{query}'\n\n"
                    response += "📊 Brief analysis of found content will be added in the next update."
            else:
                if language == 'ru':
                    response = f"❌ Ничего не найдено для анализа по запросу '{query}'"
                else:
                    response = f"❌ Nothing found to analyze for '{query}'"
        else:
            await self._execute_stats_command(update, context, language)
            return
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, target: str, language: str):
        """Execute delete command."""
        if language == 'ru':
            response = f"⚠️ Функция удаления '{target}' будет доступна в следующем обновлении!\n"
            response += "Для безопасности данных эта функция требует дополнительного подтверждения."
        else:
            response = f"⚠️ Delete functionality for '{target}' will be available in the next update!\n"
            response += "For data safety, this function requires additional confirmation."
        
        await update.message.reply_text(response)
    
    async def _send_search_help(self, update: Update, language: str):
        """Send search help message."""
        if language == 'ru':
            response = "🔍 Укажите что искать. Например: 'найди код на Python'"
        else:
            response = "🔍 Please specify what to search for. Example: 'find Python code'"
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
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("delete_confirm_"):
            # Extract target from callback data
            target = data.replace("delete_confirm_", "")
            
            try:
                # Perform actual deletion using storage
                success = await self.storage.delete_item(target)
                
                if success:
                    # Determine language from user context or message
                    language = 'ru' if any(ord(c) > 127 for c in query.message.text) else 'en'
                    
                    if language == 'ru':
                        response = f"✅ '{target}' успешно удален!"
                    else:
                        response = f"✅ '{target}' successfully deleted!"
                else:
                    if language == 'ru':
                        response = f"❌ Не удалось удалить '{target}'. Возможно, элемент не найден."
                    else:
                        response = f"❌ Failed to delete '{target}'. Item might not exist."
                        
            except Exception as e:
                logger.error(f"Error deleting item: {e}")
                language = 'ru' if any(ord(c) > 127 for c in query.message.text) else 'en'
                
                if language == 'ru':
                    response = f"❌ Ошибка при удалении: {str(e)}"
                else:
                    response = f"❌ Error during deletion: {str(e)}"
            
            # Edit the original message
            await query.edit_message_text(response)
            
        elif data == "delete_cancel":
            # Determine language
            language = 'ru' if any(ord(c) > 127 for c in query.message.text) else 'en'
            
            if language == 'ru':
                response = "❌ Удаление отменено."
            else:
                response = "❌ Deletion cancelled."
            
            await query.edit_message_text(response)
        
        else:
            # Handle other callback queries if needed
            logger.warning(f"Unknown callback query data: {data}")
    
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

    async def create_folder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create a virtual folder for organizing resources."""
        if not context.args:
            await update.message.reply_text(
                "📁 **Usage:** `/create_folder <folder_name> [description]`\n"
                "📁 **Использование:** `/create_folder <имя_папки> [описание]`\n\n"
                "**Examples / Примеры:**\n"
                "• `/create_folder react_projects React проекты и компоненты`\n"
                "• `/create_folder design_resources UI/UX дизайн ресурсы`"
            )
            return
        
        folder_name = context.args[0]
        description = ' '.join(context.args[1:]) if len(context.args) > 1 else f"Папка для {folder_name}"
        
        try:
            # Create folder as a special resource
            folder_id = self.storage.create_folder(
                name=folder_name,
                description=description,
                user_id=update.effective_user.id,
                username=update.effective_user.username
            )
            
            await update.message.reply_text(
                f"📁 **Folder created successfully!**\n\n"
                f"📂 **Name:** {folder_name}\n"
                f"📝 **Description:** {description}\n"
                f"🆔 **ID:** {folder_id}\n\n"
                f"📁 **Папка успешно создана!**\n"
                f"Используйте `/add_to_folder {folder_id}` для добавления ресурсов",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            await update.message.reply_text(
                "❌ Error creating folder. Please try again.\n"
                "❌ Ошибка создания папки. Попробуйте еще раз."
            )
    
    async def create_archive_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create an archive from selected resources."""
        if not context.args:
            await update.message.reply_text(
                "📦 **Usage:** `/create_archive <archive_name> [resource_ids...]`\n"
                "📦 **Использование:** `/create_archive <имя_архива> [id_ресурсов...]`\n\n"
                "**Examples / Примеры:**\n"
                "• `/create_archive web_dev_2024 abc123 def456 ghi789`\n"
                "• `/create_archive react_components` (создаст архив из последних React ресурсов)"
            )
            return
        
        archive_name = context.args[0]
        resource_ids = context.args[1:] if len(context.args) > 1 else []
        
        try:
            # If no specific IDs provided, use smart selection
            if not resource_ids:
                resource_ids = await self._smart_select_resources_for_archive(archive_name)
            
            archive_id = self.storage.create_archive(
                name=archive_name,
                resource_ids=resource_ids,
                user_id=update.effective_user.id,
                username=update.effective_user.username
            )
            
            await update.message.reply_text(
                f"📦 **Archive created successfully!**\n\n"
                f"📂 **Name:** {archive_name}\n"
                f"📊 **Resources:** {len(resource_ids)}\n"
                f"🆔 **ID:** {archive_id}\n\n"
                f"📦 **Архив успешно создан!**\n"
                f"Используйте `/export_archive {archive_id}` для скачивания",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error creating archive: {e}")
            await update.message.reply_text(
                "❌ Error creating archive. Please try again.\n"
                "❌ Ошибка создания архива. Попробуйте еще раз."
            )
    
    async def find_folder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Find folders and archives by name or content."""
        if not context.args:
            await update.message.reply_text(
                "🔍 **Usage:** `/find_folder <search_query>`\n"
                "🔍 **Использование:** `/find_folder <поисковый_запрос>`\n\n"
                "**Examples / Примеры:**\n"
                "• `/find_folder react`\n"
                "• `/find_folder дизайн`\n"
                "• `/find_folder web development`"
            )
            return
        
        query = ' '.join(context.args)
        
        try:
            folders = self.storage.find_folders(query)
            archives = self.storage.find_archives(query)
            
            if folders or archives:
                response = f"🔍 **Search Results for '{query}':**\n\n"
                
                if folders:
                    response += "📁 **Folders:**\n"
                    for folder in folders[:5]:
                        response += f"• {folder['name']} - {folder['description'][:50]}...\n"
                        response += f"  🆔 ID: {folder['id']} | 📊 Items: {folder.get('item_count', 0)}\n\n"
                
                if archives:
                    response += "📦 **Archives:**\n"
                    for archive in archives[:5]:
                        response += f"• {archive['name']} - {archive.get('description', 'Archive')[:50]}...\n"
                        response += f"  🆔 ID: {archive['id']} | 📊 Items: {len(archive.get('resource_ids', []))}\n\n"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    f"❌ No folders or archives found for '{query}'.\n"
                    f"❌ Папки или архивы по запросу '{query}' не найдены."
                )
                
        except Exception as e:
            logger.error(f"Error finding folders: {e}")
            await update.message.reply_text(
                "❌ Search error. Please try again.\n"
                "❌ Ошибка поиска. Попробуйте еще раз."
            )
    
    async def smart_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced search with AI-powered understanding."""
        if not context.args:
            await update.message.reply_text(
                "🧠 **Usage:** `/smart_search <natural_language_query>`\n"
                "🧠 **Использование:** `/smart_search <запрос_на_естественном_языке>`\n\n"
                "**Examples / Примеры:**\n"
                "• `/smart_search найди все React компоненты с хуками`\n"
                "• `/smart_search show me Python tutorials for beginners`\n"
                "• `/smart_search дизайн системы для мобильных приложений`"
            )
            return
        
        query = ' '.join(context.args)
        
        try:
            # Show processing indicator
            status_msg = await update.message.reply_text("🧠 Analyzing query / Анализирую запрос...")
            
            # Use AI to understand and enhance the query
            enhanced_query = await self._enhance_search_query(query)
            
            # Perform enhanced search
            results = await self._perform_smart_search(enhanced_query)
            
            await status_msg.delete()
            
            if results:
                response = f"🧠 **Smart Search Results for '{query}':**\n\n"
                
                for i, result in enumerate(results[:8], 1):
                    relevance = result.get('relevance_score', 0.0)
                    response += (
                        f"{i}. **{result['category']}** - {result['description'][:80]}...\n"
                        f"   🎯 Relevance: {relevance:.1f}/10 | 🆔 ID: {result['id']}\n\n"
                    )
                
                if len(results) > 8:
                    response += f"... and {len(results) - 8} more results\n\n"
                
                response += f"📊 Found {len(results)} relevant results"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    f"❌ No relevant results found for '{query}'.\n"
                    f"❌ Релевантные результаты по запросу '{query}' не найдены."
                )
                
        except Exception as e:
            logger.error(f"Error in smart search: {e}")
            await update.message.reply_text(
                "❌ Smart search error. Please try again.\n"
                "❌ Ошибка умного поиска. Попробуйте еще раз."
            )
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analyze and provide insights about stored content."""
        try:
            # Show processing indicator
            status_msg = await update.message.reply_text("📊 Analyzing content / Анализирую контент...")
            
            # Get comprehensive analysis
            analysis = await self._perform_content_analysis()
            
            await status_msg.delete()
            
            response = (
                "📊 **Content Analysis / Анализ контента:**\n\n"
                f"📂 **Total Resources / Всего ресурсов:** {analysis['total_resources']}\n"
                f"🏷️ **Categories / Категорий:** {analysis['total_categories']}\n"
                f"📁 **Folders / Папок:** {analysis['total_folders']}\n"
                f"📦 **Archives / Архивов:** {analysis['total_archives']}\n\n"
            )
            
            # Top categories
            if analysis.get('top_categories'):
                response += "🔝 **Top Categories / Топ категории:**\n"
                for category, count in analysis['top_categories'][:5]:
                    response += f"• {category}: {count}\n"
                response += "\n"
            
            # Technology insights
            if analysis.get('technologies'):
                response += "💻 **Technologies Found / Найденные технологии:**\n"
                for tech, count in analysis['technologies'][:8]:
                    response += f"• {tech}: {count}\n"
                response += "\n"
            
            # Recommendations
            if analysis.get('recommendations'):
                response += "💡 **Recommendations / Рекомендации:**\n"
                for rec in analysis['recommendations'][:3]:
                    response += f"• {rec}\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            await update.message.reply_text(
                "❌ Analysis error. Please try again.\n"
                "❌ Ошибка анализа. Попробуйте еще раз."
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
    
    async def _smart_select_resources_for_archive(self, archive_name: str) -> list:
        """Smart selection of resources for archive based on name."""
        try:
            # Extract keywords from archive name
            keywords = archive_name.lower().replace('_', ' ').split()
            
            # Search for relevant resources
            all_resources = self.storage.get_all_resources()
            selected = []
            
            for resource in all_resources:
                score = 0
                content_lower = resource['content'].lower()
                desc_lower = resource['description'].lower()
                category_lower = resource['category'].lower()
                
                # Score based on keyword matches
                for keyword in keywords:
                    if keyword in content_lower:
                        score += 3
                    if keyword in desc_lower:
                        score += 2
                    if keyword in category_lower:
                        score += 4
                
                # Include if score is high enough
                if score >= 2:
                    selected.append(resource['id'])
            
            # Limit to 20 most recent if too many
            if len(selected) > 20:
                selected = selected[-20:]
            
            return selected
            
        except Exception as e:
            logger.error(f"Error in smart resource selection: {e}")
            return []
    
    async def _enhance_search_query(self, query: str) -> dict:
        """Use AI to enhance and understand search query."""
        try:
            # Create enhanced prompt for query understanding
            prompt = f"""
Analyze this search query and extract key information:
Query: "{query}"

Provide a JSON response with:
{{
    "keywords": ["list", "of", "key", "terms"],
    "categories": ["relevant", "categories"],
    "technologies": ["mentioned", "technologies"],
    "intent": "what user is looking for",
    "language": "detected language (en/ru)",
    "filters": {{
        "file_types": ["if", "specific", "types"],
        "difficulty": "beginner/intermediate/advanced or null",
        "recency": "recent/old or null"
    }}
}}

Focus on web development, design, programming topics.
"""
            
            # Try to get AI enhancement
            if self.classifier.groq_client:
                response = await self.classifier._call_groq_api(prompt)
                if response and 'keywords' in response:
                    return response
            
            # Fallback to simple keyword extraction
            return {
                "keywords": query.lower().split(),
                "categories": [],
                "technologies": self._extract_technologies_from_text(query),
                "intent": "search",
                "language": "ru" if any(ord(c) > 127 for c in query) else "en",
                "filters": {}
            }
            
        except Exception as e:
            logger.error(f"Error enhancing search query: {e}")
            return {"keywords": query.lower().split(), "categories": [], "technologies": [], "intent": "search", "language": "en", "filters": {}}
    
    async def _perform_smart_search(self, enhanced_query: dict) -> list:
        """Perform enhanced search using AI-processed query."""
        try:
            all_resources = self.storage.get_all_resources()
            scored_results = []
            
            keywords = enhanced_query.get('keywords', [])
            categories = enhanced_query.get('categories', [])
            technologies = enhanced_query.get('technologies', [])
            
            for resource in all_resources:
                score = 0
                content_lower = resource['content'].lower()
                desc_lower = resource['description'].lower()
                category_lower = resource['category'].lower()
                
                # Keyword matching
                for keyword in keywords:
                    if keyword in content_lower:
                        score += 2
                    if keyword in desc_lower:
                        score += 3
                    if keyword in category_lower:
                        score += 4
                
                # Category matching
                for category in categories:
                    if category.lower() in category_lower:
                        score += 5
                
                # Technology matching
                for tech in technologies:
                    if tech.lower() in content_lower or tech.lower() in desc_lower:
                        score += 3
                
                # URL bonus for web development content
                if any(url_indicator in content_lower for url_indicator in ['http', 'www', '.com', '.org', 'github']):
                    score += 1
                
                if score > 0:
                    # Calculate relevance score (0-10)
                    relevance = min(10, score)
                    
                    result = resource.copy()
                    result['relevance_score'] = relevance
                    scored_results.append(result)
            
            # Sort by relevance score
            scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return scored_results
            
        except Exception as e:
            logger.error(f"Error in smart search: {e}")
            return []
    
    async def _perform_content_analysis(self) -> dict:
        """Perform comprehensive analysis of stored content."""
        try:
            all_resources = self.storage.get_all_resources()
            folders = self.storage.get_all_folders()
            archives = self.storage.get_all_archives()
            
            # Basic statistics
            analysis = {
                'total_resources': len(all_resources),
                'total_categories': len(set(r['category'] for r in all_resources)),
                'total_folders': len(folders),
                'total_archives': len(archives)
            }
            
            # Category analysis
            category_counts = {}
            for resource in all_resources:
                category = resource['category']
                category_counts[category] = category_counts.get(category, 0) + 1
            
            analysis['top_categories'] = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Technology analysis
            tech_counts = {}
            tech_patterns = {
                'React': ['react', 'jsx', 'hooks'],
                'Vue': ['vue', 'vuejs'],
                'Angular': ['angular', 'typescript'],
                'Python': ['python', 'django', 'flask'],
                'JavaScript': ['javascript', 'js', 'node'],
                'CSS': ['css', 'sass', 'scss'],
                'HTML': ['html', 'html5'],
                'Docker': ['docker', 'container'],
                'Git': ['git', 'github', 'gitlab'],
                'API': ['api', 'rest', 'graphql'],
                'Database': ['sql', 'mongodb', 'postgres'],
                'Design': ['figma', 'sketch', 'ui', 'ux']
            }
            
            for resource in all_resources:
                content_lower = resource['content'].lower()
                for tech, patterns in tech_patterns.items():
                    if any(pattern in content_lower for pattern in patterns):
                        tech_counts[tech] = tech_counts.get(tech, 0) + 1
            
            analysis['technologies'] = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Generate recommendations
            recommendations = []
            
            if analysis['total_resources'] > 50:
                recommendations.append("Consider creating more specific folders to organize your resources")
            
            if len(analysis['top_categories']) > 10:
                recommendations.append("You have many categories - consider consolidating similar ones")
            
            if any(count > 20 for _, count in analysis['top_categories'][:3]):
                recommendations.append("Create archives for your most popular categories")
            
            analysis['recommendations'] = recommendations
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in content analysis: {e}")
            return {'total_resources': 0, 'total_categories': 0, 'total_folders': 0, 'total_archives': 0}
    
    def _extract_technologies_from_text(self, text: str) -> list:
        """Extract technology names from text."""
        technologies = []
        text_lower = text.lower()
        
        tech_keywords = {
            'react', 'vue', 'angular', 'python', 'javascript', 'typescript',
            'css', 'html', 'sass', 'scss', 'node', 'express', 'django',
            'flask', 'docker', 'kubernetes', 'git', 'github', 'api', 'rest',
            'graphql', 'sql', 'mongodb', 'postgres', 'figma', 'sketch',
            'photoshop', 'illustrator', 'ui', 'ux', 'design', 'frontend',
            'backend', 'fullstack', 'mobile', 'ios', 'android', 'swift',
            'kotlin', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust'
        }
        
        for tech in tech_keywords:
            if tech in text_lower:
                technologies.append(tech.capitalize())
        
        return list(set(technologies))
    
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
                    await self._execute_search_command(update, context, query, language)
                else:
                    await self._send_search_help(update, language)
            
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
                category = parameters.get('category', '')
                await self._execute_list_command(update, context, category, language)
            
            elif command_type == CommandType.HELP:
                await self._execute_help_command(update, context, language)
            
            elif command_type == CommandType.STATS:
                await self._execute_stats_command(update, context, language)
            
            elif command_type == CommandType.EXPORT:
                await self._execute_export_command(update, context, language)
            
            elif command_type == CommandType.ANALYZE:
                query = parameters.get('query', '')
                await self._execute_analyze_command(update, context, query, language)
            
            elif command_type == CommandType.DELETE:
                target = parameters.get('target', '')
                await self._execute_delete_command(update, context, target, language)
            
            await status_msg.delete()
            
        except Exception as e:
            logger.error(f"Error handling command intent: {e}")
            error_msg = "❌ Ошибка выполнения команды" if language == 'ru' else "❌ Command execution error"
            await update.message.reply_text(error_msg)
    
    async def _execute_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, language: str):
        """Execute search command."""
        results = self.storage.search_resources(query)
        
        if results:
            if language == 'ru':
                response = f"🔍 **Результаты поиска для '{query}':**\n\n"
            else:
                response = f"🔍 **Search results for '{query}':**\n\n"
            
            for i, result in enumerate(results[:10], 1):
                response += f"{i}. **{result['category']}** - {result['description'][:100]}...\n"
                response += f"   🆔 ID: {result['id']}\n\n"
            
            if len(results) > 10:
                if language == 'ru':
                    response += f"... и еще {len(results) - 10} результатов\n"
                else:
                    response += f"... and {len(results) - 10} more results\n"
        else:
            if language == 'ru':
                response = f"❌ Ничего не найдено по запросу '{query}'"
            else:
                response = f"❌ No results found for '{query}'"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_create_folder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, folder_name: str, language: str):
        """Execute create folder command."""
        try:
            folder_id = self.storage.create_folder(folder_name, update.effective_user.id)
            
            if language == 'ru':
                response = f"✅ Папка '{folder_name}' создана успешно!\n🆔 ID: {folder_id}"
            else:
                response = f"✅ Folder '{folder_name}' created successfully!\n🆔 ID: {folder_id}"
            
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            if language == 'ru':
                response = f"❌ Ошибка создания папки '{folder_name}'"
            else:
                response = f"❌ Error creating folder '{folder_name}'"
            await update.message.reply_text(response)
    
    async def _execute_create_archive_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, archive_name: str, language: str):
        """Execute create archive command."""
        try:
            archive_id = self.storage.create_archive(archive_name, update.effective_user.id)
            
            if language == 'ru':
                response = f"✅ Архив '{archive_name}' создан успешно!\n🆔 ID: {archive_id}"
            else:
                response = f"✅ Archive '{archive_name}' created successfully!\n🆔 ID: {archive_id}"
            
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error creating archive: {e}")
            if language == 'ru':
                response = f"❌ Ошибка создания архива '{archive_name}'"
            else:
                response = f"❌ Error creating archive '{archive_name}'"
            await update.message.reply_text(response)
    
    async def _execute_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, language: str):
        """Execute list command."""
        if category:
            resources = self.storage.get_resources_by_category(category)
            if language == 'ru':
                title = f"📋 Ресурсы в категории '{category}':"
            else:
                title = f"📋 Resources in category '{category}':"
        else:
            resources = self.storage.get_all_resources()
            if language == 'ru':
                title = "📋 Все ресурсы:"
            else:
                title = "📋 All resources:"
        
        if resources:
            response = f"**{title}**\n\n"
            for i, resource in enumerate(resources[:20], 1):
                response += f"{i}. **{resource['category']}** - {resource['description'][:80]}...\n"
            
            if len(resources) > 20:
                if language == 'ru':
                    response += f"\n... и еще {len(resources) - 20} ресурсов"
                else:
                    response += f"\n... and {len(resources) - 20} more resources"
        else:
            if language == 'ru':
                response = "❌ Ресурсы не найдены"
            else:
                response = "❌ No resources found"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute help command."""
        if language == 'ru':
            help_text = (
                "🆘 **Справка по командам**\n\n"
                "**Поиск:**\n"
                "• 'найди Python код'\n"
                "• 'покажи все документы'\n\n"
                "**Создание:**\n"
                "• 'создай папку для проектов'\n"
                "• 'сделай архив старых файлов'\n\n"
                "**Управление:**\n"
                "• 'статистика'\n"
                "• 'экспорт данных'\n"
                "• 'помощь'\n\n"
                "💡 Просто говорите естественным языком!"
            )
        else:
            help_text = (
                "🆘 **Command Help**\n\n"
                "**Search:**\n"
                "• 'find Python code'\n"
                "• 'show all documents'\n\n"
                "**Creation:**\n"
                "• 'create project folder'\n"
                "• 'make archive for old files'\n\n"
                "**Management:**\n"
                "• 'statistics'\n"
                "• 'export data'\n"
                "• 'help'\n\n"
                "💡 Just speak naturally!"
            )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute stats command."""
        analysis = await self._analyze_content()
        
        if language == 'ru':
            response = (
                f"📊 **Статистика**\n\n"
                f"📁 Всего ресурсов: {analysis['total_resources']}\n"
                f"📂 Категорий: {analysis['total_categories']}\n"
                f"🗂 Папок: {analysis['total_folders']}\n"
                f"📦 Архивов: {analysis['total_archives']}\n\n"
            )
            
            if analysis.get('top_categories'):
                response += "**Топ категории:**\n"
                for category, count in analysis['top_categories'][:5]:
                    response += f"• {category}: {count}\n"
        else:
            response = (
                f"📊 **Statistics**\n\n"
                f"📁 Total resources: {analysis['total_resources']}\n"
                f"📂 Categories: {analysis['total_categories']}\n"
                f"🗂 Folders: {analysis['total_folders']}\n"
                f"📦 Archives: {analysis['total_archives']}\n\n"
            )
            
            if analysis.get('top_categories'):
                response += "**Top categories:**\n"
                for category, count in analysis['top_categories'][:5]:
                    response += f"• {category}: {count}\n"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Execute export command."""
        if language == 'ru':
            response = "📤 Функция экспорта будет доступна в следующем обновлении!"
        else:
            response = "📤 Export functionality will be available in the next update!"
        
        await update.message.reply_text(response)
    
    async def _execute_analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, language: str):
        """Execute analyze command."""
        if query:
            results = self.storage.search_resources(query)
            if results:
                if language == 'ru':
                    response = f"🔍 Найдено {len(results)} ресурсов по запросу '{query}'\n\n"
                    response += "📊 Краткий анализ найденного контента будет добавлен в следующем обновлении."
                else:
                    response = f"🔍 Found {len(results)} resources for '{query}'\n\n"
                    response += "📊 Brief analysis of found content will be added in the next update."
            else:
                if language == 'ru':
                    response = f"❌ Ничего не найдено для анализа по запросу '{query}'"
                else:
                    response = f"❌ Nothing found to analyze for '{query}'"
        else:
            await self._execute_stats_command(update, context, language)
            return
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _execute_delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, target: str, language: str):
        """Execute delete command."""
        if language == 'ru':
            response = f"⚠️ Функция удаления '{target}' будет доступна в следующем обновлении!\n"
            response += "Для безопасности данных эта функция требует дополнительного подтверждения."
        else:
            response = f"⚠️ Delete functionality for '{target}' will be available in the next update!\n"
            response += "For data safety, this function requires additional confirmation."
        
        await update.message.reply_text(response)
    
    async def _send_search_help(self, update: Update, language: str):
        """Send search help message."""
        if language == 'ru':
            response = "🔍 Укажите что искать. Например: 'найди код на Python'"
        else:
            response = "🔍 Please specify what to search for. Example: 'find Python code'"
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
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("delete_confirm_"):
            # Extract target from callback data
            target = data.replace("delete_confirm_", "")
            
            try:
                # Perform actual deletion using storage
                success = await self.storage.delete_item(target)
                
                if success:
                    # Determine language from user context or message
                    language = 'ru' if any(ord(c) > 127 for c in query.message.text) else 'en'
                    
                    if language == 'ru':
                        response = f"✅ '{target}' успешно удален!"
                    else:
                        response = f"✅ '{target}' successfully deleted!"
                else:
                    if language == 'ru':
                        response = f"❌ Не удалось удалить '{target}'. Возможно, элемент не найден."
                    else:
                        response = f"❌ Failed to delete '{target}'. Item might not exist."
                        
            except Exception as e:
                logger.error(f"Error deleting item: {e}")
                language = 'ru' if any(ord(c) > 127 for c in query.message.text) else 'en'
                
                if language == 'ru':
                    response = f"❌ Ошибка при удалении: {str(e)}"
                else:
                    response = f"❌ Error during deletion: {str(e)}"
            
            # Edit the original message
            await query.edit_message_text(response)
            
        elif data == "delete_cancel":
            # Determine language
            language = 'ru' if any(ord(c) > 127 for c in query.message.text) else 'en'
            
            if language == 'ru':
                response = "❌ Удаление отменено."
            else:
                response = "❌ Deletion cancelled."
            
            await query.edit_message_text(response)
        
        else:
            # Handle other callback queries if needed
            logger.warning(f"Unknown callback query data: {data}")