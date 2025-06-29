"""
Интерпретатор естественных команд для Render.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CommandType(Enum):
    """Типы команд, которые могут быть распознаны."""
    SEARCH = "search"
    SEMANTIC_SEARCH = "semantic_search"
    LIST = "list"
    HELP = "help"
    STATS = "stats"
    UNKNOWN = "unknown"

@dataclass
class CommandIntent:
    """Представляет распознанное намерение команды."""
    command_type: CommandType
    parameters: Dict[str, Any]
    confidence: float
    original_text: str
    language: str = "ru"

class NaturalLanguageCommandInterpreter:
    """Интерпретирует команды на естественном языке."""
    
    def __init__(self, classifier=None):
        """Инициализация интерпретатора команд."""
        self.classifier = classifier
        self._init_patterns()
        self._init_synonyms()
    
    def _init_patterns(self):
        """Инициализация паттернов команд."""
        self.command_patterns = {
            CommandType.SEARCH: {
                'ru': [
                    r'(найди|найти|поиск|ищи|искать|покажи|показать)\s+(.+)',
                    r'где\s+(.+)\?*',
                    r'есть\s+ли\s+(.+)\?*',
                    r'дай\s+мне\s+(.+)',
                    r'хочу\s+(найти|посмотреть)\s+(.+)',
                    r'мне\s+нужно\s+(найти\s+)*(.+)',
                    r'можешь\s+(найти|показать)\s+(.+)\?*',
                    r'поищи\s+(.+)',
                    r'ищу\s+(.+)',
                    r'нужен\s+(.+)',
                    r'нужна\s+(.+)',
                ],
                'en': [
                    r'(find|search|look|show|get|locate)\s+(.+)',
                    r'where\s+(.+)\?*',
                    r'do\s+you\s+have\s+(.+)\?*',
                    r'i\s+need\s+(.+)',
                    r'show\s+me\s+(.+)',
                    r'can\s+you\s+(find|show)\s+(.+)\?*',
                    r'looking\s+for\s+(.+)',
                ]
            },
            
            CommandType.SEMANTIC_SEARCH: {
                'ru': [
                    r'семантический\s+поиск\s+(.+)',
                    r'умный\s+поиск\s+(.+)',
                    r'найди\s+похожее\s+на\s+(.+)',
                    r'поиск\s+по\s+смыслу\s+(.+)',
                    r'ищи\s+семантически\s+(.+)',
                    r'найди\s+по\s+значению\s+(.+)',
                ],
                'en': [
                    r'semantic\s+search\s+(.+)',
                    r'smart\s+search\s+(.+)',
                    r'find\s+similar\s+to\s+(.+)',
                    r'search\s+by\s+meaning\s+(.+)',
                ]
            },
            
            CommandType.LIST: {
                'ru': [
                    r'покажи\s+(все\s+)*(.*)\s*',
                    r'список\s*(.*)\s*',
                    r'что\s+у\s+меня\s+есть\s*(.*)\s*',
                    r'мои\s+(.+)',
                    r'все\s+(.+)',
                    r'перечисли\s*(.*)\s*',
                ],
                'en': [
                    r'show\s+(all\s+)*(.*)\s*',
                    r'list\s*(.*)\s*',
                    r'what\s+do\s+i\s+have\s*(.*)\s*',
                    r'my\s+(.+)',
                    r'all\s+(.+)',
                ]
            },
            
            CommandType.HELP: {
                'ru': [
                    r'помощь',
                    r'справка',
                    r'что\s+ты\s+умеешь\?*',
                    r'как\s+(пользоваться|работать)\?*',
                    r'команды',
                    r'help',
                ],
                'en': [
                    r'help',
                    r'what\s+can\s+you\s+do\?*',
                    r'how\s+to\s+use\?*',
                    r'commands',
                ]
            },
            
            CommandType.STATS: {
                'ru': [
                    r'статистика',
                    r'статы',
                    r'сколько\s+у\s+меня\s+(.+)\?*',
                    r'количество\s*(.*)\s*',
                    r'подсчет\s*(.*)\s*',
                    r'отчет\s*(.*)\s*',
                ],
                'en': [
                    r'stats',
                    r'statistics',
                    r'how\s+many\s+(.+)\?*',
                    r'count\s*(.*)\s*',
                ]
            }
        }
        
        # Ключевые слова для определения языка
        self.russian_keywords = {
            'найди', 'найти', 'поиск', 'ищи', 'искать', 'покажи', 'показать',
            'список', 'все', 'мои', 'помощь', 'справка', 'что', 'как',
            'статистика', 'где', 'есть', 'дай', 'мне', 'нужно', 'хочу'
        }
    
    def _init_synonyms(self):
        """Инициализация синонимов для лучшего понимания."""
        self.synonyms = {
            'ru': {
                'search': ['найди', 'найти', 'поиск', 'ищи', 'искать', 'покажи', 'показать'],
                'semantic_search': ['семантический', 'умный', 'похожее', 'смыслу', 'семантически'],
                'list': ['список', 'покажи', 'все', 'перечисли'],
                'help': ['помощь', 'справка'],
                'stats': ['статистика', 'статы', 'количество', 'подсчет']
            },
            'en': {
                'search': ['find', 'search', 'look', 'show', 'get', 'locate'],
                'semantic_search': ['semantic', 'smart', 'similar', 'meaning'],
                'list': ['list', 'show', 'all'],
                'help': ['help'],
                'stats': ['stats', 'statistics', 'count']
            }
        }
    
    def detect_language(self, text: str) -> str:
        """Определение языка текста."""
        text_lower = text.lower()
        words = text_lower.split()
        
        # Подсчет русских ключевых слов
        russian_words = sum(1 for word in words if word in self.russian_keywords)
        
        # Проверка на кириллицу
        cyrillic_chars = len(re.findall(r'[а-яё]', text_lower))
        
        # Если больше 25% слов русские или есть кириллица, считаем русским
        total_words = len(words)
        if total_words > 0:
            russian_ratio = russian_words / total_words
            if russian_ratio > 0.25 or cyrillic_chars > 2:
                return 'ru'
        
        if cyrillic_chars > 0:
            return 'ru'
        
        return 'en'
    
    async def interpret_command(self, text: str) -> CommandIntent:
        """Интерпретация команды с улучшенной поддержкой русского языка."""
        text = text.strip()
        language = self.detect_language(text)
        
        # Попытка AI-интерпретации если доступна
        if self.classifier:
            ai_intent = await self._ai_interpret_command(text, language)
            if ai_intent and ai_intent.confidence > 0.7:
                return ai_intent
        
        # Улучшенное сопоставление паттернов
        pattern_intent = self._enhanced_pattern_interpret_command(text, language)
        
        return pattern_intent
    
    async def _ai_interpret_command(self, text: str, language: str) -> Optional[CommandIntent]:
        """AI-интерпретация команд."""
        try:
            prompt = self._create_command_interpretation_prompt(text, language)
            
            # Использование возможностей AI классификатора
            if hasattr(self.classifier, '_classify_with_groq'):
                response = await self.classifier._classify_with_groq(prompt)
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
    
    def _create_command_interpretation_prompt(self, text: str, language: str) -> str:
        """Создание промпта для AI-интерпретации команд."""
        if language == 'ru':
            return f"""
Ты - интеллектуальный интерпретатор команд для русскоязычного бота-помощника разработчика.
Определи намерение пользователя из текста: "{text}"

Доступные типы команд:
- search: поиск ресурсов, файлов, информации
- semantic_search: семантический поиск по смыслу
- list: показать список, перечислить ресурсы
- help: помощь, справка, инструкции
- stats: статистика, подсчет, метрики
- unknown: неизвестная команда

Верни результат ТОЛЬКО в JSON формате:
{{
    "command_type": "тип_команды",
    "parameters": {{
        "query": "поисковый запрос или параметр",
        "category": "категория если указана"
    }},
    "confidence": 0.9
}}
"""
        else:
            return f"""
You are an intelligent command interpreter for an English-speaking developer assistant bot.
Determine user intent from text: "{text}"

Available command types:
- search: search for resources, files, information
- semantic_search: semantic search by meaning
- list: show list, enumerate resources
- help: help, instructions, guide
- stats: statistics, count, metrics
- unknown: unknown command

Return result ONLY in JSON format:
{{
    "command_type": "command_type",
    "parameters": {{
        "query": "search query or parameter",
        "category": "category if specified"
    }},
    "confidence": 0.9
}}
"""
    
    def _enhanced_pattern_interpret_command(self, text: str, language: str) -> CommandIntent:
        """Улучшенное сопоставление паттернов."""
        text_lower = text.lower().strip()
        
        # Предобработка текста
        text_processed = self._preprocess_text(text_lower, language)
        
        # Попытка сопоставления с каждым типом команды
        for command_type, patterns in self.command_patterns.items():
            lang_patterns = patterns.get(language, [])
            
            for pattern in lang_patterns:
                match = re.search(pattern, text_processed)
                if match:
                    parameters = self._extract_parameters(match, command_type, text_lower, language)
                    confidence = self._calculate_confidence(text_lower, command_type, language)
                    
                    return CommandIntent(
                        command_type=command_type,
                        parameters=parameters,
                        confidence=confidence,
                        original_text=text,
                        language=language
                    )
        
        # Семантическое сопоставление
        semantic_intent = self._semantic_matching(text_lower, language)
        if semantic_intent.command_type != CommandType.UNKNOWN:
            return semantic_intent
        
        # Паттерн не найден
        return CommandIntent(
            command_type=CommandType.UNKNOWN,
            parameters={},
            confidence=0.0,
            original_text=text,
            language=language
        )
    
    def _preprocess_text(self, text: str, language: str) -> str:
        """Предобработка текста для лучшего сопоставления паттернов."""
        # Удаление пунктуации кроме важной
        text = re.sub(r'[^а-яёa-z0-9\s\-_]', ' ', text)
        
        # Нормализация пробелов
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_parameters(self, match, command_type: CommandType, text: str, language: str) -> Dict[str, Any]:
        """Извлечение параметров из совпадения."""
        parameters = {}
        
        if len(match.groups()) > 0:
            param_text = match.group(-1).strip()  # Последняя группа обычно параметр
            
            if command_type in [CommandType.SEARCH, CommandType.SEMANTIC_SEARCH]:
                parameters['query'] = param_text
                
                # Попытка определить категорию из контекста
                category = self._detect_category_from_text(text, language)
                if category:
                    parameters['category'] = category
                    
            elif command_type == CommandType.LIST:
                if param_text:
                    parameters['category'] = param_text
        
        return parameters
    
    def _detect_category_from_text(self, text: str, language: str) -> Optional[str]:
        """Определение категории из контекстных слов."""
        context_words = {
            'ru': {
                'frontend': ['фронтенд', 'react', 'vue', 'angular', 'javascript', 'css', 'html'],
                'backend': ['бэкенд', 'сервер', 'api', 'nodejs', 'python', 'php'],
                'database': ['база', 'данных', 'sql', 'mongodb'],
                'tools': ['инструменты', 'утилиты', 'docker', 'git']
            },
            'en': {
                'frontend': ['frontend', 'react', 'vue', 'angular', 'javascript', 'css', 'html'],
                'backend': ['backend', 'server', 'api', 'nodejs', 'python', 'php'],
                'database': ['database', 'sql', 'mongodb'],
                'tools': ['tools', 'utilities', 'docker', 'git']
            }
        }
        
        words = context_words.get(language, {})
        for category, keywords in words.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return None
    
    def _calculate_confidence(self, text: str, command_type: CommandType, language: str) -> float:
        """Вычисление уверенности на основе различных факторов."""
        base_confidence = 0.8 if language == 'ru' else 0.7
        
        # Повышение уверенности для точных совпадений ключевых слов
        synonyms = self.synonyms.get(language, {})
        command_synonyms = synonyms.get(command_type.value, [])
        
        if any(synonym in text for synonym in command_synonyms):
            base_confidence += 0.1
        
        # Повышение уверенности для контекстных слов
        if self._detect_category_from_text(text, language):
            base_confidence += 0.05
        
        return min(base_confidence, 0.95)
    
    def _semantic_matching(self, text: str, language: str) -> CommandIntent:
        """Семантическое сопоставление с использованием анализа синонимов."""
        synonyms = self.synonyms.get(language, {})
        
        # Подсчет совпадений для каждого типа команды
        command_scores = {}
        
        for command_name, command_synonyms in synonyms.items():
            score = sum(1 for synonym in command_synonyms if synonym in text)
            if score > 0:
                try:
                    if command_name == 'search':
                        command_type = CommandType.SEARCH
                    elif command_name == 'semantic_search':
                        command_type = CommandType.SEMANTIC_SEARCH
                    elif command_name == 'list':
                        command_type = CommandType.LIST
                    elif command_name == 'help':
                        command_type = CommandType.HELP
                    elif command_name == 'stats':
                        command_type = CommandType.STATS
                    else:
                        continue
                    
                    command_scores[command_type] = score
                except:
                    continue
        
        if command_scores:
            # Получить команду с наивысшим счетом
            best_command = max(command_scores.items(), key=lambda x: x[1])
            command_type, score = best_command
            
            # Извлечь базовые параметры
            parameters = {}
            if command_type in [CommandType.SEARCH, CommandType.SEMANTIC_SEARCH]:
                # Попытка извлечь запрос из оставшегося текста
                query_words = [word for word in text.split() 
                             if word not in synonyms.get('search', []) 
                             and word not in synonyms.get('semantic_search', [])]
                if query_words:
                    parameters['query'] = ' '.join(query_words)
            
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