"""
Оптимизированная система хранения для Render.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
import uuid

logger = logging.getLogger(__name__)

class ResourceStorage:
    def __init__(self, enable_semantic_search: bool = False):
        """Инициализация хранилища для Render."""
        self.resources = {}  # Dict[str, Dict] - resource_id -> resource_data
        self.categories = {}  # Dict[str, List[str]] - category -> list of resource_ids
        self.search_index = {}  # Dict[str, Set[str]] - keyword -> set of resource_ids
        
        # Семантический поиск отключен для стабильности
        self.semantic_search_engine = None
        logger.info("Storage initialized without semantic search for stability")
    
    def add_resource(self, content: str, category: str, user_id: int, 
                    username: str = None, confidence: float = 0.0, 
                    description: str = "", urls: list = None, **kwargs) -> str:
        """Добавить ресурс в хранилище."""
        resource_id = self._generate_id()
        
        resource = {
            'id': resource_id,
            'content': content,
            'category': category,
            'user_id': user_id,
            'username': username,
            'confidence': confidence,
            'description': description,
            'urls': urls or [],
            'timestamp': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        # Добавить дополнительные поля
        resource.update(kwargs)
        
        self.resources[resource_id] = resource
        
        # Обновить индекс категорий
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(resource_id)
        
        # Обновить поисковый индекс
        self._update_search_index(resource_id, content, description, category, 
                                 kwargs.get('subcategory'))
        
        return resource_id
    
    def _generate_id(self) -> str:
        """Генерация короткого уникального ID."""
        return str(uuid.uuid4())[:8]
    
    def get_resource(self, resource_id: str) -> Optional[Dict]:
        """Получить ресурс по ID."""
        resource = self.resources.get(resource_id)
        if resource:
            # Увеличить счетчик доступа
            if 'access_count' not in resource:
                resource['access_count'] = 0
            resource['access_count'] += 1
        return resource
    
    def get_resources_by_category(self, category: str) -> List[Dict]:
        """Получить все ресурсы в категории."""
        resource_ids = self.categories.get(category, [])
        return [self.resources[rid] for rid in resource_ids if rid in self.resources]
    
    def get_all_resources(self) -> List[Dict]:
        """Получить все ресурсы, отсортированные по времени."""
        all_resources = list(self.resources.values())
        return sorted(all_resources, key=lambda x: x['timestamp'], reverse=True)
    
    def search_resources(self, query: str, use_semantic: bool = False, 
                        semantic_weight: float = 0.7, category_filter: str = None, 
                        date_from: str = None, date_to: str = None) -> List[Dict]:
        """Поиск ресурсов (только текстовый поиск)."""
        # Только текстовый поиск
        text_results = self._text_search(query)
        
        # Преобразование результатов
        results = []
        for resource_id, score in text_results:
            if resource_id in self.resources:
                resource = self.resources[resource_id].copy()
                resource['search_score'] = score
                results.append(resource)
        
        # Применение фильтров
        if category_filter or date_from or date_to:
            results = self._apply_filters(results, category_filter, date_from, date_to)
        
        return results
    
    def _text_search(self, query: str) -> List[Tuple[str, float]]:
        """Текстовый поиск."""
        query_lower = query.lower()
        matching_ids = set()
        
        # Поиск в содержимом, описании и категории
        for resource_id, resource in self.resources.items():
            if (query_lower in resource['content'].lower() or
                query_lower in resource['description'].lower() or
                query_lower in resource['category'].lower() or
                (resource.get('subcategory') and query_lower in resource['subcategory'].lower())):
                matching_ids.add(resource_id)
        
        # Поиск в индексе
        for keyword, resource_ids in self.search_index.items():
            if query_lower in keyword:
                matching_ids.update(resource_ids)
        
        # Вычисление оценок
        results = []
        for resource_id in matching_ids:
            if resource_id in self.resources:
                resource = self.resources[resource_id]
                confidence_score = resource.get('confidence', 0.5)
                recency_score = 0.1
                total_score = confidence_score + recency_score
                results.append((resource_id, total_score))
        
        return results
    
    def get_categories(self) -> Dict[str, int]:
        """Получить все категории с количеством ресурсов."""
        return {category: len(resource_ids) for category, resource_ids in self.categories.items()}
    
    def get_statistics(self) -> Dict:
        """Получить статистику хранилища."""
        total_resources = len(self.resources)
        categories_count = len(self.categories)
        
        # Самая популярная категория
        popular_category = None
        max_count = 0
        for category, resource_ids in self.categories.items():
            if len(resource_ids) > max_count:
                max_count = len(resource_ids)
                popular_category = category
        
        # Средняя уверенность
        avg_confidence = 0.0
        if total_resources > 0:
            total_confidence = sum(r.get('confidence', 0) for r in self.resources.values())
            avg_confidence = total_confidence / total_resources
        
        stats = {
            'total_resources': total_resources,
            'categories_count': categories_count,
            'popular_category': popular_category,
            'average_confidence': avg_confidence,
            'total_urls': sum(len(r.get('urls', [])) for r in self.resources.values()),
            'semantic_search_enabled': False
        }
        
        return stats
    
    def _update_search_index(self, resource_id: str, content: str, description: str, 
                           category: str, subcategory: str = None):
        """Обновить поисковый индекс."""
        text = f"{content} {description} {category}"
        if subcategory:
            text += f" {subcategory}"
        
        # Извлечение ключевых слов
        keywords = set()
        for word in text.lower().split():
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) >= 3:
                keywords.add(clean_word)
        
        # Обновление индекса
        for keyword in keywords:
            if keyword not in self.search_index:
                self.search_index[keyword] = set()
            self.search_index[keyword].add(resource_id)
    
    def delete_resource(self, resource_id: str) -> bool:
        """Удалить ресурс по ID."""
        if resource_id not in self.resources:
            return False
        
        resource = self.resources[resource_id]
        category = resource['category']
        
        # Удалить из ресурсов
        del self.resources[resource_id]
        
        # Удалить из индекса категорий
        if category in self.categories:
            if resource_id in self.categories[category]:
                self.categories[category].remove(resource_id)
            if not self.categories[category]:
                del self.categories[category]
        
        # Удалить из поискового индекса
        for keyword, resource_ids in self.search_index.items():
            resource_ids.discard(resource_id)
        
        # Очистить пустые записи в поисковом индексе
        self.search_index = {k: v for k, v in self.search_index.items() if v}
        
        logger.info(f"Deleted resource {resource_id}")
        return True
    
    def export_data(self) -> str:
        """Экспорт всех данных в JSON."""
        export_data = {
            'resources': self.resources,
            'categories': self.categories,
            'timestamp': datetime.now().isoformat(),
            'version': 'render-optimized'
        }
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def import_data(self, json_data: str) -> bool:
        """Импорт данных из JSON."""
        try:
            data = json.loads(json_data)
            
            if 'resources' in data:
                self.resources = data['resources']
            
            if 'categories' in data:
                self.categories = data['categories']
            
            # Перестроить поисковый индекс
            self.search_index = {}
            for resource_id, resource in self.resources.items():
                self._update_search_index(
                    resource_id, 
                    resource['content'], 
                    resource.get('description', ''),
                    resource['category'],
                    resource.get('subcategory')
                )
            
            logger.info("Successfully imported data")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import data: {e}")
            return False
    
    def _apply_filters(self, results: List[Dict], category_filter: str = None, 
                      date_from: str = None, date_to: str = None) -> List[Dict]:
        """Применить фильтры к результатам поиска."""
        filtered_results = []
        
        for resource in results:
            # Фильтр по категории
            if category_filter and resource.get('category') != category_filter:
                continue
            
            # Фильтры по дате
            if date_from or date_to:
                resource_date = resource.get('timestamp', '')
                if isinstance(resource_date, str) and len(resource_date) >= 10:
                    resource_date = resource_date[:10]  # Извлечь YYYY-MM-DD
                else:
                    continue
                
                if date_from and resource_date < date_from:
                    continue
                if date_to and resource_date > date_to:
                    continue
            
            filtered_results.append(resource)
        
        return filtered_results