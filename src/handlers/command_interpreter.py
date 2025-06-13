#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intelligent command interpreter for natural language commands in Russian and English.
Enhanced version with improved Russian language understanding.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CommandType(Enum):
    """Types of commands that can be recognized."""
    SEARCH = "search"
    SEMANTIC_SEARCH = "semantic_search"
    CREATE_FOLDER = "create_folder"
    CREATE_ARCHIVE = "create_archive"
    LIST = "list"
    HELP = "help"
    STATS = "stats"
    EXPORT = "export"
    ANALYZE = "analyze"
    DELETE = "delete"
    UNKNOWN = "unknown"

@dataclass
class CommandIntent:
    """Represents a recognized command intent."""
    command_type: CommandType
    parameters: Dict[str, Any]
    confidence: float
    original_text: str
    language: str = "ru"

class NaturalLanguageCommandInterpreter:
    """Interprets natural language commands using AI and enhanced pattern matching."""
    
    def __init__(self, classifier=None):
        """Initialize the command interpreter."""
        self.classifier = classifier
        self._init_patterns()
        self._init_synonyms()
        self._init_context_words()
    
    def _init_patterns(self):
        """Initialize enhanced command patterns for different languages."""
        self.command_patterns = {
            # Enhanced Search patterns with more variations and time filters
            CommandType.SEARCH: {
                'ru': [
                    r'(найди|найти|поиск|ищи|искать|покажи|показать|отыщи|разыщи)\s+(.+)',
                    r'где\s+(.+)\?*',
                    r'есть\s+ли\s+(.+)\?*',
                    r'что\s+у\s+(тебя|меня)\s+есть\s+про\s+(.+)\?*',
                    r'дай\s+мне\s+(.+)',
                    r'хочу\s+(найти|посмотреть)\s+(.+)',
                    r'мне\s+нужно\s+(найти\s+)*(.+)',
                    r'можешь\s+(найти|показать)\s+(.+)\?*',
                    r'поищи\s+(.+)',
                    r'найдется\s+ли\s+(.+)\?*',
                    r'у\s+тебя\s+есть\s+(.+)\?*',
                    r'ищу\s+(.+)',
                    r'нужен\s+(.+)',
                    r'нужна\s+(.+)',
                    r'нужно\s+(.+)',
                    r'требуется\s+(.+)',
                    r'интересует\s+(.+)',
                    r'хотел\s+бы\s+(найти|посмотреть)\s+(.+)',
                    # Complex queries with time filters
                    r'(найди|покажи)\s+(все\s+)*(.+?)\s+(за\s+)*(последний|последние|последнюю)\s+(день|неделю|месяц|год|дни|недели|месяцы|года)',
                    r'(найди|покажи)\s+(все\s+)*(.+?)\s+(с\s+)*(начала\s+)*(недели|месяца|года)',
                    r'(найди|покажи)\s+(все\s+)*(.+?)\s+(старше|новее)\s+(\d+)\s+(дней|недель|месяцев|лет)',
                    r'(найди|покажи)\s+(все\s+)*(.+?)\s+(до|после)\s+([\d\.\-\/]+)',
                    r'(найди|покажи)\s+(все\s+)*(.+?)\s+(категории|типа)\s+(.+)',
                ],
                'en': [
                    r'(find|search|look|show|get|locate)\s+(.+)',
                    r'where\s+(.+)\?*',
                    r'do\s+you\s+have\s+(.+)\?*',
                    r'i\s+need\s+(.+)',
                    r'show\s+me\s+(.+)',
                    r'can\s+you\s+(find|show)\s+(.+)\?*',
                    r'looking\s+for\s+(.+)',
                    # Complex queries with time filters
                    r'(find|show)\s+(all\s+)*(.+?)\s+(from\s+)*(last|past)\s+(day|week|month|year|days|weeks|months|years)',
                    r'(find|show)\s+(all\s+)*(.+?)\s+(since\s+)*(beginning\s+of\s+)*(week|month|year)',
                    r'(find|show)\s+(all\s+)*(.+?)\s+(older|newer)\s+than\s+(\d+)\s+(days|weeks|months|years)',
                    r'(find|show)\s+(all\s+)*(.+?)\s+(before|after)\s+([\d\.\-\/]+)',
                    r'(find|show)\s+(all\s+)*(.+?)\s+(of\s+type|category)\s+(.+)',
                ]
            },
            
            # Semantic search patterns
            CommandType.SEMANTIC_SEARCH: {
                'ru': [
                    r'семантический\s+поиск\s+(.+)',
                    r'умный\s+поиск\s+(.+)',
                    r'найди\s+похожее\s+на\s+(.+)',
                    r'поиск\s+по\s+смыслу\s+(.+)',
                    r'ищи\s+семантически\s+(.+)',
                    r'найди\s+по\s+значению\s+(.+)',
                    r'интеллектуальный\s+поиск\s+(.+)',
                    r'смысловой\s+поиск\s+(.+)',
                    r'найди\s+связанное\s+с\s+(.+)',
                    r'поиск\s+по\s+контексту\s+(.+)',
                ],
                'en': [
                    r'semantic\s+search\s+(.+)',
                    r'smart\s+search\s+(.+)',
                    r'find\s+similar\s+to\s+(.+)',
                    r'search\s+by\s+meaning\s+(.+)',
                    r'intelligent\s+search\s+(.+)',
                    r'contextual\s+search\s+(.+)',
                    r'find\s+related\s+to\s+(.+)',
                ]
            },
            
            # Enhanced Create folder patterns
            CommandType.CREATE_FOLDER: {
                'ru': [
                    r'создай\s+(папку|директорию|каталог)\s+(.+)',
                    r'сделай\s+(папку|директорию)\s+(.+)',
                    r'(новая|новый)\s+(папка|директория|каталог)\s+(.+)',
                    r'создать\s+(папку|директорию)\s+(.+)',
                    r'добавь\s+(папку|директорию)\s+(.+)',
                    r'организуй\s+(папку|директорию)\s+(.+)',
                    r'заведи\s+(папку|директорию)\s+(.+)',
                    r'нужна\s+(папка|директория)\s+(.+)',
                    r'хочу\s+(папку|директорию)\s+(.+)',
                ],
                'en': [
                    r'create\s+(folder|directory)\s+(.+)',
                    r'make\s+(folder|directory)\s+(.+)',
                    r'new\s+(folder|directory)\s+(.+)',
                    r'add\s+(folder|directory)\s+(.+)',
                ]
            },
            
            # Enhanced Create archive patterns
            CommandType.CREATE_ARCHIVE: {
                'ru': [
                    r'создай\s+архив\s+(.+)',
                    r'сделай\s+архив\s+(.+)',
                    r'новый\s+архив\s+(.+)',
                    r'заархивируй\s+(.+)',
                    r'упакуй\s+(в\s+архив\s+)*(.+)',
                    r'сожми\s+(в\s+архив\s+)*(.+)',
                    r'архивируй\s+(.+)',
                    r'нужен\s+архив\s+(.+)',
                ],
                'en': [
                    r'create\s+archive\s+(.+)',
                    r'make\s+archive\s+(.+)',
                    r'new\s+archive\s+(.+)',
                    r'archive\s+(.+)',
                    r'compress\s+(.+)',
                ]
            },
            
            # Enhanced List patterns
            CommandType.LIST: {
                'ru': [
                    r'покажи\s+(все\s+)*(.*)\s*',
                    r'список\s*(.*)\s*',
                    r'что\s+у\s+меня\s+есть\s*(.*)\s*',
                    r'мои\s+(.+)',
                    r'все\s+(.+)',
                    r'перечисли\s*(.*)\s*',
                    r'выведи\s+(список\s+)*(.*)\s*',
                    r'отобрази\s*(.*)\s*',
                    r'просмотр\s*(.*)\s*',
                    r'содержимое\s*(.*)\s*',
                    r'инвентарь\s*(.*)\s*',
                ],
                'en': [
                    r'show\s+(all\s+)*(.*)\s*',
                    r'list\s*(.*)\s*',
                    r'what\s+do\s+i\s+have\s*(.*)\s*',
                    r'my\s+(.+)',
                    r'all\s+(.+)',
                    r'display\s*(.*)\s*',
                ]
            },
            
            # Enhanced Help patterns
            CommandType.HELP: {
                'ru': [
                    r'помощь',
                    r'справка',
                    r'что\s+ты\s+умеешь\?*',
                    r'как\s+(пользоваться|работать)\?*',
                    r'команды',
                    r'help',
                    r'инструкция',
                    r'руководство',
                    r'подсказка',
                    r'как\s+дела\?*',
                    r'что\s+можешь\?*',
                    r'возможности',
                    r'функции',
                    r'что\s+делать\?*',
                    r'не\s+понимаю',
                    r'объясни',
                ],
                'en': [
                    r'help',
                    r'what\s+can\s+you\s+do\?*',
                    r'how\s+to\s+use\?*',
                    r'commands',
                    r'instructions',
                    r'guide',
                ]
            },
            
            # Enhanced Stats patterns
            CommandType.STATS: {
                'ru': [
                    r'статистика',
                    r'статы',
                    r'сколько\s+у\s+меня\s+(.+)\?*',
                    r'количество\s*(.*)\s*',
                    r'подсчет\s*(.*)\s*',
                    r'итоги\s*(.*)\s*',
                    r'отчет\s*(.*)\s*',
                    r'сводка\s*(.*)\s*',
                    r'аналитика\s*(.*)\s*',
                    r'метрики\s*(.*)\s*',
                ],
                'en': [
                    r'stats',
                    r'statistics',
                    r'how\s+many\s+(.+)\?*',
                    r'count\s*(.*)\s*',
                    r'metrics\s*(.*)\s*',
                    r'analytics\s*(.*)\s*',
                ]
            },
            
            # Enhanced Export patterns
            CommandType.EXPORT: {
                'ru': [
                    r'экспорт\s*(.*)\s*',
                    r'экспортировать\s*(.*)\s*',
                    r'скачать\s+(все\s+)*(.*)\s*',
                    r'выгрузить\s+(данные\s+)*(.*)\s*',
                    r'сохранить\s+(все\s+)*(.*)\s*',
                    r'бэкап\s*(.*)\s*',
                    r'резервная\s+копия\s*(.*)\s*',
                    r'дамп\s*(.*)\s*',
                ],
                'en': [
                    r'export\s*(.*)\s*',
                    r'download\s+(all\s+)*(.*)\s*',
                    r'backup\s*(.*)\s*',
                    r'save\s+(all\s+)*(.*)\s*',
                ]
            },
            
            # Enhanced Analyze patterns
            CommandType.ANALYZE: {
                'ru': [
                    r'анализ\s*(.*)\s*',
                    r'проанализируй\s+(.+)',
                    r'что\s+это\s+за\s+(.+)\?*',
                    r'расскажи\s+про\s+(.+)',
                    r'изучи\s+(.+)',
                    r'разбери\s+(.+)',
                    r'исследуй\s+(.+)',
                    r'посмотри\s+на\s+(.+)',
                    r'оцени\s+(.+)',
                    r'проверь\s+(.+)',
                ],
                'en': [
                    r'analyze\s*(.*)\s*',
                    r'what\s+is\s+(.+)\?*',
                    r'tell\s+me\s+about\s+(.+)',
                    r'examine\s+(.+)',
                    r'study\s+(.+)',
                ]
            },
            
            # Enhanced Delete patterns
            CommandType.DELETE: {
                'ru': [
                    r'удали\s+(.+)',
                    r'удалить\s+(.+)',
                    r'убери\s+(.+)',
                    r'стереть\s+(.+)',
                    r'очисти\s+(.+)',
                    r'снеси\s+(.+)',
                    r'уничтожь\s+(.+)',
                    r'избавься\s+от\s+(.+)',
                    r'выкинь\s+(.+)',
                    r'сотри\s+(.+)',
                ],
                'en': [
                    r'delete\s+(.+)',
                    r'remove\s+(.+)',
                    r'erase\s+(.+)',
                    r'clear\s+(.+)',
                ]
            }
        }
    
        # Keywords for language detection (expanded)
        self.russian_keywords = {
            'найди', 'найти', 'поиск', 'ищи', 'искать', 'покажи', 'показать',
            'создай', 'сделай', 'новая', 'новый', 'папку', 'архив',
            'список', 'все', 'мои', 'помощь', 'справка', 'что', 'как',
            'статистика', 'экспорт', 'анализ', 'удали', 'удалить',
            'где', 'есть', 'дай', 'мне', 'нужно', 'хочу', 'можешь',
            'поищи', 'ищу', 'нужен', 'нужна', 'требуется', 'интересует',
            'перечисли', 'выведи', 'отобрази', 'инструкция', 'руководство',
            'количество', 'сколько', 'подсчет', 'итоги', 'отчет',
            'скачать', 'выгрузить', 'сохранить', 'бэкап', 'проанализируй',
            'расскажи', 'изучи', 'разбери', 'убери', 'стереть', 'очисти'
        }
    
    def detect_language(self, text: str) -> str:
        """Enhanced language detection."""
        text_lower = text.lower()
        words = text_lower.split()
        
        # Count Russian keywords
        russian_words = sum(1 for word in words if word in self.russian_keywords)
        
        # Check for Cyrillic characters
        cyrillic_chars = len(re.findall(r'[а-яё]', text_lower))
        
        # If more than 25% of words are Russian keywords or has Cyrillic, consider it Russian
        total_words = len(words)
        if total_words > 0:
            russian_ratio = russian_words / total_words
            if russian_ratio > 0.25 or cyrillic_chars > 2:
                return 'ru'
        
        # Check for Cyrillic characters in short texts
        if cyrillic_chars > 0:
            return 'ru'
        
        return 'en'
    
    async def interpret_command(self, text: str) -> CommandIntent:
        """Enhanced command interpretation with better Russian support."""
        text = text.strip()
        language = self.detect_language(text)
        
        # Try AI-powered interpretation first
        if self.classifier:
            ai_intent = await self._ai_interpret_command(text, language)
            if ai_intent and ai_intent.confidence > 0.7:
                return ai_intent
        
        # Enhanced pattern matching
        pattern_intent = self._enhanced_pattern_interpret_command(text, language)
        
        # If AI gave low confidence result, combine with pattern matching
        if self.classifier and ai_intent and pattern_intent.command_type != CommandType.UNKNOWN:
            if ai_intent.confidence > 0.4:
                # Merge parameters intelligently
                merged_params = {**pattern_intent.parameters, **ai_intent.parameters}
                pattern_intent.parameters = merged_params
                pattern_intent.confidence = max(pattern_intent.confidence, ai_intent.confidence)
        
        return pattern_intent
    
    async def _ai_interpret_command(self, text: str, language: str) -> Optional[CommandIntent]:
        """Enhanced AI interpretation with better Russian prompts."""
        try:
            prompt = self._create_enhanced_command_interpretation_prompt(text, language)
            
            # Use the classifier's AI capabilities
            if hasattr(self.classifier, '_call_groq_api'):
                response = await self.classifier._call_groq_api(prompt)
            elif hasattr(self.classifier, '_call_ollama_api'):
                response = await self.classifier._call_ollama_api(prompt)
            else:
                return None
            
            if response:
                import json
                result = json.loads(response)
                
                command_type = CommandType(result.get('command_type', 'unknown'))
                parameters = result.get('parameters', {})
                confidence = result.get('confidence', 0.5)
                
                return CommandIntent(
                    command_type=command_type,
                    parameters=parameters,
                    confidence=confidence,
                    original_text=text,
                    language=language
                )
        
        except Exception as e:
            logger.warning(f"AI command interpretation failed: {e}")
            return None
    
    def _create_enhanced_command_interpretation_prompt(self, text: str, language: str) -> str:
        """Create enhanced prompt for AI command interpretation."""
        if language == 'ru':
            return f"""
Ты - продвинутый интеллектуальный интерпретатор команд для русскоязычного бота-помощника разработчика.
Твоя задача - точно понять намерение пользователя из естественной речи на русском языке.

Текст пользователя: "{text}"

Доступные типы команд:
- search: поиск ресурсов, файлов, информации
- create_folder: создание папки, директории, каталога
- create_archive: создание архива, упаковка файлов
- list: показать список, перечислить ресурсы
- help: помощь, справка, инструкции
- stats: статистика, подсчет, метрики
- export: экспорт, выгрузка, сохранение данных
- analyze: анализ, изучение, исследование контента
- delete: удаление, очистка ресурсов
- unknown: неизвестная команда

Верни результат ТОЛЬКО в JSON формате:
{{
    "command_type": "тип_команды",
    "parameters": {{
        "query": "поисковый запрос или параметр",
        "name": "имя папки/архива если применимо",
        "category": "категория если указана",
        "target": "цель действия если указана"
    }},
    "confidence": 0.9
}}

Примеры:
- "найди все про Python" -> {{"command_type": "search", "parameters": {{"query": "Python"}}, "confidence": 0.9}}
- "создай папку для React проектов" -> {{"command_type": "create_folder", "parameters": {{"name": "React проекты"}}, "confidence": 0.9}}
- "покажи статистику" -> {{"command_type": "stats", "parameters": {{}}, "confidence": 0.9}}
- "удали старые файлы" -> {{"command_type": "delete", "parameters": {{"target": "старые файлы"}}, "confidence": 0.8}}
"""
        else:
            return f"""
You are an advanced intelligent command interpreter for an English-speaking developer assistant bot.
Your task is to accurately understand user intent from natural language.

User text: "{text}"

Available command types:
- search: search for resources, files, information
- create_folder: create folder, directory
- create_archive: create archive, pack files
- list: show list, enumerate resources
- help: help, instructions, guide
- stats: statistics, count, metrics
- export: export, download, save data
- analyze: analyze, study, examine content
- delete: delete, remove resources
- unknown: unknown command

Return result ONLY in JSON format:
{{
    "command_type": "command_type",
    "parameters": {{
        "query": "search query or parameter",
        "name": "folder/archive name if applicable",
        "category": "category if specified",
        "target": "action target if specified"
    }},
    "confidence": 0.9
}}
"""
    
    def _enhanced_pattern_interpret_command(self, text: str, language: str) -> CommandIntent:
        """Enhanced pattern matching with context analysis."""
        text_lower = text.lower().strip()
        
        # Pre-process text for better matching
        text_processed = self._preprocess_text(text_lower, language)
        
        # Try each command type with enhanced matching
        for command_type, patterns in self.command_patterns.items():
            lang_patterns = patterns.get(language, [])
            
            for pattern in lang_patterns:
                match = re.search(pattern, text_processed)
                if match:
                    parameters = self._enhanced_extract_parameters(match, command_type, text_lower, language)
                    confidence = self._calculate_confidence(text_lower, command_type, language)
                    
                    return CommandIntent(
                        command_type=command_type,
                        parameters=parameters,
                        confidence=confidence,
                        original_text=text,
                        language=language
                    )
        
        # Fallback: try semantic matching
        semantic_intent = self._semantic_matching(text_lower, language)
        if semantic_intent.command_type != CommandType.UNKNOWN:
            return semantic_intent
        
        # No pattern matched
        return CommandIntent(
            command_type=CommandType.UNKNOWN,
            parameters={},
            confidence=0.0,
            original_text=text,
            language=language
        )
    
    def _preprocess_text(self, text: str, language: str) -> str:
        """Preprocess text for better pattern matching."""
        # Remove punctuation except important ones
        text = re.sub(r'[^а-яёa-z0-9\s\-_]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _enhanced_extract_parameters(self, match, command_type: CommandType, text: str, language: str) -> Dict[str, Any]:
        """Enhanced parameter extraction with context analysis."""
        parameters = {}
        
        # Extract basic parameters from match groups
        if len(match.groups()) > 0:
            param_text = match.group(-1).strip()  # Last group is usually the parameter
            
            if command_type in [CommandType.SEARCH, CommandType.SEMANTIC_SEARCH, CommandType.ANALYZE]:
                # Extract time filters and categories from complex queries
                time_params = self._extract_time_filters(text, language)
                category_params = self._extract_category_filters(text, language)
                
                # For complex queries, extract the main search term
                if len(match.groups()) >= 3:
                    # Complex query pattern matched
                    main_query = match.group(3).strip() if match.group(3) else param_text
                    parameters['query'] = main_query
                else:
                    parameters['query'] = param_text
                
                # Add time filters if found
                parameters.update(time_params)
                
                # Add category filters if found
                parameters.update(category_params)
                
                # Try to detect category from context if not already found
                if 'category' not in parameters:
                    category = self._detect_category_from_text(text, language)
                    if category:
                        parameters['category'] = category
                        
                # For semantic search, add semantic flag
                if command_type == CommandType.SEMANTIC_SEARCH:
                    parameters['semantic'] = True
                    
            elif command_type in [CommandType.CREATE_FOLDER, CommandType.CREATE_ARCHIVE]:
                parameters['name'] = param_text
                
            elif command_type == CommandType.LIST:
                if param_text:
                    parameters['category'] = param_text
                    
            elif command_type == CommandType.DELETE:
                parameters['target'] = param_text
                # Try to extract ID if present
                id_match = re.search(r'\b(\d+)\b', param_text)
                if id_match:
                    parameters['id'] = id_match.group(1)
        
        return parameters
    
    def _detect_category_from_text(self, text: str, language: str) -> Optional[str]:
        """Detect category from context words."""
        context_words = self.context_words.get(language, {})
        
        for category, words in context_words.items():
            if any(word in text for word in words):
                return category
        
        return None
    
    def _calculate_confidence(self, text: str, command_type: CommandType, language: str) -> float:
        """Calculate confidence based on various factors."""
        base_confidence = 0.8 if language == 'ru' else 0.7
        
        # Boost confidence for exact keyword matches
        synonyms = self.synonyms.get(language, {})
        command_synonyms = synonyms.get(command_type.value, [])
        
        if any(synonym in text for synonym in command_synonyms):
            base_confidence += 0.1
        
        # Boost confidence for context words
        if self._detect_category_from_text(text, language):
            base_confidence += 0.05
        
        return min(base_confidence, 0.95)
    
    def _semantic_matching(self, text: str, language: str) -> CommandIntent:
        """Semantic matching using synonym analysis."""
        synonyms = self.synonyms.get(language, {})
        
        # Count matches for each command type
        command_scores = {}
        
        for command_name, command_synonyms in synonyms.items():
            score = sum(1 for synonym in command_synonyms if synonym in text)
            if score > 0:
                # Try to map command_name to CommandType
                try:
                    if command_name == 'search':
                        command_type = CommandType.SEARCH
                    elif command_name == 'semantic_search':
                        command_type = CommandType.SEMANTIC_SEARCH
                    elif command_name == 'create':
                        # Determine if folder or archive based on context
                        if any(word in text for word in synonyms.get('folder', [])):
                            command_type = CommandType.CREATE_FOLDER
                        elif any(word in text for word in synonyms.get('archive', [])):
                            command_type = CommandType.CREATE_ARCHIVE
                        else:
                            command_type = CommandType.CREATE_FOLDER  # Default
                    elif command_name == 'list':
                        command_type = CommandType.LIST
                    elif command_name == 'help':
                        command_type = CommandType.HELP
                    elif command_name == 'stats':
                        command_type = CommandType.STATS
                    elif command_name == 'export':
                        command_type = CommandType.EXPORT
                    elif command_name == 'analyze':
                        command_type = CommandType.ANALYZE
                    elif command_name == 'delete':
                        command_type = CommandType.DELETE
                    else:
                        continue
                    
                    command_scores[command_type] = score
                except:
                    continue
        
        if command_scores:
            # Get command with highest score
            best_command = max(command_scores.items(), key=lambda x: x[1])
            command_type, score = best_command
            
            # Extract basic parameters
            parameters = {}
            if command_type in [CommandType.SEARCH, CommandType.SEMANTIC_SEARCH, CommandType.ANALYZE]:
                # Try to extract query from remaining text
                query_words = [word for word in text.split() 
                             if word not in synonyms.get('search', []) 
                             and word not in synonyms.get('analyze', []) 
                             and word not in synonyms.get('semantic_search', [])]
                if query_words:
                    parameters['query'] = ' '.join(query_words)
                # For semantic search, add semantic flag
                if command_type == CommandType.SEMANTIC_SEARCH:
                    parameters['semantic'] = True
            
            confidence = min(0.6 + (score * 0.1), 0.8)
            
            return CommandIntent(
                command_type=command_type,
                parameters=parameters,
                confidence=confidence,
                original_text=text,
                language=language
            )
        
        return CommandIntent(
            command_type=CommandType.UNKNOWN,
            parameters={},
            confidence=0.0,
            original_text=text,
            language=language
        )
    
    def get_command_suggestions(self, text: str) -> List[str]:
        """Enhanced command suggestions based on partial input."""
        language = self.detect_language(text)
        suggestions = []
        
        if language == 'ru':
            base_suggestions = [
                "найди код на Python",
                "создай папку для проектов",
                "покажи все документы",
                "статистика по категориям",
                "помощь по командам",
                "экспорт всех данных",
                "проанализируй этот файл",
                "удали старые файлы",
                "список всех ресурсов",
                "создай архив проектов",
                "найди документацию по React",
                "покажи мои заметки"
            ]
        else:
            base_suggestions = [
                "find Python code",
                "create project folder",
                "show all documents",
                "stats by category",
                "help with commands",
                "export all data",
                "analyze this file",
                "delete old files",
                "list all resources",
                "create project archive"
            ]
        
        # Filter suggestions based on input
        if text:
            text_lower = text.lower()
            suggestions = [s for s in base_suggestions 
                         if any(word in s.lower() for word in text_lower.split())]
        else:
            suggestions = base_suggestions
        
        return suggestions[:8]  # Return top 8 suggestions
    
    def _init_synonyms(self):
        """Initialize synonym dictionaries for better understanding."""
        self.synonyms = {
            'ru': {
                'search': ['найди', 'найти', 'поиск', 'ищи', 'искать', 'покажи', 'показать', 'отыщи', 'разыщи', 'поищи', 'все', 'всё'],
                'semantic_search': ['семантический', 'умный', 'похожее', 'смыслу', 'семантически', 'значению', 'интеллектуальный', 'смысловой', 'связанное', 'контексту'],
                'create': ['создай', 'сделай', 'новая', 'новый', 'добавь', 'организуй', 'заведи'],
                'folder': ['папку', 'папка', 'директорию', 'директория', 'каталог'],
                'archive': ['архив', 'архивируй', 'заархивируй', 'упакуй', 'сожми'],
                'list': ['список', 'покажи', 'все', 'перечисли', 'выведи', 'отобрази'],
                'help': ['помощь', 'справка', 'инструкция', 'руководство', 'подсказка'],
                'stats': ['статистика', 'статы', 'количество', 'подсчет', 'итоги', 'отчет'],
                'export': ['экспорт', 'экспортировать', 'скачать', 'выгрузить', 'сохранить', 'бэкап'],
                'analyze': ['анализ', 'проанализируй', 'изучи', 'разбери', 'исследуй'],
                'delete': ['удали', 'удалить', 'убери', 'стереть', 'очисти', 'снеси']
            },
            'en': {
                'search': ['find', 'search', 'look', 'show', 'get', 'locate'],
                'semantic_search': ['semantic', 'smart', 'similar', 'meaning', 'intelligent', 'contextual', 'related'],
                'create': ['create', 'make', 'new', 'add'],
                'folder': ['folder', 'directory'],
                'archive': ['archive', 'compress'],
                'list': ['list', 'show', 'all', 'display'],
                'help': ['help', 'instructions', 'guide'],
                'stats': ['stats', 'statistics', 'count', 'metrics'],
                'export': ['export', 'download', 'backup', 'save'],
                'analyze': ['analyze', 'examine', 'study'],
                'delete': ['delete', 'remove', 'erase', 'clear']
            }
        }
    
    def _init_context_words(self):
        """Initialize context words for better understanding."""
        self.context_words = {
            'ru': {
                'programming': ['код', 'программа', 'скрипт', 'функция', 'класс', 'python', 'javascript', 'java', 'react', 'vue', 'angular', 'node', 'php', 'c++', 'c#', 'go', 'rust'],
                'documentation': ['документация', 'доки', 'руководство', 'инструкция', 'readme', 'туториал', 'туториалы', 'гайд', 'гайды', 'мануал'],
                'projects': ['проект', 'проекты', 'работа', 'задача', 'задачи', 'приложение', 'приложения', 'сайт', 'сайты'],
                'files': ['файл', 'файлы', 'документ', 'документы', 'изображение', 'изображения', 'видео', 'аудио'],
                'data': ['данные', 'информация', 'контент', 'материал', 'ресурс', 'ресурсы'],
                'learning': ['обучение', 'изучение', 'курс', 'курсы', 'урок', 'уроки', 'лекция', 'лекции', 'практика'],
                'tools': ['инструмент', 'инструменты', 'утилита', 'утилиты', 'библиотека', 'библиотеки', 'фреймворк', 'фреймворки']
            },
            'en': {
                'programming': ['code', 'program', 'script', 'function', 'class', 'python', 'javascript', 'java', 'react', 'vue', 'angular', 'node', 'php', 'cpp', 'csharp', 'go', 'rust'],
                'documentation': ['docs', 'documentation', 'guide', 'manual', 'readme', 'tutorial', 'tutorials', 'howto'],
                'projects': ['project', 'projects', 'work', 'task', 'tasks', 'app', 'application', 'website', 'site'],
                'files': ['file', 'files', 'document', 'documents', 'image', 'images', 'video', 'audio'],
                'data': ['data', 'information', 'content', 'material', 'resource', 'resources'],
                'learning': ['learning', 'study', 'course', 'courses', 'lesson', 'lessons', 'lecture', 'lectures', 'practice'],
                'tools': ['tool', 'tools', 'utility', 'utilities', 'library', 'libraries', 'framework', 'frameworks']
            }
        }
        
    def _extract_time_filters(self, text: str, language: str) -> Dict[str, Any]:
        """Extract time-based filters from text."""
        time_params = {}
        
        if language == 'ru':
            # Last period patterns
            last_period_match = re.search(r'(последний|последние|последнюю)\s+(\d+\s+)*(день|дни|неделю|недели|месяц|месяцы|год|года)', text)
            if last_period_match:
                period = last_period_match.group(3)
                number = last_period_match.group(2)
                if number:
                    number = int(re.search(r'\d+', number).group())
                else:
                    number = 1
                    
                if period in ['день', 'дни']:
                    time_params['date_from'] = f'last_{number}_days'
                elif period in ['неделю', 'недели']:
                    time_params['date_from'] = f'last_{number}_weeks'
                elif period in ['месяц', 'месяцы']:
                    time_params['date_from'] = f'last_{number}_months'
                elif period in ['год', 'года']:
                    time_params['date_from'] = f'last_{number}_years'
            
            # Since beginning patterns
            since_match = re.search(r'(с\s+)*(начала\s+)*(недели|месяца|года)', text)
            if since_match:
                period = since_match.group(3)
                if period == 'недели':
                    time_params['date_from'] = 'beginning_of_week'
                elif period == 'месяца':
                    time_params['date_from'] = 'beginning_of_month'
                elif period == 'года':
                    time_params['date_from'] = 'beginning_of_year'
            
            # Older/newer than patterns
            age_match = re.search(r'(старше|новее)\s+(\d+)\s+(дней|недель|месяцев|лет)', text)
            if age_match:
                comparison = age_match.group(1)
                number = int(age_match.group(2))
                period = age_match.group(3)
                
                if comparison == 'старше':
                    time_params['date_to'] = f'{number}_{period}_ago'
                else:  # новее
                    time_params['date_from'] = f'{number}_{period}_ago'
            
            # Specific date patterns
            date_match = re.search(r'(до|после)\s+([\d\.\-\/]+)', text)
            if date_match:
                comparison = date_match.group(1)
                date_str = date_match.group(2)
                
                if comparison == 'до':
                    time_params['date_to'] = date_str
                else:  # после
                    time_params['date_from'] = date_str
                    
        else:  # English
            # Last period patterns
            last_period_match = re.search(r'(last|past)\s+(\d+\s+)*(day|days|week|weeks|month|months|year|years)', text)
            if last_period_match:
                period = last_period_match.group(3)
                number = last_period_match.group(2)
                if number:
                    number = int(re.search(r'\d+', number).group())
                else:
                    number = 1
                    
                time_params['date_from'] = f'last_{number}_{period}'
            
            # Since beginning patterns
            since_match = re.search(r'(since\s+)*(beginning\s+of\s+)*(week|month|year)', text)
            if since_match:
                period = since_match.group(3)
                time_params['date_from'] = f'beginning_of_{period}'
            
            # Older/newer than patterns
            age_match = re.search(r'(older|newer)\s+than\s+(\d+)\s+(days|weeks|months|years)', text)
            if age_match:
                comparison = age_match.group(1)
                number = int(age_match.group(2))
                period = age_match.group(3)
                
                if comparison == 'older':
                    time_params['date_to'] = f'{number}_{period}_ago'
                else:  # newer
                    time_params['date_from'] = f'{number}_{period}_ago'
            
            # Specific date patterns
            date_match = re.search(r'(before|after)\s+([\d\.\-\/]+)', text)
            if date_match:
                comparison = date_match.group(1)
                date_str = date_match.group(2)
                
                if comparison == 'before':
                    time_params['date_to'] = date_str
                else:  # after
                    time_params['date_from'] = date_str
        
        return time_params
    
    def _extract_category_filters(self, text: str, language: str) -> Dict[str, Any]:
        """Extract category-based filters from text."""
        category_params = {}
        
        if language == 'ru':
            # Category patterns
            category_match = re.search(r'(категории|типа)\s+(.+?)(?:\s+(за|с|до|после|старше|новее)|$)', text)
            if category_match:
                category_params['category'] = category_match.group(2).strip()
        else:  # English
            category_match = re.search(r'(of\s+type|category)\s+(.+?)(?:\s+(from|since|before|after|older|newer)|$)', text)
            if category_match:
                category_params['category'] = category_match.group(2).strip()
        
        return category_params