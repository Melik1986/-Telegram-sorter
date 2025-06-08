"""
In-memory storage system for classified resources.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)

class ResourceStorage:
    def __init__(self):
        """Initialize in-memory storage."""
        self.resources = {}  # Dict[str, Dict] - resource_id -> resource_data
        self.categories = {}  # Dict[str, List[str]] - category -> list of resource_ids
        self.search_index = {}  # Dict[str, List[str]] - keyword -> list of resource_ids
    
    def add_resource(self, content: str, category: str, user_id: int, username: str = None, confidence: float = 0.0, description: str = "", urls: list = None, **kwargs) -> str:
        """Add a new resource to storage."""
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
        
        # Add any additional fields (for file support)
        resource.update(kwargs)
        
        self.resources[resource_id] = resource
        
        # Update category index
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(resource_id)
        
        # Update search index
        search_text = f"{content} {category} {description}".lower()
        # Include file-related fields in search if present
        if 'file_type' in kwargs:
            search_text += f" {kwargs['file_type']}"
        if 'mime_type' in kwargs:
            search_text += f" {kwargs['mime_type']}"
        
        for word in search_text.split():
            if word not in self.search_index:
                self.search_index[word] = set()
            self.search_index[word].add(resource_id)
        
        return resource_id
    
    def _generate_id(self) -> str:
        """Generate a short unique ID."""
        return str(uuid.uuid4())[:8]
    
    def get_resource(self, resource_id: str) -> Optional[Dict]:
        """Get a specific resource by ID."""
        resource = self.resources.get(resource_id)
        if resource:
            # Increment access count if it exists
            if 'access_count' not in resource:
                resource['access_count'] = 0
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
                (resource.get('subcategory') and query_lower in resource['subcategory'].lower()) or
                (resource.get('file_type') and query_lower in resource['file_type'].lower()) or
                (resource.get('mime_type') and query_lower in resource['mime_type'].lower())):
                matching_ids.add(resource_id)
        
        # Search in search index
        for keyword, resource_ids in self.search_index.items():
            if query_lower in keyword:
                matching_ids.update(resource_ids)
        
        # Return sorted results (by relevance and timestamp)
        results = [self.resources[rid] for rid in matching_ids if rid in self.resources]
        return sorted(results, key=lambda x: (x.get('confidence', 0), x['timestamp']), reverse=True)
    
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
            total_confidence = sum(r.get('confidence', 0) for r in self.resources.values())
            avg_confidence = total_confidence / total_resources
        
        # File statistics
        file_resources = sum(1 for r in self.resources.values() if r.get('file_type'))
        
        return {
            'total_resources': total_resources,
            'categories_count': categories_count,
            'popular_category': popular_category,
            'average_confidence': avg_confidence,
            'total_urls': sum(len(r.get('urls', [])) for r in self.resources.values()),
            'file_resources': file_resources
        }
    
    def get_categories(self) -> Dict[str, int]:
        """Get all categories with resource counts."""
        return {category: len(resource_ids) for category, resource_ids in self.categories.items()}
    
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
                self.search_index[keyword] = set()
            self.search_index[keyword].add(resource_id)
    
    def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource by ID."""
        if resource_id not in self.resources:
            return False
        
        resource = self.resources[resource_id]
        category = resource['category']
        
        # Remove from resources
        del self.resources[resource_id]
        
        # Remove from category index
        if category in self.categories:
            if resource_id in self.categories[category]:
                self.categories[category].remove(resource_id)
            if not self.categories[category]:  # Remove empty category
                del self.categories[category]
        
        # Remove from search index
        for keyword, resource_ids in self.search_index.items():
            resource_ids.discard(resource_id)
        
        # Clean up empty search index entries
        self.search_index = {k: v for k, v in self.search_index.items() if v}
        
        logger.info(f"Deleted resource {resource_id}")
        return True
    
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
                search_text = f"{resource['content']} {resource['category']} {resource.get('description', '')}".lower()
                if resource.get('file_type'):
                    search_text += f" {resource['file_type']}"
                if resource.get('mime_type'):
                    search_text += f" {resource['mime_type']}"
                
                for word in search_text.split():
                    if word not in self.search_index:
                        self.search_index[word] = set()
                    self.search_index[word].add(resource_id)
            
            logger.info("Successfully imported data")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import data: {e}")
            return False
    
    def create_folder(self, name: str, description: str = "") -> str:
        """Create a new folder."""
        folder_id = f"folder_{len(self.folders) + 1}_{int(time.time())}"
        
        folder = {
            'id': folder_id,
            'name': name,
            'description': description,
            'type': 'folder',
            'created_at': datetime.now().isoformat(),
            'resources': []
        }
        
        if not hasattr(self, 'folders'):
            self.folders = {}
        
        self.folders[folder_id] = folder
        logger.info(f"Created folder: {name} (ID: {folder_id})")
        return folder_id
    
    def create_archive(self, name: str, description: str = "", resource_ids: list = None) -> str:
        """Create a new archive with selected resources."""
        archive_id = f"archive_{len(getattr(self, 'archives', {})) + 1}_{int(time.time())}"
        
        if resource_ids is None:
            resource_ids = []
        
        # Validate resource IDs
        valid_resource_ids = [rid for rid in resource_ids if rid in self.resources]
        
        archive = {
            'id': archive_id,
            'name': name,
            'description': description,
            'type': 'archive',
            'created_at': datetime.now().isoformat(),
            'resources': valid_resource_ids,
            'resource_count': len(valid_resource_ids)
        }
        
        if not hasattr(self, 'archives'):
            self.archives = {}
        
        self.archives[archive_id] = archive
        logger.info(f"Created archive: {name} (ID: {archive_id}) with {len(valid_resource_ids)} resources")
        return archive_id
    
    def get_all_folders(self) -> list:
        """Get all folders."""
        if not hasattr(self, 'folders'):
            self.folders = {}
        return list(self.folders.values())
    
    def get_all_archives(self) -> list:
        """Get all archives."""
        if not hasattr(self, 'archives'):
            self.archives = {}
        return list(self.archives.values())
    
    def get_folder(self, folder_id: str) -> dict:
        """Get folder by ID."""
        if not hasattr(self, 'folders'):
            self.folders = {}
        return self.folders.get(folder_id)
    
    def get_archive(self, archive_id: str) -> dict:
        """Get archive by ID."""
        if not hasattr(self, 'archives'):
            self.archives = {}
        return self.archives.get(archive_id)
    
    def search_folders(self, query: str) -> list:
        """Search folders by name or description."""
        if not hasattr(self, 'folders'):
            self.folders = {}
        
        query_lower = query.lower()
        results = []
        
        for folder in self.folders.values():
            if (query_lower in folder['name'].lower() or 
                query_lower in folder.get('description', '').lower()):
                results.append(folder)
        
        return results
    
    def search_archives(self, query: str) -> list:
        """Search archives by name or description."""
        if not hasattr(self, 'archives'):
            self.archives = {}
        
        query_lower = query.lower()
        results = []
        
        for archive in self.archives.values():
            if (query_lower in archive['name'].lower() or 
                query_lower in archive.get('description', '').lower()):
                results.append(archive)
        
        return results
    
    def add_resource_to_folder(self, folder_id: str, resource_id: str) -> bool:
        """Add resource to folder."""
        if not hasattr(self, 'folders'):
            self.folders = {}
        
        if folder_id not in self.folders or resource_id not in self.resources:
            return False
        
        if resource_id not in self.folders[folder_id]['resources']:
            self.folders[folder_id]['resources'].append(resource_id)
        
        return True
    
    def remove_resource_from_folder(self, folder_id: str, resource_id: str) -> bool:
        """Remove resource from folder."""
        if not hasattr(self, 'folders'):
            self.folders = {}
        
        if folder_id not in self.folders:
            return False
        
        if resource_id in self.folders[folder_id]['resources']:
            self.folders[folder_id]['resources'].remove(resource_id)
        
        return True