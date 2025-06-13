"""
In-memory storage system for classified resources.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
import uuid

try:
    from .semantic_search import SemanticSearchEngine
    SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    SEMANTIC_SEARCH_AVAILABLE = False
    logger.warning("Semantic search dependencies not available. Install sentence-transformers and faiss-cpu for enhanced search.")

logger = logging.getLogger(__name__)

class ResourceStorage:
    def __init__(self, enable_semantic_search: bool = True):
        """Initialize in-memory storage.
        
        Args:
            enable_semantic_search: Whether to enable semantic search capabilities
        """
        self.resources = {}  # Dict[str, Dict] - resource_id -> resource_data
        self.categories = {}  # Dict[str, List[str]] - category -> list of resource_ids
        self.search_index = {}  # Dict[str, List[str]] - keyword -> list of resource_ids
        
        # Initialize semantic search if available
        self.semantic_search = None
        if enable_semantic_search and SEMANTIC_SEARCH_AVAILABLE:
            try:
                self.semantic_search = SemanticSearchEngine()
                logger.info("Semantic search engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize semantic search: {e}")
                self.semantic_search = None
    
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
        
        # Add to semantic search if available
        if self.semantic_search:
            try:
                self.semantic_search.add_resource(resource_id, resource)
            except Exception as e:
                logger.error(f"Failed to add resource to semantic search: {e}")
        
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
    
    def search_resources(self, query: str, use_semantic: bool = True, semantic_weight: float = 0.7, 
                        category_filter: str = None, date_from: str = None, date_to: str = None) -> List[Dict]:
        """Search resources by query using both text and semantic search.
        
        Args:
            query: Search query
            use_semantic: Whether to use semantic search
            semantic_weight: Weight for semantic search results (0.0-1.0)
            category_filter: Filter by specific category
            date_from: Filter resources from this date (YYYY-MM-DD)
            date_to: Filter resources to this date (YYYY-MM-DD)
            
        Returns:
            List of resources sorted by relevance
        """
        # Get text search results
        text_results = self._text_search(query)
        
        # Get semantic search results if available
        semantic_results = []
        if use_semantic and self.semantic_search:
            semantic_results = self._semantic_search(query)
        
        # Combine and rank results
        results = self._combine_search_results(text_results, semantic_results, semantic_weight)
        
        # Apply filters
        if category_filter or date_from or date_to:
            results = self._apply_filters(results, category_filter, date_from, date_to)
        
        return results
    
    def _text_search(self, query: str) -> List[Tuple[str, float]]:
        """Perform text-based search.
        
        Args:
            query: Search query
            
        Returns:
            List of (resource_id, score) tuples
        """
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
        
        # Calculate text search scores (simple relevance based on confidence and recency)
        results = []
        for resource_id in matching_ids:
            if resource_id in self.resources:
                resource = self.resources[resource_id]
                # Simple scoring: confidence + recency factor
                confidence_score = resource.get('confidence', 0.5)
                recency_score = 0.1  # Base recency score
                total_score = confidence_score + recency_score
                results.append((resource_id, total_score))
        
        return results
    
    def _semantic_search(self, query: str) -> List[Tuple[str, float]]:
        """Perform semantic search.
        
        Args:
            query: Search query
            
        Returns:
            List of (resource_id, similarity_score) tuples
        """
        try:
            return self.semantic_search.search(query, top_k=20, min_similarity=0.3)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _combine_search_results(self, text_results: List[Tuple[str, float]], 
                               semantic_results: List[Tuple[str, float]], 
                               semantic_weight: float) -> List[Dict]:
        """Combine text and semantic search results.
        
        Args:
            text_results: Text search results
            semantic_results: Semantic search results
            semantic_weight: Weight for semantic results
            
        Returns:
            Combined and sorted list of resources
        """
        # Create score dictionary
        combined_scores = {}
        
        # Add text search scores
        text_weight = 1.0 - semantic_weight
        for resource_id, score in text_results:
            combined_scores[resource_id] = text_weight * score
        
        # Add semantic search scores
        for resource_id, score in semantic_results:
            if resource_id in combined_scores:
                combined_scores[resource_id] += semantic_weight * score
            else:
                combined_scores[resource_id] = semantic_weight * score
        
        # Sort by combined score
        sorted_ids = sorted(combined_scores.keys(), 
                           key=lambda x: combined_scores[x], 
                           reverse=True)
        
        # Return resource objects
        results = []
        for resource_id in sorted_ids:
            if resource_id in self.resources:
                resource = self.resources[resource_id].copy()
                resource['search_score'] = combined_scores[resource_id]
                results.append(resource)
        
        return results
    
    def semantic_search_resources(self, query: str, top_k: int = 10) -> List[Dict]:
        """Perform pure semantic search.
        
        Args:
            query: Search query
            top_k: Number of top results
            
        Returns:
            List of resources sorted by semantic similarity
        """
        if not self.semantic_search:
            logger.warning("Semantic search not available")
            return []
        
        try:
            semantic_results = self.semantic_search.search(query, top_k=top_k)
            results = []
            
            for resource_id, similarity in semantic_results:
                if resource_id in self.resources:
                    resource = self.resources[resource_id].copy()
                    resource['similarity_score'] = similarity
                    results.append(resource)
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    async def semantic_search_resources_filtered(self, query: str, limit: int = 10,
                                               category_filter: str = None, 
                                               date_from: str = None, 
                                               date_to: str = None) -> List[Dict]:
        """Perform semantic search with filters.
        
        Args:
            query: Search query
            limit: Maximum number of results
            category_filter: Filter by specific category
            date_from: Filter resources from this date (YYYY-MM-DD)
            date_to: Filter resources to this date (YYYY-MM-DD)
            
        Returns:
            List of filtered resources with similarity scores
        """
        # Get semantic search results
        results = self.semantic_search_resources(query, top_k=limit * 2)  # Get more to account for filtering
        
        # Apply filters
        if category_filter or date_from or date_to:
            results = self._apply_filters(results, category_filter, date_from, date_to)
        
        # Limit results and format for async return
        limited_results = results[:limit]
        
        # Format results to match expected structure
        formatted_results = []
        for resource in limited_results:
            formatted_result = {
                'resource': resource,
                'score': resource.get('similarity_score', 0.0)
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
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
        
        # Semantic search statistics
        semantic_stats = {}
        if self.semantic_search:
            try:
                semantic_stats = self.semantic_search.get_stats()
            except Exception as e:
                logger.error(f"Failed to get semantic search stats: {e}")
        
        stats = {
            'total_resources': total_resources,
            'categories_count': categories_count,
            'popular_category': popular_category,
            'average_confidence': avg_confidence,
            'total_urls': sum(len(r.get('urls', [])) for r in self.resources.values()),
            'file_resources': file_resources,
            'semantic_search_enabled': self.semantic_search is not None
        }
        
        # Add semantic search stats if available
        if semantic_stats:
            stats['semantic_search'] = semantic_stats
        
        return stats
    
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
        
        # Remove from semantic search if available
        if self.semantic_search:
            try:
                self.semantic_search.remove_resource(resource_id)
            except Exception as e:
                logger.error(f"Failed to remove resource from semantic search: {e}")
        
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
    
    def _apply_filters(self, results: List[Dict], category_filter: str = None, 
                      date_from: str = None, date_to: str = None) -> List[Dict]:
        """Apply filters to search results.
        
        Args:
            results: List of resources to filter
            category_filter: Filter by specific category
            date_from: Filter resources from this date (YYYY-MM-DD)
            date_to: Filter resources to this date (YYYY-MM-DD)
            
        Returns:
            Filtered list of resources
        """
        filtered_results = []
        
        for resource in results:
            # Category filter
            if category_filter and resource.get('category') != category_filter:
                continue
            
            # Date filters
            if date_from or date_to:
                resource_date = resource.get('timestamp', '')
                if isinstance(resource_date, (int, float)):
                    # Convert timestamp to date string
                    from datetime import datetime
                    resource_date = datetime.fromtimestamp(resource_date).strftime('%Y-%m-%d')
                elif isinstance(resource_date, str) and len(resource_date) >= 10:
                    resource_date = resource_date[:10]  # Extract YYYY-MM-DD part
                else:
                    continue  # Skip if no valid date
                
                if date_from and resource_date < date_from:
                    continue
                if date_to and resource_date > date_to:
                    continue
            
            filtered_results.append(resource)
        
        return filtered_results