"""
Минимальная система хранения в памяти для Railway.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ResourceStorage:
    def __init__(self):
        """Инициализация хранилища в памяти."""
        self.resources = {}  # resource_id -> resource_data
        self.categories = {}  # category -> list of resource_ids
        self.search_index = {}  # keyword -> set of resource_ids
    
    def add_resource(self, content: str, category: str, user_id: int, 
                    username: str = None, confidence: float = 0.0, 
                    description: str = "", **kwargs) -> str:
        """Добавить ресурс."""
        resource_id = str(uuid.uuid4())[:8]
        
        resource = {
            'id': resource_id,
            'content': content,
            'category': category,
            'user_id': user_id,
            'username': username,
            'confidence': confidence,
            'description': description,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        self.resources[resource_id] = resource
        
        # Обновление индексов
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(resource_id)
        
        # Простая индексация по словам
        words = content.lower().split()
        for word in words:
            if len(word) > 2:
                if word not in self.search_index:
                    self.search_index[word] = set()
                self.search_index[word].add(resource_id)
        
        return resource_id
    
    def search_resources(self, query: str, **kwargs) -> List[Dict]:
        """Поиск ресурсов."""
        query_words = query.lower().split()
        matching_ids = set()
        
        for word in query_words:
            if word in self.search_index:
                matching_ids.update(self.search_index[word])
        
        # Поиск в содержимом
        for resource_id, resource in self.resources.items():
            if query.lower() in resource['content'].lower():
                matching_ids.add(resource_id)
        
        results = []
        for resource_id in matching_ids:
            if resource_id in self.resources:
                results.append(self.resources[resource_id])
        
        return sorted(results, key=lambda x: x['timestamp'], reverse=True)
    
    def get_all_resources(self) -> List[Dict]:
        """Получить все ресурсы."""
        return sorted(self.resources.values(), 
                     key=lambda x: x['timestamp'], reverse=True)
    
    def get_categories(self) -> Dict[str, int]:
        """Получить категории с количеством."""
        return {cat: len(ids) for cat, ids in self.categories.items()}
    
    def get_statistics(self) -> Dict:
        """Получить статистику."""
        return {
            'total_resources': len(self.resources),
            'categories_count': len(self.categories),
            'popular_category': max(self.categories.keys(), 
                                  key=lambda k: len(self.categories[k])) 
                                  if self.categories else None
        }