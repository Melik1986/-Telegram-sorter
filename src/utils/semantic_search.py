"""Модуль для семантического поиска по содержимому.

Этот модуль предоставляет функциональность для:
- Семантического поиска по содержимому с использованием векторных представлений
- Поиска по метаданным и тегам
- Фильтрации по категориям и датам
- Ранжирования результатов по релевантности
"""

import logging
import pickle
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import re
from collections import defaultdict

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import faiss
    ADVANCED_SEARCH_AVAILABLE = True
except ImportError:
    ADVANCED_SEARCH_AVAILABLE = False
    np = None
    SentenceTransformer = None
    faiss = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    TfidfVectorizer = None
    cosine_similarity = None

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Результат поиска."""
    file_path: str
    title: str
    content_preview: str
    category: str
    subcategory: Optional[str]
    confidence: float
    relevance_score: float
    metadata: Dict[str, Any]
    tags: List[str]
    programming_languages: List[str]
    created_date: Optional[str]
    modified_date: Optional[str]
    match_type: str  # 'semantic', 'keyword', 'metadata', 'tag'
    matched_terms: List[str]

@dataclass
class SearchFilter:
    """Фильтры для поиска."""
    categories: Optional[List[str]] = None
    subcategories: Optional[List[str]] = None
    programming_languages: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    difficulty_levels: Optional[List[str]] = None
    content_types: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    file_extensions: Optional[List[str]] = None

class SemanticSearchEngine:
    """Улучшенный движок семантического поиска с поддержкой фильтрации и метаданных."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', cache_dir: str = None, data_dir: str = None):
        """Инициализация поискового движка.
        
        Args:
            model_name: Название модели sentence transformer
            cache_dir: Директория для кэширования эмбеддингов и индекса
            data_dir: Директория с данными для SQLite индекса
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or 'cache/semantic_search'
        self.data_dir = Path(data_dir) if data_dir else Path('data')
        
        # Создание директорий
        os.makedirs(self.cache_dir, exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        # Инициализация компонентов
        self.model = None
        self.index = None
        self.resource_ids = []  # Соответствие позиций FAISS индекса и ID ресурсов
        self.embeddings_cache = {}  # Кэш эмбеддингов ресурсов
        
        # База данных для метаданных и быстрого поиска
        self.db_path = self.data_dir / "enhanced_search_index.db"
        
        # Инициализация
        self._init_database()
        self._load_model()
        self._init_fallback_search()
        self._load_stopwords()
        
        logger.info(f"Enhanced semantic search engine initialized. Advanced: {ADVANCED_SEARCH_AVAILABLE}")
    
    def _init_database(self):
        """Инициализация базы данных для расширенного поиска."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS enhanced_search_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id TEXT UNIQUE NOT NULL,
                    file_path TEXT,
                    title TEXT,
                    content TEXT,
                    content_preview TEXT,
                    category TEXT,
                    subcategory TEXT,
                    confidence REAL,
                    metadata TEXT,
                    tags TEXT,
                    programming_languages TEXT,
                    frameworks_libraries TEXT,
                    topics TEXT,
                    difficulty_level TEXT,
                    content_type TEXT,
                    created_date TEXT,
                    modified_date TEXT,
                    indexed_date TEXT,
                    content_hash TEXT,
                    embedding_vector BLOB
                )
            ''')
            
            # Создание индексов для быстрого поиска
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_category ON enhanced_search_index(category)',
                'CREATE INDEX IF NOT EXISTS idx_subcategory ON enhanced_search_index(subcategory)',
                'CREATE INDEX IF NOT EXISTS idx_difficulty ON enhanced_search_index(difficulty_level)',
                'CREATE INDEX IF NOT EXISTS idx_content_type ON enhanced_search_index(content_type)',
                'CREATE INDEX IF NOT EXISTS idx_created_date ON enhanced_search_index(created_date)',
                'CREATE INDEX IF NOT EXISTS idx_confidence ON enhanced_search_index(confidence)',
                'CREATE INDEX IF NOT EXISTS idx_title ON enhanced_search_index(title)',
                'CREATE INDEX IF NOT EXISTS idx_content ON enhanced_search_index(content)'
            ]
            
            for index_sql in indexes:
                self.conn.execute(index_sql)
            
            self.conn.commit()
            logger.info("Enhanced search database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing enhanced search database: {e}")
            raise
    
    def _load_model(self):
        """Загрузка модели sentence transformer."""
        if not ADVANCED_SEARCH_AVAILABLE:
            logger.warning("Advanced search libraries not available. Using fallback search only.")
            return
        
        try:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model = None
    
    def _init_fallback_search(self):
        """Инициализация резервного поиска с TF-IDF."""
        if SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8,
                lowercase=True,
                strip_accents='unicode'
            )
            self.tfidf_matrix = None
            logger.info("TF-IDF fallback search initialized")
        else:
            self.tfidf_vectorizer = None
            logger.info("Using simple keyword matching as fallback")
    
    def _load_stopwords(self):
        """Загрузка стоп-слов."""
        self.stopwords = set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'this', 'that',
            'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
            'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his',
            'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself',
            'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who',
            'whom', 'whose', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
            'do', 'does', 'did', 'doing', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'shall'
        ])
    
    def _get_text_for_embedding(self, resource: Dict) -> str:
        """Извлечение текста из ресурса для создания эмбеддинга.
        
        Args:
            resource: Словарь с данными ресурса
            
        Returns:
            Объединенный текст для эмбеддинга
        """
        text_parts = []
        
        # Добавление основного контента
        if resource.get('content'):
            text_parts.append(resource['content'])
        
        # Добавление описания
        if resource.get('description'):
            text_parts.append(resource['description'])
        
        # Добавление заголовка с повышенным весом
        if resource.get('title'):
            text_parts.append(f"Title: {resource['title']} {resource['title']}")
        
        # Добавление категории и подкатегории
        if resource.get('category'):
            text_parts.append(f"Category: {resource['category']}")
        
        if resource.get('subcategory'):
            text_parts.append(f"Subcategory: {resource['subcategory']}")
        
        # Добавление тегов
        if resource.get('tags'):
            tags = resource['tags'] if isinstance(resource['tags'], list) else [resource['tags']]
            text_parts.append(f"Tags: {' '.join(tags)}")
        
        # Добавление языков программирования
        if resource.get('programming_languages'):
            langs = resource['programming_languages'] if isinstance(resource['programming_languages'], list) else [resource['programming_languages']]
            text_parts.append(f"Programming languages: {' '.join(langs)}")
        
        # Добавление типа файла
        if resource.get('file_type'):
            text_parts.append(f"File type: {resource['file_type']}")
        
        return ' '.join(text_parts)
    
    def add_resource(self, resource_id: str, resource: Dict):
        """Добавление ресурса в индекс семантического поиска.
        
        Args:
            resource_id: Уникальный идентификатор ресурса
            resource: Словарь с данными ресурса
        """
        try:
            # Извлечение текста для эмбеддинга
            text = self._get_text_for_embedding(resource)
            
            if not text.strip():
                logger.warning(f"Empty text for resource {resource_id}, skipping")
                return
            
            # Создание эмбеддинга (если доступно)
            embedding = None
            if self.model:
                embedding = self.model.encode([text])[0]
                self.embeddings_cache[resource_id] = embedding
                self._add_to_faiss_index(resource_id, embedding)
            
            # Сохранение в базу данных
            self._save_to_database(resource_id, resource, text, embedding)
            
            # Обновление TF-IDF матрицы
            if self.tfidf_vectorizer:
                self._update_tfidf_matrix()
            
            logger.debug(f"Added resource {resource_id} to enhanced search index")
            
        except Exception as e:
            logger.error(f"Failed to add resource {resource_id} to enhanced search: {e}")
    
    def _add_to_faiss_index(self, resource_id: str, embedding: np.ndarray):
        """Добавление эмбеддинга в FAISS индекс.
        
        Args:
            resource_id: Идентификатор ресурса
            embedding: Вектор эмбеддинга ресурса
        """
        if not ADVANCED_SEARCH_AVAILABLE:
            return
        
        # Инициализация индекса при необходимости
        if self.index is None:
            dimension = len(embedding)
            self.index = faiss.IndexFlatIP(dimension)  # Внутреннее произведение для косинусного сходства
            self.resource_ids = []
        
        # Нормализация эмбеддинга для косинусного сходства
        normalized_embedding = embedding / np.linalg.norm(embedding)
        
        # Добавление в индекс
        self.index.add(normalized_embedding.reshape(1, -1))
        self.resource_ids.append(resource_id)
    
    def _save_to_database(self, resource_id: str, resource: Dict, text: str, embedding: Optional[np.ndarray]):
        """Сохранение ресурса в базу данных."""
        try:
            # Подготовка данных
            current_time = datetime.now().isoformat()
            content_hash = str(hash(text))
            
            # Сериализация сложных данных
            metadata_json = json.dumps(resource.get('metadata', {}), ensure_ascii=False)
            tags_json = json.dumps(resource.get('tags', []), ensure_ascii=False)
            prog_langs_json = json.dumps(resource.get('programming_languages', []), ensure_ascii=False)
            frameworks_json = json.dumps(resource.get('frameworks_libraries', []), ensure_ascii=False)
            topics_json = json.dumps(resource.get('topics', []), ensure_ascii=False)
            
            # Сериализация эмбеддинга
            embedding_blob = None
            if embedding is not None:
                embedding_blob = pickle.dumps(embedding)
            
            # Создание превью контента
            content_preview = self._create_content_preview(resource.get('content', ''))
            
            # Получение дат файла
            file_path = resource.get('file_path', '')
            created_date = resource.get('created_date')
            modified_date = resource.get('modified_date')
            
            if file_path and Path(file_path).exists():
                try:
                    stat = Path(file_path).stat()
                    if not created_date:
                        created_date = datetime.fromtimestamp(stat.st_ctime).isoformat()
                    if not modified_date:
                        modified_date = datetime.fromtimestamp(stat.st_mtime).isoformat()
                except:
                    pass
            
            # Сохранение в базу данных
            self.conn.execute('''
                INSERT OR REPLACE INTO enhanced_search_index (
                    resource_id, file_path, title, content, content_preview, category, subcategory,
                    confidence, metadata, tags, programming_languages, frameworks_libraries,
                    topics, difficulty_level, content_type, created_date, modified_date,
                    indexed_date, content_hash, embedding_vector
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                resource_id, file_path, resource.get('title', ''), text, content_preview,
                resource.get('category', ''), resource.get('subcategory'),
                resource.get('confidence', 0.0), metadata_json, tags_json, prog_langs_json,
                frameworks_json, topics_json, resource.get('difficulty_level'),
                resource.get('content_type'), created_date, modified_date,
                current_time, content_hash, embedding_blob
            ))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error saving resource {resource_id} to database: {e}")
    
    def _create_content_preview(self, content: str, max_length: int = 300) -> str:
        """Создание превью контента."""
        if not content:
            return ""
        
        # Удаление лишних пробелов и переносов строк
        cleaned = re.sub(r'\s+', ' ', content.strip())
        
        if len(cleaned) <= max_length:
            return cleaned
        
        # Обрезка по словам
        words = cleaned.split()
        preview = ""
        for word in words:
            if len(preview + " " + word) > max_length - 3:
                break
            preview += (" " if preview else "") + word
        
        return preview + "..."
    
    def _update_tfidf_matrix(self):
        """Обновление TF-IDF матрицы."""
        if not self.tfidf_vectorizer:
            return
        
        try:
            # Получение всех документов
            cursor = self.conn.execute('SELECT resource_id, content FROM enhanced_search_index')
            documents = cursor.fetchall()
            
            if not documents:
                return
            
            # Подготовка текстов для векторизации
            texts = [doc[1] for doc in documents]
            resource_ids = [doc[0] for doc in documents]
            
            # Создание TF-IDF матрицы
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Сохранение соответствия индексов и ID ресурсов
            self.tfidf_index_to_id = {i: rid for i, rid in enumerate(resource_ids)}
            self.tfidf_id_to_index = {rid: i for i, rid in enumerate(resource_ids)}
            
            logger.debug(f"TF-IDF matrix updated with {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error updating TF-IDF matrix: {e}")
    
    def search(self, query: str, filters: Optional[SearchFilter] = None,
              top_k: int = 20, min_similarity: float = 0.3) -> List[SearchResult]:
        """Выполнение расширенного поиска.
        
        Args:
            query: Поисковый запрос
            filters: Фильтры поиска
            top_k: Максимальное количество результатов
            min_similarity: Минимальный порог сходства
            
        Returns:
            Список результатов поиска
        """
        try:
            # Нормализация запроса
            normalized_query = self._normalize_query(query)
            
            # Получение результатов разными методами
            results = []
            
            # Семантический поиск (если доступен)
            if self.model and self.index:
                semantic_results = self._semantic_search(normalized_query, min_similarity)
                results.extend(semantic_results)
            
            # TF-IDF поиск (если доступен)
            if self.tfidf_vectorizer and self.tfidf_matrix is not None:
                tfidf_results = self._tfidf_search(normalized_query, min_similarity)
                results.extend(tfidf_results)
            
            # Поиск по ключевым словам
            keyword_results = self._keyword_search(normalized_query)
            results.extend(keyword_results)
            
            # Поиск по метаданным
            metadata_results = self._metadata_search(normalized_query)
            results.extend(metadata_results)
            
            # Поиск по тегам
            tag_results = self._tag_search(normalized_query)
            results.extend(tag_results)
            
            # Объединение и ранжирование результатов
            merged_results = self._merge_and_rank_results(results)
            
            # Применение фильтров
            filtered_results = self._apply_filters(merged_results, filters)
            
            # Ограничение количества результатов
            final_results = filtered_results[:top_k]
            
            logger.info(f"Enhanced search completed: {len(final_results)} results for query '{query}'")
            return final_results
            
        except Exception as e:
            logger.error(f"Error during enhanced search: {e}")
            return []
    
    def _normalize_query(self, query: str) -> str:
        """Нормализация поискового запроса."""
        # Приведение к нижнему регистру
        normalized = query.lower().strip()
        
        # Удаление лишних пробелов
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Удаление специальных символов (кроме важных для программирования)
        normalized = re.sub(r'[^\w\s\-\.\+\#]', ' ', normalized)
        
        return normalized
    
    def _semantic_search(self, query: str, min_similarity: float) -> List[Tuple[str, float, str]]:
        """Семантический поиск с использованием FAISS."""
        if not self.model or not self.index or len(self.resource_ids) == 0:
            return []
        
        try:
            # Создание эмбеддинга запроса
            query_embedding = self.model.encode([query])[0]
            
            # Нормализация для косинусного сходства
            normalized_query = query_embedding / np.linalg.norm(query_embedding)
            
            # Поиск в FAISS индексе
            similarities, indices = self.index.search(
                normalized_query.reshape(1, -1),
                min(len(self.resource_ids), 50)
            )
            
            # Фильтрация результатов по минимальному сходству
            results = []
            for similarity, idx in zip(similarities[0], indices[0]):
                if similarity >= min_similarity and idx < len(self.resource_ids):
                    resource_id = self.resource_ids[idx]
                    results.append((resource_id, float(similarity), 'semantic'))
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _tfidf_search(self, query: str, min_similarity: float) -> List[Tuple[str, float, str]]:
        """Поиск с использованием TF-IDF."""
        if not self.tfidf_vectorizer or self.tfidf_matrix is None:
            return []
        
        try:
            # Векторизация запроса
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Вычисление косинусного сходства
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
            
            # Получение топ результатов
            top_indices = similarities.argsort()[-50:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] >= min_similarity:
                    resource_id = self.tfidf_index_to_id[idx]
                    results.append((resource_id, float(similarities[idx]), 'tfidf'))
            
            return results
            
        except Exception as e:
            logger.error(f"TF-IDF search failed: {e}")
            return []
    
    def _keyword_search(self, query: str) -> List[Tuple[str, float, str]]:
        """Поиск по ключевым словам."""
        try:
            keywords = [word for word in query.split() if word not in self.stopwords and len(word) > 2]
            
            if not keywords:
                return []
            
            # Построение SQL запроса
            conditions = []
            params = []
            
            for keyword in keywords:
                conditions.append('(title LIKE ? OR content LIKE ?)')
                params.extend([f'%{keyword}%', f'%{keyword}%'])
            
            sql = f'''
                SELECT resource_id, 
                       ({" + ".join(["(CASE WHEN title LIKE ? THEN 2 ELSE 0 END) + (CASE WHEN content LIKE ? THEN 1 ELSE 0 END)" for _ in keywords])}) as score
                FROM enhanced_search_index 
                WHERE {" AND ".join(conditions)}
                ORDER BY score DESC
                LIMIT 50
            '''
            
            # Дублирование параметров для подсчета очков
            score_params = []
            for keyword in keywords:
                score_params.extend([f'%{keyword}%', f'%{keyword}%'])
            
            cursor = self.conn.execute(sql, score_params + params)
            rows = cursor.fetchall()
            
            results = []
            for resource_id, score in rows:
                if score > 0:
                    relevance = min(1.0, score / (len(keywords) * 2))  # Нормализация
                    results.append((resource_id, relevance, 'keyword'))
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _metadata_search(self, query: str) -> List[Tuple[str, float, str]]:
        """Поиск по метаданным."""
        try:
            cursor = self.conn.execute(
                'SELECT resource_id FROM enhanced_search_index WHERE metadata LIKE ?',
                (f'%{query}%',)
            )
            rows = cursor.fetchall()
            
            results = []
            for (resource_id,) in rows:
                results.append((resource_id, 0.3, 'metadata'))  # Базовая релевантность
            
            return results
            
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return []
    
    def _tag_search(self, query: str) -> List[Tuple[str, float, str]]:
        """Поиск по тегам."""
        try:
            cursor = self.conn.execute(
                'SELECT resource_id, tags FROM enhanced_search_index WHERE tags LIKE ?',
                (f'%{query}%',)
            )
            rows = cursor.fetchall()
            
            results = []
            for resource_id, tags_json in rows:
                try:
                    tags = json.loads(tags_json)
                    matching_tags = [tag for tag in tags if query.lower() in tag.lower()]
                    
                    if matching_tags:
                        results.append((resource_id, 0.4, 'tag'))  # Высокая релевантность для тегов
                except:
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Tag search failed: {e}")
            return []
    
    def _merge_and_rank_results(self, results: List[Tuple[str, float, str]]) -> List[SearchResult]:
        """Объединение и ранжирование результатов."""
        # Группировка по resource_id
        grouped = defaultdict(list)
        for resource_id, score, match_type in results:
            grouped[resource_id].append((score, match_type))
        
        # Создание финальных результатов
        final_results = []
        for resource_id, scores_and_types in grouped.items():
            # Комбинирование очков
            max_score = max(score for score, _ in scores_and_types)
            avg_score = sum(score for score, _ in scores_and_types) / len(scores_and_types)
            combined_score = (max_score + avg_score) / 2
            
            # Объединение типов совпадений
            match_types = list(set(match_type for _, match_type in scores_and_types))
            
            # Создание объекта результата
            search_result = self._create_search_result(resource_id, combined_score, match_types)
            if search_result:
                final_results.append(search_result)
        
        # Сортировка по релевантности
        final_results.sort(key=lambda x: (x.relevance_score, x.confidence), reverse=True)
        
        return final_results
    
    def _create_search_result(self, resource_id: str, relevance_score: float, match_types: List[str]) -> Optional[SearchResult]:
        """Создание объекта результата поиска."""
        try:
            cursor = self.conn.execute(
                '''SELECT file_path, title, content_preview, category, subcategory, confidence,
                          metadata, tags, programming_languages, created_date, modified_date
                   FROM enhanced_search_index WHERE resource_id = ?''',
                (resource_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            file_path, title, content_preview, category, subcategory, confidence, \
            metadata_json, tags_json, prog_langs_json, created_date, modified_date = row
            
            # Парсинг JSON данных
            try:
                metadata = json.loads(metadata_json) if metadata_json else {}
                tags = json.loads(tags_json) if tags_json else []
                programming_languages = json.loads(prog_langs_json) if prog_langs_json else []
            except:
                metadata = {}
                tags = []
                programming_languages = []
            
            return SearchResult(
                file_path=file_path or "",
                title=title or "",
                content_preview=content_preview or "",
                category=category or "",
                subcategory=subcategory,
                confidence=confidence or 0.0,
                relevance_score=relevance_score,
                metadata=metadata,
                tags=tags,
                programming_languages=programming_languages,
                created_date=created_date,
                modified_date=modified_date,
                match_type=', '.join(match_types),
                matched_terms=[]
            )
            
        except Exception as e:
            logger.error(f"Error creating search result for {resource_id}: {e}")
            return None
    
    def _apply_filters(self, results: List[SearchResult], filters: Optional[SearchFilter]) -> List[SearchResult]:
        """Применение фильтров к результатам поиска."""
        if not filters:
            return results
        
        filtered = []
        
        for result in results:
            # Фильтр по категориям
            if filters.categories and result.category not in filters.categories:
                continue
            
            # Фильтр по подкатегориям
            if filters.subcategories and result.subcategory not in filters.subcategories:
                continue
            
            # Фильтр по языкам программирования
            if filters.programming_languages:
                if not any(lang in result.programming_languages 
                          for lang in filters.programming_languages):
                    continue
            
            # Фильтр по тегам
            if filters.tags:
                if not any(tag in result.tags for tag in filters.tags):
                    continue
            
            # Фильтр по уверенности
            if filters.min_confidence and result.confidence < filters.min_confidence:
                continue
            
            # Фильтр по датам
            if filters.date_from or filters.date_to:
                result_date = None
                if result.created_date:
                    try:
                        result_date = datetime.fromisoformat(result.created_date.replace('Z', '+00:00'))
                    except:
                        pass
                
                if result_date:
                    if filters.date_from and result_date < filters.date_from:
                        continue
                    if filters.date_to and result_date > filters.date_to:
                        continue
            
            # Фильтр по расширениям файлов
            if filters.file_extensions:
                file_ext = Path(result.file_path).suffix.lower()
                if file_ext not in filters.file_extensions:
                    continue
            
            filtered.append(result)
        
        return filtered
    
    # Методы совместимости с оригинальным API
    def remove_resource(self, resource_id: str):
        """Удаление ресурса из индекса поиска."""
        try:
            # Удаление из базы данных
            self.conn.execute('DELETE FROM enhanced_search_index WHERE resource_id = ?', (resource_id,))
            self.conn.commit()
            
            # Удаление из кэша эмбеддингов
            if resource_id in self.embeddings_cache:
                del self.embeddings_cache[resource_id]
            
            # Для FAISS нужно перестроить индекс
            if resource_id in self.resource_ids:
                self._rebuild_faiss_index_without_resource(resource_id)
            
            # Обновление TF-IDF матрицы
            if self.tfidf_vectorizer:
                self._update_tfidf_matrix()
            
            logger.debug(f"Removed resource {resource_id} from enhanced search index")
            
        except Exception as e:
            logger.error(f"Failed to remove resource {resource_id}: {e}")
    
    def _rebuild_faiss_index_without_resource(self, resource_id_to_remove: str):
        """Перестройка FAISS индекса без указанного ресурса."""
        if not ADVANCED_SEARCH_AVAILABLE or not self.resource_ids:
            return
        
        # Получение эмбеддингов для всех ресурсов кроме удаляемого
        remaining_embeddings = []
        remaining_ids = []
        
        for resource_id in self.resource_ids:
            if resource_id != resource_id_to_remove and resource_id in self.embeddings_cache:
                remaining_embeddings.append(self.embeddings_cache[resource_id])
                remaining_ids.append(resource_id)
        
        # Перестройка индекса
        if remaining_embeddings:
            dimension = len(remaining_embeddings[0])
            self.index = faiss.IndexFlatIP(dimension)
            
            # Нормализация и добавление эмбеддингов
            for embedding in remaining_embeddings:
                normalized = embedding / np.linalg.norm(embedding)
                self.index.add(normalized.reshape(1, -1))
            
            self.resource_ids = remaining_ids
        else:
            # Нет оставшихся ресурсов
            self.index = None
            self.resource_ids = []
    
    def update_resource(self, resource_id: str, resource: Dict):
        """Обновление ресурса в индексе поиска."""
        # Удаление старой версии и добавление новой
        self.remove_resource(resource_id)
        self.add_resource(resource_id, resource)
    
    def save_index(self, filepath: str = None):
        """Сохранение индекса и метаданных на диск."""
        if not filepath:
            filepath = os.path.join(self.cache_dir, 'enhanced_semantic_index')
        
        try:
            # Сохранение FAISS индекса
            if self.index and ADVANCED_SEARCH_AVAILABLE:
                faiss.write_index(self.index, f"{filepath}.faiss")
            
            # Сохранение метаданных
            metadata = {
                'resource_ids': self.resource_ids,
                'embeddings_cache': self.embeddings_cache,
                'model_name': self.model_name
            }
            
            with open(f"{filepath}.pkl", 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Saved enhanced semantic search index to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save enhanced semantic search index: {e}")
    
    def load_index(self, filepath: str = None):
        """Загрузка индекса и метаданных с диска."""
        if not filepath:
            filepath = os.path.join(self.cache_dir, 'enhanced_semantic_index')
        
        try:
            # Загрузка FAISS индекса
            if os.path.exists(f"{filepath}.faiss") and ADVANCED_SEARCH_AVAILABLE:
                self.index = faiss.read_index(f"{filepath}.faiss")
            
            # Загрузка метаданных
            if os.path.exists(f"{filepath}.pkl"):
                with open(f"{filepath}.pkl", 'rb') as f:
                    metadata = pickle.load(f)
                
                self.resource_ids = metadata.get('resource_ids', [])
                self.embeddings_cache = metadata.get('embeddings_cache', {})
                
                # Проверка совместимости модели
                saved_model = metadata.get('model_name')
                if saved_model and saved_model != self.model_name:
                    logger.warning(f"Model mismatch: saved={saved_model}, current={self.model_name}")
            
            logger.info(f"Loaded enhanced semantic search index from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load enhanced semantic search index: {e}")
    
    def get_stats(self) -> Dict:
        """Получение статистики поискового движка."""
        try:
            # Базовая статистика
            stats = {
                'model_name': self.model_name,
                'advanced_search_available': ADVANCED_SEARCH_AVAILABLE,
                'sklearn_available': SKLEARN_AVAILABLE,
                'total_resources': len(self.resource_ids),
                'cache_size': len(self.embeddings_cache)
            }
            
            # Статистика FAISS
            if self.index:
                stats.update({
                    'faiss_index_size': self.index.ntotal,
                    'faiss_dimension': self.index.d
                })
            
            # Статистика из базы данных
            cursor = self.conn.execute('SELECT COUNT(*) FROM enhanced_search_index')
            stats['database_records'] = cursor.fetchone()[0]
            
            # Статистика по категориям
            cursor = self.conn.execute(
                'SELECT category, COUNT(*) FROM enhanced_search_index GROUP BY category'
            )
            stats['categories'] = dict(cursor.fetchall())
            
            # Статистика по языкам программирования
            cursor = self.conn.execute('SELECT programming_languages FROM enhanced_search_index')
            lang_counts = defaultdict(int)
            for (prog_langs_json,) in cursor.fetchall():
                try:
                    langs = json.loads(prog_langs_json)
                    for lang in langs:
                        lang_counts[lang] += 1
                except:
                    continue
            stats['programming_languages'] = dict(lang_counts)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting enhanced search stats: {e}")
            return {'error': str(e)}
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Получение предложений для автодополнения поиска."""
        try:
            suggestions = set()
            
            # Поиск в заголовках
            cursor = self.conn.execute(
                'SELECT DISTINCT title FROM enhanced_search_index WHERE title LIKE ? LIMIT ?',
                (f'%{partial_query}%', limit)
            )
            for (title,) in cursor.fetchall():
                if title:
                    suggestions.add(title)
            
            # Поиск в тегах
            cursor = self.conn.execute(
                'SELECT DISTINCT tags FROM enhanced_search_index WHERE tags LIKE ?',
                (f'%{partial_query}%',)
            )
            for (tags_json,) in cursor.fetchall():
                try:
                    tags = json.loads(tags_json)
                    for tag in tags:
                        if partial_query.lower() in tag.lower():
                            suggestions.add(tag)
                except:
                    continue
            
            return list(suggestions)[:limit]
            
        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return []
    
    def close(self):
        """Закрытие соединения с базой данных."""
        if hasattr(self, 'conn'):
            self.conn.close()
            logger.info("Enhanced search engine connection closed")