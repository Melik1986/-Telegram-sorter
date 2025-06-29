"""
Оптимизированный семантический поиск для Render.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    logger.warning("Semantic search dependencies not available")

class SemanticSearchEngine:
    """Движок семантического поиска с оптимизацией для Render."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Инициализация движка семантического поиска.
        
        Args:
            model_name: Название модели для эмбеддингов
        """
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError("Required dependencies not available")
        
        self.model_name = model_name
        self.model = None
        self.index = None
        self.resource_ids = []
        self.embeddings = []
        
        # Инициализация модели
        self._initialize_model()
        
        logger.info(f"Semantic search engine initialized with model: {model_name}")
    
    def _initialize_model(self):
        """Инициализация модели эмбеддингов."""
        try:
            # Используем легковесную модель для экономии ресурсов
            self.model = SentenceTransformer(self.model_name)
            logger.info("Sentence transformer model loaded")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer model: {e}")
            raise
    
    def add_resource(self, resource_id: str, resource: Dict):
        """
        Добавить ресурс в семантический индекс.
        
        Args:
            resource_id: ID ресурса
            resource: Данные ресурса
        """
        try:
            # Подготовить текст для эмбеддинга
            text = self._prepare_text_for_embedding(resource)
            
            # Создать эмбеддинг
            embedding = self.model.encode([text])[0]
            
            # Добавить в индекс
            self.resource_ids.append(resource_id)
            self.embeddings.append(embedding)
            
            # Перестроить FAISS индекс
            self._rebuild_index()
            
            logger.debug(f"Added resource {resource_id} to semantic index")
            
        except Exception as e:
            logger.error(f"Failed to add resource {resource_id} to semantic index: {e}")
    
    def _prepare_text_for_embedding(self, resource: Dict) -> str:
        """
        Подготовить текст ресурса для создания эмбеддинга.
        
        Args:
            resource: Данные ресурса
            
        Returns:
            Подготовленный текст
        """
        text_parts = []
        
        # Основной контент
        if resource.get('content'):
            text_parts.append(resource['content'])
        
        # Описание
        if resource.get('description'):
            text_parts.append(resource['description'])
        
        # Категория и подкатегория
        if resource.get('category'):
            text_parts.append(resource['category'])
        
        if resource.get('subcategory'):
            text_parts.append(resource['subcategory'])
        
        # Языки программирования
        if resource.get('programming_languages'):
            text_parts.extend(resource['programming_languages'])
        
        # Технологический стек
        if resource.get('technology_stack'):
            text_parts.extend(resource['technology_stack'])
        
        # Темы
        if resource.get('topics'):
            text_parts.extend(resource['topics'])
        
        # Объединить все части
        combined_text = ' '.join(text_parts)
        
        # Ограничить длину для эффективности
        return combined_text[:1000]
    
    def _rebuild_index(self):
        """Перестроить FAISS индекс."""
        if not self.embeddings:
            return
        
        try:
            # Конвертировать в numpy массив
            embeddings_array = np.array(self.embeddings).astype('float32')
            
            # Создать FAISS индекс
            dimension = embeddings_array.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner Product для косинусного сходства
            
            # Нормализовать эмбеддинги для косинусного сходства
            faiss.normalize_L2(embeddings_array)
            
            # Добавить эмбеддинги в индекс
            self.index.add(embeddings_array)
            
            logger.debug(f"Rebuilt FAISS index with {len(self.embeddings)} embeddings")
            
        except Exception as e:
            logger.error(f"Failed to rebuild FAISS index: {e}")
    
    def search(self, query: str, top_k: int = 10, min_similarity: float = 0.3) -> List[Tuple[str, float]]:
        """
        Выполнить семантический поиск.
        
        Args:
            query: Поисковый запрос
            top_k: Количество топ результатов
            min_similarity: Минимальное сходство
            
        Returns:
            Список кортежей (resource_id, similarity_score)
        """
        if not self.index or not self.embeddings:
            logger.warning("Semantic search index is empty")
            return []
        
        try:
            # Создать эмбеддинг запроса
            query_embedding = self.model.encode([query]).astype('float32')
            
            # Нормализовать для косинусного сходства
            faiss.normalize_L2(query_embedding)
            
            # Выполнить поиск
            similarities, indices = self.index.search(query_embedding, min(top_k, len(self.embeddings)))
            
            # Подготовить результаты
            results = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if similarity >= min_similarity and idx < len(self.resource_ids):
                    resource_id = self.resource_ids[idx]
                    results.append((resource_id, float(similarity)))
            
            logger.debug(f"Semantic search found {len(results)} results for query: {query[:50]}")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def remove_resource(self, resource_id: str):
        """
        Удалить ресурс из семантического индекса.
        
        Args:
            resource_id: ID ресурса для удаления
        """
        try:
            if resource_id in self.resource_ids:
                idx = self.resource_ids.index(resource_id)
                
                # Удалить из списков
                self.resource_ids.pop(idx)
                self.embeddings.pop(idx)
                
                # Перестроить индекс
                self._rebuild_index()
                
                logger.debug(f"Removed resource {resource_id} from semantic index")
            
        except Exception as e:
            logger.error(f"Failed to remove resource {resource_id} from semantic index: {e}")
    
    def get_stats(self) -> Dict:
        """
        Получить статистику семантического поиска.
        
        Returns:
            Словарь со статистикой
        """
        return {
            'model_name': self.model_name,
            'indexed_resources': len(self.resource_ids),
            'embedding_dimension': len(self.embeddings[0]) if self.embeddings else 0,
            'index_available': self.index is not None
        }
    
    def clear_index(self):
        """Очистить семантический индекс."""
        self.resource_ids = []
        self.embeddings = []
        self.index = None
        logger.info("Semantic search index cleared")