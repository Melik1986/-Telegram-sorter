"""Модуль для автоматического извлечения метаданных из контента.

Этот модуль предоставляет функциональность для:
- Автоматического извлечения тегов из контента
- Определения сложности материала
- Анализа актуальности информации
- Извлечения дополнительных метаданных
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DifficultyLevel(Enum):
    """Уровни сложности материала."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ContentFreshness(Enum):
    """Уровни актуальности контента."""
    VERY_FRESH = "very_fresh"  # < 3 месяцев
    FRESH = "fresh"            # 3-12 месяцев
    MODERATE = "moderate"      # 1-2 года
    OUTDATED = "outdated"      # > 2 лет
    UNKNOWN = "unknown"        # Дата неизвестна

@dataclass
class ExtractedMetadata:
    """Структура для хранения извлеченных метаданных."""
    tags: List[str]
    difficulty_level: DifficultyLevel
    confidence_score: float
    content_freshness: ContentFreshness
    estimated_reading_time: int  # в минутах
    programming_languages: List[str]
    frameworks_libraries: List[str]
    topics: List[str]
    content_type: str
    quality_indicators: Dict[str, Any]
    extracted_dates: List[str]
    key_concepts: List[str]

class MetadataExtractor:
    """Класс для извлечения метаданных из контента."""
    
    def __init__(self):
        """Инициализация экстрактора метаданных."""
        self._init_patterns()
        self._init_difficulty_indicators()
        self._init_technology_patterns()
        
    def _init_patterns(self):
        """Инициализация паттернов для извлечения информации."""
        # Паттерны для извлечения дат
        self.date_patterns = [
            r'\b(\d{1,2}[./\-]\d{1,2}[./\-]\d{4})\b',  # DD/MM/YYYY или DD-MM-YYYY
            r'\b(\d{4}[./\-]\d{1,2}[./\-]\d{1,2})\b',  # YYYY/MM/DD или YYYY-MM-DD
            r'\b(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})\b',
            r'\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b'
        ]
        
        # Паттерны для извлечения версий
        self.version_patterns = [
            r'\bv?(\d+\.\d+(?:\.\d+)?)\b',
            r'\bversion\s+(\d+\.\d+(?:\.\d+)?)\b',
            r'\b(\d+\.\d+(?:\.\d+)?\s*(?:beta|alpha|rc|stable))\b'
        ]
        
        # Паттерны для извлечения ключевых концепций
        self.concept_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+Pattern|\s+Principle|\s+Method))\b',
            r'\b((?:design|architectural|programming)\s+pattern)\b',
            r'\b(best\s+practice)s?\b',
            r'\b(algorithm)s?\b',
            r'\b(data\s+structure)s?\b'
        ]
    
    def _init_difficulty_indicators(self):
        """Инициализация индикаторов сложности."""
        self.difficulty_indicators = {
            DifficultyLevel.BEGINNER: {
                'keywords': [
                    'beginner', 'начинающий', 'introduction', 'введение', 'basics', 'основы',
                    'getting started', 'first steps', 'tutorial', 'урок', 'simple', 'простой',
                    'easy', 'легкий', 'basic', 'базовый', 'fundamentals', 'основы'
                ],
                'negative_keywords': [
                    'advanced', 'expert', 'complex', 'sophisticated', 'enterprise',
                    'production', 'optimization', 'performance', 'architecture'
                ],
                'weight': 1.0
            },
            DifficultyLevel.INTERMEDIATE: {
                'keywords': [
                    'intermediate', 'средний', 'practical', 'практический', 'real-world',
                    'project', 'проект', 'implementation', 'реализация', 'building',
                    'создание', 'developing', 'разработка', 'working with', 'работа с'
                ],
                'negative_keywords': [],
                'weight': 1.0
            },
            DifficultyLevel.ADVANCED: {
                'keywords': [
                    'advanced', 'продвинутый', 'complex', 'сложный', 'deep dive',
                    'глубокое погружение', 'optimization', 'оптимизация', 'performance',
                    'производительность', 'architecture', 'архитектура', 'patterns',
                    'паттерны', 'scalability', 'масштабируемость'
                ],
                'negative_keywords': ['beginner', 'basic', 'simple', 'introduction'],
                'weight': 1.5
            },
            DifficultyLevel.EXPERT: {
                'keywords': [
                    'expert', 'экспертный', 'enterprise', 'корпоративный', 'production',
                    'продакшн', 'high-performance', 'высокопроизводительный', 'distributed',
                    'распределенный', 'microservices', 'микросервисы', 'kubernetes',
                    'docker', 'devops', 'security', 'безопасность', 'cryptography'
                ],
                'negative_keywords': ['beginner', 'basic', 'simple', 'tutorial'],
                'weight': 2.0
            }
        }
    
    def _init_technology_patterns(self):
        """Инициализация паттернов для распознавания технологий."""
        self.programming_languages = {
            'python': [r'\bpython\b', r'\.py\b', r'\bpip\b', r'\bdjango\b', r'\bflask\b'],
            'javascript': [r'\bjavascript\b', r'\bjs\b', r'\.js\b', r'\bnode\.?js\b', r'\bnpm\b'],
            'typescript': [r'\btypescript\b', r'\bts\b', r'\.ts\b', r'\btsc\b'],
            'java': [r'\bjava\b', r'\.java\b', r'\bspring\b', r'\bmaven\b', r'\bgradle\b'],
            'csharp': [r'\bc#\b', r'\bcsharp\b', r'\.cs\b', r'\b\.net\b', r'\bvisual studio\b'],
            'php': [r'\bphp\b', r'\.php\b', r'\blaravel\b', r'\bsymfony\b', r'\bcomposer\b'],
            'go': [r'\bgo\b', r'\bgolang\b', r'\.go\b'],
            'rust': [r'\brust\b', r'\.rs\b', r'\bcargo\b'],
            'cpp': [r'\bc\+\+\b', r'\bcpp\b', r'\.cpp\b', r'\.h\b'],
            'ruby': [r'\bruby\b', r'\.rb\b', r'\brails\b', r'\bgem\b']
        }
        
        self.frameworks_libraries = {
            'react': [r'\breact\b', r'\bjsx\b', r'\breact\.js\b'],
            'vue': [r'\bvue\b', r'\bvue\.js\b', r'\bnuxt\b'],
            'angular': [r'\bangular\b', r'\bangularjs\b', r'\bionic\b'],
            'django': [r'\bdjango\b', r'\bdjango\.py\b'],
            'flask': [r'\bflask\b'],
            'express': [r'\bexpress\b', r'\bexpress\.js\b'],
            'spring': [r'\bspring\b', r'\bspring boot\b'],
            'laravel': [r'\blaravel\b'],
            'rails': [r'\brails\b', r'\bruby on rails\b'],
            'nextjs': [r'\bnext\.js\b', r'\bnextjs\b'],
            'gatsby': [r'\bgatsby\b', r'\bgatsby\.js\b'],
            'svelte': [r'\bsvelte\b', r'\bsveltekit\b']
        }
    
    def extract_metadata(self, content: str, url: Optional[str] = None, 
                        title: Optional[str] = None) -> ExtractedMetadata:
        """Извлечение всех метаданных из контента."""
        try:
            # Базовая очистка контента
            cleaned_content = self._clean_content(content)
            
            # Извлечение различных типов метаданных
            tags = self._extract_tags(cleaned_content, title)
            difficulty = self._determine_difficulty(cleaned_content)
            freshness = self._analyze_content_freshness(cleaned_content, url)
            reading_time = self._estimate_reading_time(cleaned_content)
            prog_langs = self._extract_programming_languages(cleaned_content)
            frameworks = self._extract_frameworks_libraries(cleaned_content)
            topics = self._extract_topics(cleaned_content)
            content_type = self._determine_content_type(cleaned_content, url)
            quality = self._assess_quality_indicators(cleaned_content)
            dates = self._extract_dates(cleaned_content)
            concepts = self._extract_key_concepts(cleaned_content)
            
            # Вычисление общего уровня уверенности
            confidence = self._calculate_confidence_score(
                tags, difficulty, prog_langs, frameworks, topics
            )
            
            return ExtractedMetadata(
                tags=tags,
                difficulty_level=difficulty,
                confidence_score=confidence,
                content_freshness=freshness,
                estimated_reading_time=reading_time,
                programming_languages=prog_langs,
                frameworks_libraries=frameworks,
                topics=topics,
                content_type=content_type,
                quality_indicators=quality,
                extracted_dates=dates,
                key_concepts=concepts
            )
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            # Возвращаем базовые метаданные в случае ошибки
            return ExtractedMetadata(
                tags=[],
                difficulty_level=DifficultyLevel.INTERMEDIATE,
                confidence_score=0.1,
                content_freshness=ContentFreshness.UNKNOWN,
                estimated_reading_time=5,
                programming_languages=[],
                frameworks_libraries=[],
                topics=[],
                content_type="unknown",
                quality_indicators={},
                extracted_dates=[],
                key_concepts=[]
            )
    
    def _clean_content(self, content: str) -> str:
        """Очистка контента от лишних символов и форматирования."""
        # Удаление HTML тегов
        content = re.sub(r'<[^>]+>', ' ', content)
        # Удаление лишних пробелов
        content = re.sub(r'\s+', ' ', content)
        # Удаление специальных символов
        content = re.sub(r'[^\w\s\-.,!?()\[\]{}:;"\'/]', ' ', content)
        return content.strip()
    
    def _extract_tags(self, content: str, title: Optional[str] = None) -> List[str]:
        """Извлечение тегов из контента."""
        tags = set()
        content_lower = content.lower()
        
        # Извлечение тегов из заголовка
        if title:
            title_words = re.findall(r'\b\w+\b', title.lower())
            tags.update([word for word in title_words if len(word) > 2])
        
        # Технологические теги
        for lang, patterns in self.programming_languages.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    tags.add(lang)
        
        for framework, patterns in self.frameworks_libraries.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    tags.add(framework)
        
        # Общие технические теги
        tech_keywords = [
            'api', 'database', 'frontend', 'backend', 'fullstack', 'devops',
            'testing', 'deployment', 'security', 'performance', 'optimization',
            'tutorial', 'guide', 'documentation', 'example', 'project',
            'responsive', 'mobile', 'web', 'app', 'application', 'development'
        ]
        
        for keyword in tech_keywords:
            if keyword in content_lower:
                tags.add(keyword)
        
        # Ограничиваем количество тегов
        return list(tags)[:15]
    
    def _determine_difficulty(self, content: str) -> DifficultyLevel:
        """Определение уровня сложности контента."""
        content_lower = content.lower()
        scores = {level: 0.0 for level in DifficultyLevel}
        
        for level, indicators in self.difficulty_indicators.items():
            # Положительные индикаторы
            for keyword in indicators['keywords']:
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', content_lower))
                scores[level] += count * indicators['weight']
            
            # Отрицательные индикаторы
            for neg_keyword in indicators['negative_keywords']:
                count = len(re.findall(r'\b' + re.escape(neg_keyword) + r'\b', content_lower))
                scores[level] -= count * 0.5
        
        # Дополнительные эвристики
        word_count = len(content.split())
        if word_count > 2000:
            scores[DifficultyLevel.ADVANCED] += 1
            scores[DifficultyLevel.EXPERT] += 0.5
        
        # Сложные технические термины
        complex_terms = [
            'microservices', 'kubernetes', 'docker', 'devops', 'ci/cd',
            'distributed', 'scalability', 'performance', 'optimization',
            'architecture', 'design patterns', 'algorithms', 'data structures'
        ]
        
        for term in complex_terms:
            if term in content_lower:
                scores[DifficultyLevel.ADVANCED] += 1
                scores[DifficultyLevel.EXPERT] += 0.5
        
        # Возвращаем уровень с наивысшим счетом
        best_level = max(scores.keys(), key=lambda k: scores[k])
        return best_level if scores[best_level] > 0 else DifficultyLevel.INTERMEDIATE
    
    def _analyze_content_freshness(self, content: str, url: Optional[str] = None) -> ContentFreshness:
        """Анализ актуальности контента."""
        dates = self._extract_dates(content)
        current_year = datetime.now().year
        
        if not dates:
            # Если дат нет, анализируем по версиям и технологиям
            return self._analyze_freshness_by_technology(content)
        
        # Находим самую свежую дату
        latest_year = 0
        for date_str in dates:
            try:
                # Простое извлечение года из даты
                year_match = re.search(r'\b(20\d{2})\b', date_str)
                if year_match:
                    year = int(year_match.group(1))
                    latest_year = max(latest_year, year)
            except:
                continue
        
        if latest_year == 0:
            return ContentFreshness.UNKNOWN
        
        years_diff = current_year - latest_year
        
        if years_diff <= 0:
            return ContentFreshness.VERY_FRESH
        elif years_diff <= 1:
            return ContentFreshness.FRESH
        elif years_diff <= 2:
            return ContentFreshness.MODERATE
        else:
            return ContentFreshness.OUTDATED
    
    def _analyze_freshness_by_technology(self, content: str) -> ContentFreshness:
        """Анализ актуальности по упоминаемым технологиям."""
        content_lower = content.lower()
        
        # Современные технологии (указывают на свежесть)
        modern_tech = [
            'react hooks', 'vue 3', 'angular 15', 'angular 16', 'angular 17',
            'next.js 13', 'next.js 14', 'typescript 5', 'python 3.11', 'python 3.12',
            'node.js 18', 'node.js 20', 'docker compose', 'kubernetes',
            'tailwind css', 'vite', 'pnpm', 'bun'
        ]
        
        # Устаревшие технологии
        outdated_tech = [
            'jquery', 'angularjs', 'bower', 'grunt', 'python 2',
            'node.js 12', 'node.js 14', 'internet explorer', 'flash'
        ]
        
        modern_score = sum(1 for tech in modern_tech if tech in content_lower)
        outdated_score = sum(1 for tech in outdated_tech if tech in content_lower)
        
        if modern_score > outdated_score and modern_score > 0:
            return ContentFreshness.FRESH
        elif outdated_score > modern_score and outdated_score > 0:
            return ContentFreshness.OUTDATED
        else:
            return ContentFreshness.MODERATE
    
    def _estimate_reading_time(self, content: str) -> int:
        """Оценка времени чтения в минутах."""
        words = len(content.split())
        # Средняя скорость чтения 200-250 слов в минуту
        reading_time = max(1, words // 225)
        return min(reading_time, 60)  # Максимум 60 минут
    
    def _extract_programming_languages(self, content: str) -> List[str]:
        """Извлечение языков программирования."""
        found_languages = []
        content_lower = content.lower()
        
        for lang, patterns in self.programming_languages.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    found_languages.append(lang)
                    break
        
        return list(set(found_languages))[:5]
    
    def _extract_frameworks_libraries(self, content: str) -> List[str]:
        """Извлечение фреймворков и библиотек."""
        found_frameworks = []
        content_lower = content.lower()
        
        for framework, patterns in self.frameworks_libraries.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    found_frameworks.append(framework)
                    break
        
        return list(set(found_frameworks))[:8]
    
    def _extract_topics(self, content: str) -> List[str]:
        """Извлечение основных тем."""
        topics = []
        content_lower = content.lower()
        
        # Основные темы разработки
        topic_keywords = {
            'web_development': ['web development', 'веб-разработка', 'frontend', 'backend'],
            'mobile_development': ['mobile', 'мобильная разработка', 'ios', 'android', 'react native'],
            'data_science': ['data science', 'машинное обучение', 'machine learning', 'ai', 'искусственный интеллект'],
            'devops': ['devops', 'ci/cd', 'deployment', 'развертывание', 'docker', 'kubernetes'],
            'testing': ['testing', 'тестирование', 'unit test', 'integration test'],
            'security': ['security', 'безопасность', 'authentication', 'authorization'],
            'performance': ['performance', 'производительность', 'optimization', 'оптимизация'],
            'database': ['database', 'база данных', 'sql', 'nosql', 'mongodb', 'postgresql']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)
        
        return topics[:6]
    
    def _determine_content_type(self, content: str, url: Optional[str] = None) -> str:
        """Определение типа контента."""
        content_lower = content.lower()
        
        # Анализ по URL
        if url:
            url_lower = url.lower()
            if 'github.com' in url_lower:
                return 'code_repository'
            elif 'youtube.com' in url_lower or 'vimeo.com' in url_lower:
                return 'video'
            elif 'stackoverflow.com' in url_lower:
                return 'qa_discussion'
            elif any(domain in url_lower for domain in ['medium.com', 'dev.to', 'habr.com']):
                return 'article'
        
        # Анализ по содержимому
        if any(word in content_lower for word in ['tutorial', 'урок', 'step by step', 'пошагово']):
            return 'tutorial'
        elif any(word in content_lower for word in ['documentation', 'docs', 'документация', 'api reference']):
            return 'documentation'
        elif any(word in content_lower for word in ['example', 'пример', 'demo', 'демо', 'snippet']):
            return 'code_example'
        elif any(word in content_lower for word in ['course', 'курс', 'lesson', 'урок']):
            return 'course'
        elif any(word in content_lower for word in ['news', 'новости', 'announcement', 'объявление']):
            return 'news'
        else:
            return 'article'
    
    def _assess_quality_indicators(self, content: str) -> Dict[str, Any]:
        """Оценка индикаторов качества контента."""
        indicators = {}
        
        # Длина контента
        word_count = len(content.split())
        indicators['word_count'] = word_count
        indicators['content_length'] = 'short' if word_count < 300 else 'medium' if word_count < 1000 else 'long'
        
        # Наличие кода
        code_blocks = len(re.findall(r'```[\s\S]*?```|`[^`]+`', content))
        indicators['has_code_examples'] = code_blocks > 0
        indicators['code_blocks_count'] = code_blocks
        
        # Наличие ссылок
        links = len(re.findall(r'https?://[^\s]+', content))
        indicators['external_links_count'] = links
        
        # Структурированность (заголовки)
        headers = len(re.findall(r'^#+\s+', content, re.MULTILINE))
        indicators['has_structure'] = headers > 0
        indicators['headers_count'] = headers
        
        # Наличие списков
        lists = len(re.findall(r'^[\*\-\+]\s+|^\d+\.\s+', content, re.MULTILINE))
        indicators['has_lists'] = lists > 0
        
        return indicators
    
    def _extract_dates(self, content: str) -> List[str]:
        """Извлечение дат из контента."""
        dates = []
        
        for pattern in self.date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            dates.extend(matches)
        
        return list(set(dates))[:5]
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Извлечение ключевых концепций."""
        concepts = []
        
        for pattern in self.concept_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            concepts.extend([match.lower() if isinstance(match, str) else match[0].lower() for match in matches])
        
        # Дополнительные концепции
        additional_concepts = [
            'solid principles', 'design patterns', 'mvc', 'mvvm', 'rest api',
            'graphql', 'microservices', 'monolith', 'serverless', 'spa',
            'responsive design', 'mobile first', 'progressive web app'
        ]
        
        content_lower = content.lower()
        for concept in additional_concepts:
            if concept in content_lower:
                concepts.append(concept)
        
        return list(set(concepts))[:10]
    
    def _calculate_confidence_score(self, tags: List[str], difficulty: DifficultyLevel,
                                  prog_langs: List[str], frameworks: List[str],
                                  topics: List[str]) -> float:
        """Вычисление общего уровня уверенности в извлеченных метаданных."""
        score = 0.0
        
        # Базовый счет за наличие данных
        if tags:
            score += 0.2
        if prog_langs:
            score += 0.2
        if frameworks:
            score += 0.2
        if topics:
            score += 0.2
        
        # Бонус за количество извлеченной информации
        total_items = len(tags) + len(prog_langs) + len(frameworks) + len(topics)
        if total_items >= 5:
            score += 0.1
        if total_items >= 10:
            score += 0.1
        
        return min(1.0, score)