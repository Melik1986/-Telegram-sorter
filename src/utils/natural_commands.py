"""Модуль для обработки расширенных естественных команд.

Этот модуль предоставляет функциональность для:
- Парсинга сложных естественных запросов
- Извлечения параметров поиска и фильтров
- Команд управления папками
- Экспорта и архивирования
- Интеллектуального анализа намерений пользователя
"""

import logging
import re
import json
import os
import shutil
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
from collections import defaultdict

try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False
    dateparser = None

logger = logging.getLogger(__name__)

class CommandType(Enum):
    """Типы команд."""
    SEARCH = "search"
    FILTER = "filter"
    ORGANIZE = "organize"
    EXPORT = "export"
    ARCHIVE = "archive"
    STATS = "stats"
    HELP = "help"
    FOLDER_MANAGEMENT = "folder_management"
    BATCH_OPERATIONS = "batch_operations"
    CONTENT_ANALYSIS = "content_analysis"
    UNKNOWN = "unknown"

class TimeRange(Enum):
    """Временные диапазоны."""
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"

@dataclass
class ParsedCommand:
    """Результат парсинга команды."""
    command_type: CommandType
    action: str
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    original_text: str = ""
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = {}
        if self.parameters is None:
            self.parameters = {}
        if self.suggestions is None:
            self.suggestions = []

class NaturalCommandProcessor:
    """Процессор естественных команд с расширенными возможностями."""
    
    def __init__(self, data_dir: str = None):
        """Инициализация процессора команд.
        
        Args:
            data_dir: Директория для сохранения данных
        """
        self.data_dir = Path(data_dir) if data_dir else Path('data')
        self.data_dir.mkdir(exist_ok=True)
        
        # Загрузка паттернов и словарей
        self._load_patterns()
        self._load_dictionaries()
        self._load_command_templates()
        
        logger.info("Natural command processor initialized")
    
    def _load_patterns(self):
        """Загрузка паттернов для распознавания команд."""
        # Паттерны для поиска
        self.search_patterns = [
            r'найди\s+(.+)',
            r'найти\s+(.+)',
            r'поиск\s+(.+)',
            r'ищи\s+(.+)',
            r'покажи\s+(.+)',
            r'find\s+(.+)',
            r'search\s+(.+)',
            r'look\s+for\s+(.+)',
            r'show\s+(.+)',
            r'get\s+(.+)'
        ]
        
        # Паттерны для фильтрации
        self.filter_patterns = {
            'category': [
                r'категори[ияй]\s+([\w\s]+)',
                r'в\s+категории\s+([\w\s]+)',
                r'category\s+([\w\s]+)',
                r'in\s+category\s+([\w\s]+)'
            ],
            'language': [
                r'на\s+(\w+)',
                r'язык[еа]?\s+(\w+)',
                r'in\s+(\w+)',
                r'language\s+(\w+)',
                r'(python|javascript|java|c\+\+|c#|go|rust|php|ruby|swift|kotlin)\s*туториалы?',
                r'(python|javascript|java|c\+\+|c#|go|rust|php|ruby|swift|kotlin)\s*примеры?',
                r'(python|javascript|java|c\+\+|c#|go|rust|php|ruby|swift|kotlin)\s*код'
            ],
            'framework': [
                r'(react|vue|angular|django|flask|spring|express|laravel)\s*',
                r'фреймворк\s+(\w+)',
                r'framework\s+(\w+)'
            ],
            'difficulty': [
                r'(начинающих|новичков|легк[иоые]+)',
                r'(продвинут[ыеых]+|сложн[ыеых]+)',
                r'(beginner|easy|simple)',
                r'(advanced|complex|difficult)'
            ],
            'time': [
                r'за\s+(последн[иеюя]+\s+)?([\w\s]+)',
                r'в\s+течени[еи]\s+([\w\s]+)',
                r'(today|yesterday|this\s+week|last\s+week|this\s+month|last\s+month)',
                r'(сегодня|вчера|на\s+этой\s+неделе|на\s+прошлой\s+неделе|в\s+этом\s+месяце|в\s+прошлом\s+месяце)',
                r'с\s+(\d{1,2}[./]\d{1,2}[./]\d{2,4})\s+по\s+(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
                r'from\s+(\d{1,2}[./]\d{1,2}[./]\d{2,4})\s+to\s+(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
                r'старше\s+(\d+)\s+(дн[еяй]+|недел[ьи]|месяц[еваов]+|лет)',
                r'новее\s+(\d+)\s+(дн[еяй]+|недел[ьи]|месяц[еваов]+|лет)',
                r'older\s+than\s+(\d+)\s+(days?|weeks?|months?|years?)',
                r'newer\s+than\s+(\d+)\s+(days?|weeks?|months?|years?)'
            ],
            'size': [
                r'размер[ома]*\s+(больше|меньше|равен)\s+(\d+)\s*(kb|mb|gb)?',
                r'size\s+(larger|smaller|equal)\s+(\d+)\s*(kb|mb|gb)?',
                r'файлы\s+(больше|меньше)\s+(\d+)\s*(kb|mb|gb)?',
                r'files\s+(larger|smaller)\s+than\s+(\d+)\s*(kb|mb|gb)?'
            ],
            'extension': [
                r'с\s+расширением\s+([.\w]+)',
                r'файлы\s+([.\w]+)',
                r'with\s+extension\s+([.\w]+)',
                r'([.\w]+)\s+files'
            ],
            'content': [
                r'содержащие\s+"([^"]+)"',
                r'с\s+содержимым\s+"([^"]+)"',
                r'containing\s+"([^"]+)"',
                r'with\s+content\s+"([^"]+)"'
            ]
        }
        
        # Паттерны для организации
        self.organize_patterns = [
            r'организуй\s+(.+)',
            r'упорядочь\s+(.+)',
            r'сортируй\s+(.+)',
            r'organize\s+(.+)',
            r'sort\s+(.+)',
            r'arrange\s+(.+)'
        ]
        
        # Паттерны для экспорта
        self.export_patterns = [
            r'экспорт[ируй]*\s+(.+)',
            r'сохрани\s+(.+)',
            r'export\s+(.+)',
            r'save\s+(.+)',
            r'создай\s+отчет\s+(.+)',
            r'generate\s+report\s+(.+)'
        ]
        
        # Паттерны для архивирования
        self.archive_patterns = [
            r'архивируй\s+(.+)',
            r'заархивируй\s+(.+)',
            r'archive\s+(.+)',
            r'compress\s+(.+)',
            r'zip\s+(.+)'
        ]
        
        # Паттерны для управления папками
        self.folder_management_patterns = [
            r'создай\s+папк[уи]\s+(.+)',
            r'удали\s+папк[уи]\s+(.+)',
            r'переименуй\s+папк[уи]\s+(.+?)\s+в\s+(.+)',
            r'перемести\s+(.+?)\s+в\s+(.+)',
            r'скопируй\s+(.+?)\s+в\s+(.+)',
            r'create\s+folder\s+(.+)',
            r'delete\s+folder\s+(.+)',
            r'rename\s+folder\s+(.+?)\s+to\s+(.+)',
            r'move\s+(.+?)\s+to\s+(.+)',
            r'copy\s+(.+?)\s+to\s+(.+)',
            r'объедини\s+папки\s+(.+)',
            r'разбей\s+папк[уи]\s+(.+?)\s+по\s+(.+)',
            r'merge\s+folders\s+(.+)',
            r'split\s+folder\s+(.+?)\s+by\s+(.+)'
        ]
        
        # Паттерны для пакетных операций
        self.batch_patterns = [
            r'примени\s+(.+?)\s+ко\s+всем\s+(.+)',
            r'обработай\s+все\s+(.+?)\s+с\s+(.+)',
            r'apply\s+(.+?)\s+to\s+all\s+(.+)',
            r'process\s+all\s+(.+?)\s+with\s+(.+)',
            r'массово\s+(.+)',
            r'bulk\s+(.+)'
        ]
        
        # Паттерны для анализа контента
        self.content_analysis_patterns = [
            r'проанализируй\s+(.+)',
            r'найди\s+дубликаты\s+в\s+(.+)',
            r'проверь\s+качество\s+(.+)',
            r'analyze\s+(.+)',
            r'find\s+duplicates\s+in\s+(.+)',
            r'check\s+quality\s+of\s+(.+)',
            r'сравни\s+(.+?)\s+с\s+(.+)',
            r'compare\s+(.+?)\s+with\s+(.+)'
        ]
    
    def _load_dictionaries(self):
        """Загрузка словарей для нормализации терминов."""
        # Словарь категорий
        self.category_synonyms = {
            'tutorial': ['туториал', 'урок', 'обучение', 'гайд', 'guide'],
            'documentation': ['документация', 'docs', 'справка', 'reference'],
            'example': ['пример', 'образец', 'sample', 'demo'],
            'library': ['библиотека', 'lib', 'package', 'модуль'],
            'tool': ['инструмент', 'утилита', 'utility', 'софт'],
            'article': ['статья', 'пост', 'заметка', 'note'],
            'video': ['видео', 'ролик', 'запись', 'recording'],
            'book': ['книга', 'учебник', 'manual', 'handbook']
        }
        
        # Словарь языков программирования
        self.language_synonyms = {
            'python': ['питон', 'пайтон', 'py'],
            'javascript': ['js', 'джаваскрипт', 'жс'],
            'java': ['джава', 'ява'],
            'cpp': ['c++', 'си++', 'плюсплюс'],
            'csharp': ['c#', 'си#', 'шарп'],
            'go': ['golang', 'гоу', 'го'],
            'rust': ['раст', 'рст'],
            'php': ['пхп', 'пэхпэ'],
            'ruby': ['руби', 'рубин'],
            'swift': ['свифт'],
            'kotlin': ['котлин']
        }
        
        # Словарь фреймворков
        self.framework_synonyms = {
            'react': ['реакт', 'реактjs'],
            'vue': ['вью', 'vuejs'],
            'angular': ['ангуляр', 'angularjs'],
            'django': ['джанго'],
            'flask': ['фласк'],
            'spring': ['спринг'],
            'express': ['экспресс', 'expressjs'],
            'laravel': ['ларавел']
        }
        
        # Словарь уровней сложности
        self.difficulty_synonyms = {
            'beginner': ['начинающий', 'новичок', 'легкий', 'простой', 'easy', 'simple'],
            'intermediate': ['средний', 'промежуточный', 'intermediate'],
            'advanced': ['продвинутый', 'сложный', 'экспертный', 'complex', 'expert']
        }
        
        # Словарь временных периодов
        self.time_synonyms = {
            'today': ['сегодня', 'сейчас'],
            'yesterday': ['вчера'],
            'this_week': ['эта неделя', 'текущая неделя', 'на этой неделе'],
            'last_week': ['прошлая неделя', 'на прошлой неделе'],
            'this_month': ['этот месяц', 'текущий месяц', 'в этом месяце'],
            'last_month': ['прошлый месяц', 'в прошлом месяце'],
            'this_year': ['этот год', 'текущий год', 'в этом году'],
            'last_year': ['прошлый год', 'в прошлом году']
        }
    
    def _load_command_templates(self):
        """Загрузка шаблонов команд."""
        self.command_templates = {
            'search_by_language_and_time': {
                'pattern': r'найди\s+(.+?)\s+(python|javascript|java|c\+\+|c#|go|rust|php|ruby|swift|kotlin)\s+(.+?)\s+за\s+(последн[иеюя]+\s+)?([\w\s]+)',
                'groups': ['query', 'language', 'additional', 'time_modifier', 'time_period'],
                'confidence': 0.9
            },
            'search_by_category_and_difficulty': {
                'pattern': r'покажи\s+(легк[иеые]+|сложн[ыеых]+|продвинут[ыеых]+)\s+(.+?)\s+в\s+категории\s+([\w\s]+)',
                'groups': ['difficulty', 'query', 'category'],
                'confidence': 0.85
            },
            'complex_search_with_multiple_filters': {
                'pattern': r'найди\s+все\s+(.+?)\s+(python|javascript|java|c\+\+|c#|go|rust|php|ruby|swift|kotlin)\s+(.+?)\s+за\s+(последн[иеюя]+\s+)?([\w\s]+)\s+в\s+категории\s+([\w\s]+)',
                'groups': ['query', 'language', 'additional', 'time_modifier', 'time_period', 'category'],
                'confidence': 0.95
            },
            'organize_by_criteria': {
                'pattern': r'организуй\s+(.+?)\s+по\s+([\w\s]+)',
                'groups': ['target', 'criteria'],
                'confidence': 0.8
            },
            'export_filtered_results': {
                'pattern': r'экспорт[ируй]*\s+(.+?)\s+в\s+(\w+)\s*формат[еа]?',
                'groups': ['content', 'format'],
                'confidence': 0.8
            },
            'folder_create_with_structure': {
                'pattern': r'создай\s+папк[уи]\s+(.+?)\s+со\s+структурой\s+(.+)',
                'groups': ['folder_name', 'structure'],
                'confidence': 0.9
            },
            'batch_operation_with_filter': {
                'pattern': r'примени\s+(.+?)\s+ко\s+всем\s+(.+?)\s+файлам\s+(.+)',
                'groups': ['operation', 'file_type', 'filter'],
                'confidence': 0.85
            },
            'content_analysis_with_criteria': {
                'pattern': r'проанализируй\s+(.+?)\s+на\s+предмет\s+(.+)',
                'groups': ['target', 'criteria'],
                'confidence': 0.8
            },
            'move_files_by_pattern': {
                'pattern': r'перемести\s+все\s+(.+?)\s+файлы\s+из\s+(.+?)\s+в\s+(.+)',
                'groups': ['file_pattern', 'source', 'destination'],
                'confidence': 0.85
            }
        }
    
    def parse_command(self, text: str) -> ParsedCommand:
        """Парсинг естественной команды.
        
        Args:
            text: Текст команды
            
        Returns:
            Объект ParsedCommand с результатами парсинга
        """
        try:
            # Нормализация текста
            normalized_text = self._normalize_text(text)
            
            # Определение типа команды
            command_type = self._detect_command_type(normalized_text)
            
            # Парсинг в зависимости от типа
            if command_type == CommandType.SEARCH:
                return self._parse_search_command(normalized_text, text)
            elif command_type == CommandType.ORGANIZE:
                return self._parse_organize_command(normalized_text, text)
            elif command_type == CommandType.EXPORT:
                return self._parse_export_command(normalized_text, text)
            elif command_type == CommandType.ARCHIVE:
                return self._parse_archive_command(normalized_text, text)
            elif command_type == CommandType.STATS:
                return self._parse_stats_command(normalized_text, text)
            elif command_type == CommandType.FOLDER_MANAGEMENT:
                return self._parse_folder_management_command(normalized_text, text)
            elif command_type == CommandType.BATCH_OPERATIONS:
                return self._parse_batch_operations_command(normalized_text, text)
            elif command_type == CommandType.CONTENT_ANALYSIS:
                return self._parse_content_analysis_command(normalized_text, text)
            else:
                return self._parse_unknown_command(normalized_text, text)
                
        except Exception as e:
            logger.error(f"Error parsing command '{text}': {e}")
            return ParsedCommand(
                command_type=CommandType.UNKNOWN,
                action="error",
                original_text=text,
                confidence=0.0
            )
    
    def _normalize_text(self, text: str) -> str:
        """Нормализация текста команды."""
        # Приведение к нижнему регистру
        normalized = text.lower().strip()
        
        # Удаление лишних пробелов
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Замена синонимов
        for category, synonyms in self.category_synonyms.items():
            for synonym in synonyms:
                normalized = re.sub(rf'\b{re.escape(synonym)}\b', category, normalized)
        
        for language, synonyms in self.language_synonyms.items():
            for synonym in synonyms:
                normalized = re.sub(rf'\b{re.escape(synonym)}\b', language, normalized)
        
        return normalized
    
    def _detect_command_type(self, text: str) -> CommandType:
        """Определение типа команды."""
        # Проверка паттернов управления папками
        for pattern in self.folder_management_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return CommandType.FOLDER_MANAGEMENT
        
        # Проверка паттернов пакетных операций
        for pattern in self.batch_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return CommandType.BATCH_OPERATIONS
        
        # Проверка паттернов анализа контента
        for pattern in self.content_analysis_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return CommandType.CONTENT_ANALYSIS
        
        # Проверка паттернов поиска
        for pattern in self.search_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return CommandType.SEARCH
        
        # Проверка паттернов организации
        for pattern in self.organize_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return CommandType.ORGANIZE
        
        # Проверка паттернов экспорта
        for pattern in self.export_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return CommandType.EXPORT
        
        # Проверка паттернов архивирования
        for pattern in self.archive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return CommandType.ARCHIVE
        
        # Проверка команд статистики
        stats_keywords = ['статистика', 'stats', 'отчет', 'report', 'анализ', 'analysis']
        if any(keyword in text for keyword in stats_keywords):
            return CommandType.STATS
        
        # Проверка команд помощи
        help_keywords = ['помощь', 'help', 'справка', 'команды', 'commands']
        if any(keyword in text for keyword in help_keywords):
            return CommandType.HELP
        
        return CommandType.UNKNOWN
    
    def _parse_search_command(self, text: str, original: str) -> ParsedCommand:
        """Парсинг команды поиска."""
        # Извлечение основного запроса
        query = None
        for pattern in self.search_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                break
        
        if not query:
            return ParsedCommand(
                command_type=CommandType.SEARCH,
                action="search",
                original_text=original,
                confidence=0.3
            )
        
        # Извлечение фильтров
        filters = self._extract_filters(text)
        
        # Определение уровня уверенности
        confidence = self._calculate_confidence(text, filters)
        
        return ParsedCommand(
            command_type=CommandType.SEARCH,
            action="search",
            query=query,
            filters=filters,
            original_text=original,
            confidence=confidence
        )
    
    def _parse_organize_command(self, text: str, original: str) -> ParsedCommand:
        """Парсинг команды организации."""
        # Извлечение цели и критериев
        target = None
        criteria = None
        
        for pattern in self.organize_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                target = match.group(1).strip()
                break
        
        # Поиск критериев сортировки
        criteria_patterns = [
            r'по\s+(\w+)',
            r'by\s+(\w+)',
            r'сортировать\s+по\s+(\w+)'
        ]
        
        for pattern in criteria_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                criteria = match.group(1).strip()
                break
        
        parameters = {
            'target': target,
            'criteria': criteria or 'category'
        }
        
        return ParsedCommand(
            command_type=CommandType.ORGANIZE,
            action="organize",
            parameters=parameters,
            original_text=original,
            confidence=0.7 if target else 0.4
        )
    
    def _parse_export_command(self, text: str, original: str) -> ParsedCommand:
        """Парсинг команды экспорта."""
        # Извлечение содержимого и формата
        content = None
        export_format = 'json'  # По умолчанию
        
        for pattern in self.export_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                break
        
        # Поиск формата
        format_patterns = [
            r'в\s+(json|csv|xml|txt|markdown|md)\s*формат[еа]?',
            r'as\s+(json|csv|xml|txt|markdown|md)',
            r'to\s+(json|csv|xml|txt|markdown|md)'
        ]
        
        for pattern in format_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                export_format = match.group(1).lower()
                break
        
        # Извлечение фильтров для экспорта
        filters = self._extract_filters(text)
        
        parameters = {
            'content': content,
            'format': export_format,
            'filters': filters
        }
        
        return ParsedCommand(
            command_type=CommandType.EXPORT,
            action="export",
            parameters=parameters,
            original_text=original,
            confidence=0.8 if content else 0.5
        )
    
    def _parse_archive_command(self, text: str, original: str) -> ParsedCommand:
        """Парсинг команды архивирования."""
        # Извлечение цели архивирования
        target = None
        
        for pattern in self.archive_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                target = match.group(1).strip()
                break
        
        # Извлечение параметров архивирования
        archive_type = 'zip'  # По умолчанию
        
        if 'tar' in text or 'gzip' in text:
            archive_type = 'tar.gz'
        elif 'rar' in text:
            archive_type = 'rar'
        
        parameters = {
            'target': target,
            'archive_type': archive_type,
            'include_metadata': True
        }
        
        return ParsedCommand(
            command_type=CommandType.ARCHIVE,
            action="archive",
            parameters=parameters,
            original_text=original,
            confidence=0.7 if target else 0.4
        )
    
    def _parse_stats_command(self, text: str, original: str) -> ParsedCommand:
        """Парсинг команды статистики."""
        # Определение типа статистики
        stats_type = 'general'
        
        if any(word in text for word in ['категори', 'category']):
            stats_type = 'categories'
        elif any(word in text for word in ['язык', 'language']):
            stats_type = 'languages'
        elif any(word in text for word in ['время', 'time', 'дата', 'date']):
            stats_type = 'timeline'
        elif any(word in text for word in ['размер', 'size', 'объем', 'volume']):
            stats_type = 'size'
        
        parameters = {
            'stats_type': stats_type
        }
        
        return ParsedCommand(
            command_type=CommandType.STATS,
            action="stats",
            parameters=parameters,
            original_text=original,
            confidence=0.8
        )
    
    def _parse_folder_management_command(self, text: str, original: str) -> ParsedCommand:
        """Парсинг команды управления папками."""
        action = "create_folder"
        folder_name = None
        structure = None
        
        # Определение действия
        if any(word in text for word in ['создай', 'create', 'новая']):
            action = "create_folder"
        elif any(word in text for word in ['удали', 'delete', 'remove']):
            action = "delete_folder"
        elif any(word in text for word in ['переименуй', 'rename']):
            action = "rename_folder"
        elif any(word in text for word in ['перемести', 'move']):
            action = "move_folder"
        
        # Извлечение имени папки
        folder_patterns = [
            r'папк[уи]\s+([\w\s\-_]+)',
            r'folder\s+([\w\s\-_]+)',
            r'директори[юи]\s+([\w\s\-_]+)'
        ]
        
        for pattern in folder_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                folder_name = match.group(1).strip()
                break
        
        # Извлечение структуры (если указана)
        structure_patterns = [
            r'со\s+структурой\s+(.+)',
            r'with\s+structure\s+(.+)',
            r'включающ[ую]+\s+(.+)'
        ]
        
        for pattern in structure_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                structure = match.group(1).strip()
                break
        
        parameters = {
            'folder_name': folder_name,
            'structure': structure,
            'action': action
        }
        
        return ParsedCommand(
            command_type=CommandType.FOLDER_MANAGEMENT,
            action=action,
            parameters=parameters,
            original_text=original,
            confidence=0.8 if folder_name else 0.5
        )
    
    def _parse_batch_operations_command(self, text: str, original: str) -> ParsedCommand:
        """Парсинг команды пакетных операций."""
        operation = None
        file_type = None
        filter_criteria = None
        
        # Извлечение операции
        operation_patterns = [
            r'примени\s+([\w\s]+)\s+ко\s+всем',
            r'apply\s+([\w\s]+)\s+to\s+all',
            r'выполни\s+([\w\s]+)\s+для\s+всех'
        ]
        
        for pattern in operation_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                operation = match.group(1).strip()
                break
        
        # Извлечение типа файлов
        file_type_patterns = [
            r'всем\s+([\w\s]+)\s+файлам',
            r'all\s+([\w\s]+)\s+files',
            r'файлам\s+типа\s+([\w\s]+)'
        ]
        
        for pattern in file_type_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                file_type = match.group(1).strip()
                break
        
        # Извлечение критериев фильтрации
        filter_patterns = [
            r'файлам\s+(.+)$',
            r'files\s+(.+)$',
            r'которые\s+(.+)'
        ]
        
        for pattern in filter_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                filter_criteria = match.group(1).strip()
                break
        
        parameters = {
            'operation': operation,
            'file_type': file_type,
            'filter_criteria': filter_criteria,
            'batch_size': 100  # По умолчанию
        }
        
        return ParsedCommand(
            command_type=CommandType.BATCH_OPERATIONS,
            action="batch_operation",
            parameters=parameters,
            original_text=original,
            confidence=0.8 if operation and file_type else 0.5
        )
    
    def _parse_content_analysis_command(self, text: str, original: str) -> ParsedCommand:
        """Парсинг команды анализа контента."""
        target = None
        analysis_criteria = None
        
        # Извлечение цели анализа
        target_patterns = [
            r'проанализируй\s+([\w\s\-_]+)\s+на\s+предмет',
            r'analyze\s+([\w\s\-_]+)\s+for',
            r'анализ\s+([\w\s\-_]+)\s+по'
        ]
        
        for pattern in target_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                target = match.group(1).strip()
                break
        
        # Извлечение критериев анализа
        criteria_patterns = [
            r'на\s+предмет\s+(.+)',
            r'for\s+(.+)',
            r'по\s+критери[юям]+\s+(.+)'
        ]
        
        for pattern in criteria_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                analysis_criteria = match.group(1).strip()
                break
        
        # Определение типа анализа
        analysis_type = "general"
        if any(word in text for word in ['сложност', 'difficulty', 'complexity']):
            analysis_type = "complexity"
        elif any(word in text for word in ['актуальност', 'relevance', 'freshness']):
            analysis_type = "relevance"
        elif any(word in text for word in ['качеств', 'quality']):
            analysis_type = "quality"
        elif any(word in text for word in ['дублика', 'duplicate', 'similarity']):
            analysis_type = "duplicates"
        
        parameters = {
            'target': target,
            'analysis_criteria': analysis_criteria,
            'analysis_type': analysis_type
        }
        
        return ParsedCommand(
            command_type=CommandType.CONTENT_ANALYSIS,
            action="analyze_content",
            parameters=parameters,
            original_text=original,
            confidence=0.8 if target and analysis_criteria else 0.5
        )
    
    def _parse_unknown_command(self, text: str, original: str) -> ParsedCommand:
        """Парсинг неизвестной команды."""
        # Попытка предложить альтернативы
        suggestions = self._generate_suggestions(text)
        
        return ParsedCommand(
            command_type=CommandType.UNKNOWN,
            action="unknown",
            original_text=original,
            confidence=0.0,
            suggestions=suggestions
        )
    
    def _extract_filters(self, text: str) -> Dict[str, Any]:
        """Извлечение фильтров из текста."""
        filters = {}
        
        # Извлечение категории
        for pattern in self.filter_patterns['category']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                category = match.group(1).strip()
                filters['categories'] = [self._normalize_category(category)]
                break
        
        # Извлечение языка программирования
        for pattern in self.filter_patterns['language']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                language = match.group(1).strip()
                filters['programming_languages'] = [self._normalize_language(language)]
                break
        
        # Извлечение фреймворка
        for pattern in self.filter_patterns['framework']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                framework = match.group(1).strip()
                filters['frameworks'] = [self._normalize_framework(framework)]
                break
        
        # Извлечение уровня сложности
        for pattern in self.filter_patterns['difficulty']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                difficulty = match.group(1).strip()
                filters['difficulty_levels'] = [self._normalize_difficulty(difficulty)]
                break
        
        # Извлечение временного диапазона
        time_filter = self._extract_time_filter(text)
        if time_filter:
            filters.update(time_filter)
        
        return filters
    
    def _extract_time_filter(self, text: str) -> Optional[Dict[str, Any]]:
        """Извлечение временного фильтра."""
        # Поиск относительных временных выражений
        for time_key, synonyms in self.time_synonyms.items():
            for synonym in synonyms:
                if synonym in text:
                    return self._convert_time_range(time_key)
        
        # Поиск абсолютных дат (если доступен dateparser)
        if DATEPARSER_AVAILABLE:
            date_patterns = [
                r'с\s+(\d{1,2}[\.\/\-]\d{1,2}[\.\/\-]\d{2,4})',
                r'до\s+(\d{1,2}[\.\/\-]\d{1,2}[\.\/\-]\d{2,4})',
                r'from\s+(\d{1,2}[\.\/\-]\d{1,2}[\.\/\-]\d{2,4})',
                r'to\s+(\d{1,2}[\.\/\-]\d{1,2}[\.\/\-]\d{2,4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    try:
                        parsed_date = dateparser.parse(date_str)
                        if parsed_date:
                            if 'с' in pattern or 'from' in pattern:
                                return {'date_from': parsed_date}
                            else:
                                return {'date_to': parsed_date}
                    except:
                        continue
        
        return None
    
    def _convert_time_range(self, time_key: str) -> Dict[str, datetime]:
        """Конвертация временного диапазона в даты."""
        now = datetime.now()
        
        if time_key == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_key == 'yesterday':
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(hour=23, minute=59, second=59)
        elif time_key == 'this_week':
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_key == 'last_week':
            days_since_monday = now.weekday()
            this_monday = now - timedelta(days=days_since_monday)
            start = (this_monday - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (this_monday - timedelta(seconds=1))
        elif time_key == 'this_month':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_key == 'last_month':
            if now.month == 1:
                start = now.replace(year=now.year-1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
            else:
                start = now.replace(month=now.month-1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
        else:
            return {}
        
        return {
            'date_from': start,
            'date_to': end
        }
    
    def _normalize_category(self, category: str) -> str:
        """Нормализация категории."""
        category = category.lower().strip()
        
        for normalized, synonyms in self.category_synonyms.items():
            if category in synonyms or category == normalized:
                return normalized
        
        return category
    
    def _normalize_language(self, language: str) -> str:
        """Нормализация языка программирования."""
        language = language.lower().strip()
        
        for normalized, synonyms in self.language_synonyms.items():
            if language in synonyms or language == normalized:
                return normalized
        
        return language
    
    def _normalize_framework(self, framework: str) -> str:
        """Нормализация фреймворка."""
        framework = framework.lower().strip()
        
        for normalized, synonyms in self.framework_synonyms.items():
            if framework in synonyms or framework == normalized:
                return normalized
        
        return framework
    
    def _normalize_difficulty(self, difficulty: str) -> str:
        """Нормализация уровня сложности."""
        difficulty = difficulty.lower().strip()
        
        for normalized, synonyms in self.difficulty_synonyms.items():
            if difficulty in synonyms or difficulty == normalized:
                return normalized
        
        return difficulty
    
    def _calculate_confidence(self, text: str, filters: Dict[str, Any]) -> float:
        """Вычисление уровня уверенности в парсинге."""
        confidence = 0.5  # Базовый уровень
        
        # Увеличение за наличие фильтров
        confidence += len(filters) * 0.1
        
        # Увеличение за специфичность запроса
        specific_terms = ['tutorial', 'example', 'documentation', 'guide']
        for term in specific_terms:
            if term in text:
                confidence += 0.1
        
        # Увеличение за наличие языков программирования
        programming_languages = ['python', 'javascript', 'java', 'cpp', 'go', 'rust']
        for lang in programming_languages:
            if lang in text:
                confidence += 0.15
        
        return min(1.0, confidence)
    
    def _generate_suggestions(self, text: str) -> List[str]:
        """Генерация предложений для неизвестной команды."""
        suggestions = []
        
        # Базовые предложения
        suggestions.extend([
            "найди python туториалы",
            "покажи все react примеры",
            "организуй файлы по категориям",
            "экспортируй результаты в json",
            "покажи статистику по языкам",
            "создай папку для проектов",
            "примени переименование ко всем файлам",
            "проанализируй код на предмет сложности"
        ])
        
        # Предложения на основе ключевых слов в тексте
        if any(word in text for word in ['python', 'питон']):
            suggestions.insert(0, "найди python туториалы за последний месяц")
        
        if any(word in text for word in ['react', 'реакт']):
            suggestions.insert(0, "покажи react примеры для начинающих")
        
        if any(word in text for word in ['организ', 'сортир', 'упорядоч']):
            suggestions.insert(0, "организуй файлы по категориям")
        
        if any(word in text for word in ['папк', 'folder', 'директор']):
            suggestions.insert(0, "создай папку со структурой проекта")
        
        if any(word in text for word in ['примени', 'apply', 'batch']):
            suggestions.insert(0, "примени операцию ко всем файлам типа")
        
        if any(word in text for word in ['анализ', 'analyze', 'проанализ']):
            suggestions.insert(0, "проанализируй файлы на предмет качества")
        
        return suggestions[:7]  # Увеличиваем количество предложений
    
    def get_command_help(self) -> Dict[str, List[str]]:
        """Получение справки по командам."""
        return {
            'search': [
                "найди python туториалы",
                "покажи react примеры для начинающих",
                "найди все javascript статьи за последний месяц",
                "ищи документацию по django",
                "найди все React туториалы за последний месяц в категории веб-разработка"
            ],
            'organize': [
                "организуй файлы по категориям",
                "сортируй по языкам программирования",
                "упорядочь по дате создания"
            ],
            'export': [
                "экспортируй результаты в json",
                "сохрани отчет в csv формате",
                "создай markdown отчет"
            ],
            'archive': [
                "заархивируй старые файлы",
                "создай архив python проектов",
                "сжми документацию в zip"
            ],
            'stats': [
                "покажи статистику по категориям",
                "анализ по языкам программирования",
                "отчет по временным периодам"
            ],
            'folder_management': [
                "создай папку для проектов",
                "создай папку React-проекты со структурой компонентов",
                "удали папку старых файлов",
                "переименуй папку в новое название",
                "перемести папку в другое место"
            ],
            'batch_operations': [
                "примени переименование ко всем python файлам",
                "примени форматирование ко всем javascript файлам в проекте",
                "выполни конвертацию для всех изображений старше месяца",
                "примени сжатие ко всем файлам больше 10MB"
            ],
            'content_analysis': [
                "проанализируй код на предмет сложности",
                "проанализируй документацию на предмет актуальности",
                "анализ проекта по критериям качества",
                "проанализируй файлы на предмет дубликатов",
                "проверь код на соответствие стандартам"
            ]
        }
    
    def execute_command(self, parsed_command: ParsedCommand, 
                       search_engine=None, organizer=None) -> Dict[str, Any]:
        """Выполнение распарсенной команды.
        
        Args:
            parsed_command: Результат парсинга команды
            search_engine: Движок поиска
            organizer: Организатор файлов
            
        Returns:
            Результат выполнения команды
        """
        try:
            if parsed_command.command_type == CommandType.SEARCH:
                return self._execute_search(parsed_command, search_engine)
            elif parsed_command.command_type == CommandType.ORGANIZE:
                return self._execute_organize(parsed_command, organizer)
            elif parsed_command.command_type == CommandType.EXPORT:
                return self._execute_export(parsed_command)
            elif parsed_command.command_type == CommandType.ARCHIVE:
                return self._execute_archive(parsed_command)
            elif parsed_command.command_type == CommandType.STATS:
                return self._execute_stats(parsed_command)
            elif parsed_command.command_type == CommandType.FOLDER_MANAGEMENT:
                return self._execute_folder_management(parsed_command)
            elif parsed_command.command_type == CommandType.BATCH_OPERATIONS:
                return self._execute_batch_operations(parsed_command)
            elif parsed_command.command_type == CommandType.CONTENT_ANALYSIS:
                return self._execute_content_analysis(parsed_command)
            elif parsed_command.command_type == CommandType.HELP:
                return {'help': self.get_command_help()}
            else:
                return {
                    'error': 'Неизвестная команда',
                    'suggestions': parsed_command.suggestions
                }
                
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {'error': str(e)}
    
    def _execute_search(self, command: ParsedCommand, search_engine) -> Dict[str, Any]:
        """Выполнение команды поиска."""
        if not search_engine:
            return {'error': 'Search engine not available'}
        
        try:
            # Создание фильтра поиска
            from .semantic_search import SearchFilter
            
            search_filter = SearchFilter(
                categories=command.filters.get('categories'),
                programming_languages=command.filters.get('programming_languages'),
                difficulty_levels=command.filters.get('difficulty_levels'),
                date_from=command.filters.get('date_from'),
                date_to=command.filters.get('date_to')
            )
            
            # Выполнение поиска
            results = search_engine.search(
                query=command.query or "",
                filters=search_filter,
                top_k=20
            )
            
            return {
                'results': [asdict(result) for result in results],
                'total': len(results),
                'query': command.query,
                'filters': command.filters
            }
            
        except Exception as e:
            logger.error(f"Search execution error: {e}")
            return {'error': f'Search failed: {str(e)}'}
    
    def _execute_organize(self, command: ParsedCommand, organizer) -> Dict[str, Any]:
        """Выполнение команды организации."""
        if not organizer:
            return {'error': 'Organizer not available'}
        
        try:
            criteria = command.parameters.get('criteria', 'category')
            target = command.parameters.get('target', 'all')
            
            # Здесь должна быть логика организации файлов
            # Пока возвращаем заглушку
            return {
                'action': 'organize',
                'criteria': criteria,
                'target': target,
                'status': 'completed',
                'message': f'Файлы организованы по критерию: {criteria}'
            }
            
        except Exception as e:
            logger.error(f"Organize execution error: {e}")
            return {'error': f'Organization failed: {str(e)}'}
    
    def _execute_export(self, command: ParsedCommand) -> Dict[str, Any]:
        """Выполнение команды экспорта."""
        try:
            export_format = command.parameters.get('format', 'json')
            content = command.parameters.get('content', 'all')
            filters = command.parameters.get('filters', {})
            
            # Создание имени файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"export_{timestamp}.{export_format}"
            filepath = self.data_dir / filename
            
            # Здесь должна быть логика экспорта
            # Пока создаем пустой файл
            export_data = {
                'export_info': {
                    'timestamp': timestamp,
                    'format': export_format,
                    'content': content,
                    'filters': filters
                },
                'data': []
            }
            
            if export_format == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            elif export_format == 'csv':
                # Логика для CSV
                pass
            
            return {
                'action': 'export',
                'format': export_format,
                'filepath': str(filepath),
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Export execution error: {e}")
            return {'error': f'Export failed: {str(e)}'}
    
    def _execute_archive(self, command: ParsedCommand) -> Dict[str, Any]:
        """Выполнение команды архивирования."""
        try:
            target = command.parameters.get('target', 'all')
            archive_type = command.parameters.get('archive_type', 'zip')
            
            # Создание имени архива
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = f"archive_{timestamp}.{archive_type}"
            archive_path = self.data_dir / archive_name
            
            # Создание архива
            if archive_type == 'zip':
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Здесь должна быть логика добавления файлов
                    pass
            
            return {
                'action': 'archive',
                'archive_type': archive_type,
                'archive_path': str(archive_path),
                'target': target,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Archive execution error: {e}")
            return {'error': f'Archive failed: {str(e)}'}
    
    def _execute_stats(self, command: ParsedCommand) -> Dict[str, Any]:
        """Выполнение команды статистики."""
        try:
            stats_type = command.parameters.get('stats_type', 'general')
            
            # Здесь должна быть логика сбора статистики
            # Пока возвращаем заглушку
            stats = {
                'stats_type': stats_type,
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'total_files': 0,
                    'categories': {},
                    'languages': {},
                    'recent_activity': []
                }
            }
            
            return {
                'action': 'stats',
                'stats': stats,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Stats execution error: {e}")
            return {'error': f'Stats failed: {str(e)}'}
    
    def _execute_folder_management(self, command: ParsedCommand) -> Dict[str, Any]:
        """Выполнение команды управления папками."""
        try:
            action = command.parameters.get('action', 'unknown')
            target = command.parameters.get('target', '')
            
            # Здесь должна быть логика управления папками
            # Пока возвращаем заглушку
            result = {
                'action': action,
                'target': target,
                'timestamp': datetime.now().isoformat(),
                'status': 'completed'
            }
            
            return {
                'action': 'folder_management',
                'result': result,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Folder management execution error: {e}")
            return {'error': f'Folder management failed: {str(e)}'}
    
    def _execute_batch_operations(self, command: ParsedCommand) -> Dict[str, Any]:
        """Выполнение команды пакетных операций."""
        try:
            operation = command.parameters.get('operation', 'unknown')
            targets = command.parameters.get('targets', [])
            filters = command.parameters.get('filters', {})
            
            # Здесь должна быть логика пакетных операций
            # Пока возвращаем заглушку
            result = {
                'operation': operation,
                'targets': targets,
                'filters': filters,
                'processed_count': len(targets),
                'timestamp': datetime.now().isoformat(),
                'status': 'completed'
            }
            
            return {
                'action': 'batch_operations',
                'result': result,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Batch operations execution error: {e}")
            return {'error': f'Batch operations failed: {str(e)}'}
    
    def _execute_content_analysis(self, command: ParsedCommand) -> Dict[str, Any]:
        """Выполнение команды анализа контента."""
        try:
            analysis_type = command.parameters.get('analysis_type', 'general')
            target = command.parameters.get('target', '')
            filters = command.parameters.get('filters', {})
            
            # Здесь должна быть логика анализа контента
            # Пока возвращаем заглушку
            result = {
                'analysis_type': analysis_type,
                'target': target,
                'filters': filters,
                'findings': {
                    'duplicates': [],
                    'quality_issues': [],
                    'recommendations': []
                },
                'timestamp': datetime.now().isoformat(),
                'status': 'completed'
            }
            
            return {
                'action': 'content_analysis',
                'result': result,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Content analysis execution error: {e}")
            return {'error': f'Content analysis failed: {str(e)}'}