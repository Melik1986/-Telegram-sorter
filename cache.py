#!/usr/bin/env python3
"""
Caching system for DevDataSorter.
Provides in-memory and file-based caching for classification results and API responses.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import hashlib

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages caching for classification results and API responses."""
    
    def __init__(self, cache_dir: str = "cache", max_memory_items: int = 1000, 
                 default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for file-based cache
            max_memory_items: Maximum items in memory cache
            default_ttl: Default time-to-live in seconds
        """
        self.cache_dir = cache_dir
        self.max_memory_items = max_memory_items
        self.default_ttl = default_ttl
        
        # In-memory cache
        self.memory_cache = {}
        self.cache_timestamps = {}
        self.access_times = {}
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        logger.info(f"Cache manager initialized with dir: {cache_dir}")
    
    def _generate_key(self, data: str) -> str:
        """Generate cache key from data."""
        return hashlib.md5(data.encode('utf-8')).hexdigest()
    
    def _is_expired(self, timestamp: float, ttl: int) -> bool:
        """Check if cache entry is expired."""
        return time.time() - timestamp > ttl
    
    def _cleanup_memory_cache(self):
        """Remove expired and least recently used items from memory cache."""
        current_time = time.time()
        
        # Remove expired items
        expired_keys = []
        for key, timestamp in self.cache_timestamps.items():
            if self._is_expired(timestamp, self.default_ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_from_memory(key)
        
        # Remove LRU items if cache is full
        while len(self.memory_cache) >= self.max_memory_items:
            # Find least recently used item
            lru_key = min(self.access_times.keys(), 
                         key=lambda k: self.access_times[k])
            self._remove_from_memory(lru_key)
    
    def _remove_from_memory(self, key: str):
        """Remove item from memory cache."""
        self.memory_cache.pop(key, None)
        self.cache_timestamps.pop(key, None)
        self.access_times.pop(key, None)
    
    def _get_file_path(self, key: str) -> str:
        """Get file path for cache key."""
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """Get item from cache."""
        if ttl is None:
            ttl = self.default_ttl
        
        cache_key = self._generate_key(key)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            if not self._is_expired(self.cache_timestamps[cache_key], ttl):
                self.access_times[cache_key] = time.time()
                logger.debug(f"Cache hit (memory): {cache_key[:8]}")
                return self.memory_cache[cache_key]
            else:
                self._remove_from_memory(cache_key)
        
        # Check file cache
        file_path = self._get_file_path(cache_key)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                if not self._is_expired(cache_data['timestamp'], ttl):
                    # Load into memory cache
                    self._cleanup_memory_cache()
                    self.memory_cache[cache_key] = cache_data['data']
                    self.cache_timestamps[cache_key] = cache_data['timestamp']
                    self.access_times[cache_key] = time.time()
                    
                    logger.debug(f"Cache hit (file): {cache_key[:8]}")
                    return cache_data['data']
                else:
                    # Remove expired file
                    os.remove(file_path)
            except (json.JSONDecodeError, KeyError, OSError) as e:
                logger.warning(f"Error reading cache file {file_path}: {e}")
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        
        logger.debug(f"Cache miss: {cache_key[:8]}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set item in cache."""
        if ttl is None:
            ttl = self.default_ttl
        
        cache_key = self._generate_key(key)
        current_time = time.time()
        
        try:
            # Store in memory cache
            self._cleanup_memory_cache()
            self.memory_cache[cache_key] = value
            self.cache_timestamps[cache_key] = current_time
            self.access_times[cache_key] = current_time
            
            # Store in file cache
            cache_data = {
                'data': value,
                'timestamp': current_time,
                'ttl': ttl
            }
            
            file_path = self._get_file_path(cache_key)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Cache set: {cache_key[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache for key {cache_key[:8]}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        cache_key = self._generate_key(key)
        
        # Remove from memory
        self._remove_from_memory(cache_key)
        
        # Remove file
        file_path = self._get_file_path(cache_key)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.debug(f"Cache deleted: {cache_key[:8]}")
            return True
        except OSError as e:
            logger.error(f"Error deleting cache file {file_path}: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache."""
        try:
            # Clear memory cache
            self.memory_cache.clear()
            self.cache_timestamps.clear()
            self.access_times.clear()
            
            # Clear file cache
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    os.remove(file_path)
            
            logger.info("Cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        file_count = 0
        total_file_size = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_count += 1
                    file_path = os.path.join(self.cache_dir, filename)
                    total_file_size += os.path.getsize(file_path)
        except OSError:
            pass
        
        return {
            'memory_items': len(self.memory_cache),
            'file_items': file_count,
            'total_file_size_bytes': total_file_size,
            'max_memory_items': self.max_memory_items,
            'default_ttl': self.default_ttl,
            'cache_dir': self.cache_dir
        }

# Global cache instance
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager