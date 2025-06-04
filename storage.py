"""
In-memory storage system for classified resources.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

class ResourceStorage:
    def __init__(self):
        """Initialize in-memory storage."""
        self.resources = {}  # Dict[str, Dict] - resource_id -> resource_data
        self.categories = {}  # Dict[str, List[str]] - category -> list of resource_ids
        self.search_index = {}  # Dict[str, List[str]] - keyword -> list of resource_ids
    
    def add_resource(self, content: str, category: str, subcategory: str = None, 
                    confidence: float = 0.0, description: str = '', urls: list = None) -> str:
        """Add a new resource to storage."""
        resource_id = str(uuid.uuid4())[:8]  # Short UUID
        
        resource_data = {
            'id': resource_id,
            'content': content,
            'category': category,
            'subcategory': subcategory,
            'confidence': confidence,
            'description': description,
            'urls': urls or [],
            'timestamp': datetime.now().isoformat(),
            'access_count': 0
        }
        
        # Store resource
        self.resources[resource_id] = resource_data
        
        # Update category index
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(resource_id)
        
        # Update search index
        self._update_search_index(resource_id, content, description, category, subcategory)
        
        logger.info(f"Added resource {resource_id} to category {category}")
        return resource_id
    
    def get_resource(self, resource_id: str) -> Optional[Dict]:
        """Get a specific resource by ID."""
        resource = self.resources.get(resource_id)
        if resource:
            # Increment access count
            resource['access_count'] += 1
        return resource
    
    def get_resources_by_category(self, category: str) -> List[Dict]:
        """Get all resources in a specific category."""
        resource_ids = self.categories.get(category, [])
        return [self.resources[rid] for rid in resource_ids if rid in self.resources]
    
    def get_all_resources(self) -> List[Dict]:
        """Get all resources sorted by timestamp (newest first)."""
        all_resources = list(self.resources.values())
        return sorted(all_resources, key=lambda x: x['timestamp'], reverse=True)
    
    def search_resources(self, query: str) -> List[Dict]:
        """Search resources by query."""
        query_lower = query.lower()
        matching_ids = set()
        
        # Search in content, description, and category
        for resource_id, resource in self.resources.items():
            if (query_lower in resource['content'].lower() or
                query_lower in resource['description'].lower() or
                query_lower in resource['category'].lower() or
                (resource['subcategory'] and query_lower in resource['subcategory'].lower())):
                matching_ids.add(resource_id)
        
        # Search in search index
        for keyword, resource_ids in self.search_index.items():
            if query_lower in keyword:
                matching_ids.update(resource_ids)
        
        # Return sorted results (by relevance and timestamp)
        results = [self.resources[rid] for rid in matching_ids if rid in self.resources]
        return sorted(results, key=lambda x: (x['confidence'], x['timestamp']), reverse=True)
    
    def get_categories_summary(self) -> Dict[str, int]:
        """Get summary of all categories with resource counts."""
        return {category: len(resource_ids) for category, resource_ids in self.categories.items()}
    
    def get_statistics(self) -> Dict:
        """Get storage statistics."""
        total_resources = len(self.resources)
        categories_count = len(self.categories)
        
        # Most popular category
        popular_category = None
        max_count = 0
        for category, resource_ids in self.categories.items():
            if len(resource_ids) > max_count:
                max_count = len(resource_ids)
                popular_category = category
        
        # Average confidence
        avg_confidence = 0.0
        if total_resources > 0:
            total_confidence = sum(r['confidence'] for r in self.resources.values())
            avg_confidence = total_confidence / total_resources
        
        return {
            'total_resources': total_resources,
            'categories_count': categories_count,
            'popular_category': popular_category,
            'average_confidence': avg_confidence,
            'total_urls': sum(len(r['urls']) for r in self.resources.values())
        }
    
    def _update_search_index(self, resource_id: str, content: str, description: str, 
                           category: str, subcategory: str = None):
        """Update search index with resource keywords."""
        # Extract keywords from content and description
        text = f"{content} {description} {category}"
        if subcategory:
            text += f" {subcategory}"
        
        # Simple keyword extraction (split by common separators)
        keywords = set()
        for word in text.lower().split():
            # Clean word (remove punctuation)
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) >= 3:  # Only index words with 3+ characters
                keywords.add(clean_word)
        
        # Update index
        for keyword in keywords:
            if keyword not in self.search_index:
                self.search_index[keyword] = []
            if resource_id not in self.search_index[keyword]:
                self.search_index[keyword].append(resource_id)
    
    def export_data(self) -> str:
        """Export all data as JSON string."""
        export_data = {
            'resources': self.resources,
            'categories': self.categories,
            'timestamp': datetime.now().isoformat()
        }
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def import_data(self, json_data: str) -> bool:
        """Import data from JSON string."""
        try:
            data = json.loads(json_data)
            
            if 'resources' in data:
                self.resources = data['resources']
            
            if 'categories' in data:
                self.categories = data['categories']
            
            # Rebuild search index
            self.search_index = {}
            for resource_id, resource in self.resources.items():
                self._update_search_index(
                    resource_id,
                    resource['content'],
                    resource['description'],
                    resource['category'],
                    resource.get('subcategory')
                )
            
            logger.info("Successfully imported data")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import data: {e}")
            return False
