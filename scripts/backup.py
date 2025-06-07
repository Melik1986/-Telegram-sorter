#!/usr/bin/env python3
"""
Automatic backup system for DevDataSorter.
Provides scheduled backups of storage data and configuration.
"""

import json
import logging
import os
import shutil
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import zipfile

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automatic backups of application data."""
    
    def __init__(self, backup_dir: str = "backups", max_backups: int = 10, 
                 backup_interval: int = 3600):
        """
        Initialize backup manager.
        
        Args:
            backup_dir: Directory for storing backups
            max_backups: Maximum number of backups to keep
            backup_interval: Backup interval in seconds (default: 1 hour)
        """
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.backup_interval = backup_interval
        self.is_running = False
        self.backup_thread = None
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        logger.info(f"Backup manager initialized with dir: {backup_dir}")
    
    def create_backup(self, storage_data: Dict, additional_files: List[str] = None) -> str:
        """
        Create a backup of current data.
        
        Args:
            storage_data: Storage data to backup
            additional_files: Additional files to include in backup
            
        Returns:
            Path to created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Backup storage data
                storage_json = json.dumps(storage_data, ensure_ascii=False, indent=2)
                zipf.writestr("storage_data.json", storage_json)
                
                # Backup configuration
                config_data = {
                    "backup_timestamp": timestamp,
                    "backup_version": "1.0",
                    "data_format": "json"
                }
                config_json = json.dumps(config_data, ensure_ascii=False, indent=2)
                zipf.writestr("backup_config.json", config_json)
                
                # Backup additional files
                if additional_files:
                    for file_path in additional_files:
                        if os.path.exists(file_path):
                            arcname = os.path.basename(file_path)
                            zipf.write(file_path, arcname)
                        else:
                            logger.warning(f"Additional file not found: {file_path}")
                
                # Backup cache if exists
                cache_dir = "cache"
                if os.path.exists(cache_dir):
                    for root, dirs, files in os.walk(cache_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, ".")
                            zipf.write(file_path, arcname)
            
            logger.info(f"Backup created: {backup_filename}")
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            # Remove incomplete backup file
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except OSError:
                    pass
            raise
    
    def restore_backup(self, backup_path: str) -> Dict:
        """
        Restore data from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Restored storage data
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Check if it's a valid backup
                if "storage_data.json" not in zipf.namelist():
                    raise ValueError("Invalid backup file: missing storage_data.json")
                
                # Read storage data
                storage_json = zipf.read("storage_data.json").decode('utf-8')
                storage_data = json.loads(storage_json)
                
                # Read backup config if available
                if "backup_config.json" in zipf.namelist():
                    config_json = zipf.read("backup_config.json").decode('utf-8')
                    config_data = json.loads(config_json)
                    logger.info(f"Restoring backup from {config_data.get('backup_timestamp', 'unknown')}")
                
                # Extract cache files if present
                cache_files = [name for name in zipf.namelist() if name.startswith("cache/")]
                if cache_files:
                    for cache_file in cache_files:
                        zipf.extract(cache_file, ".")
                    logger.info(f"Restored {len(cache_files)} cache files")
                
                logger.info(f"Backup restored from: {backup_path}")
                return storage_data
                
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            raise
    
    def list_backups(self) -> List[Dict]:
        """List available backups with metadata."""
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("backup_") and filename.endswith(".zip"):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_stat = os.stat(file_path)
                    
                    # Extract timestamp from filename
                    timestamp_str = filename[7:-4]  # Remove "backup_" and ".zip"
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    except ValueError:
                        timestamp = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    backups.append({
                        "filename": filename,
                        "path": file_path,
                        "timestamp": timestamp,
                        "size_bytes": file_stat.st_size,
                        "size_mb": round(file_stat.st_size / (1024 * 1024), 2)
                    })
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x["timestamp"], reverse=True)
            
        except OSError as e:
            logger.error(f"Error listing backups: {e}")
        
        return backups
    
    def _cleanup_old_backups(self):
        """Remove old backups exceeding max_backups limit."""
        backups = self.list_backups()
        
        if len(backups) > self.max_backups:
            # Remove oldest backups
            backups_to_remove = backups[self.max_backups:]
            
            for backup in backups_to_remove:
                try:
                    os.remove(backup["path"])
                    logger.info(f"Removed old backup: {backup['filename']}")
                except OSError as e:
                    logger.error(f"Error removing backup {backup['filename']}: {e}")
    
    def start_automatic_backup(self, get_storage_data_func):
        """
        Start automatic backup thread.
        
        Args:
            get_storage_data_func: Function that returns current storage data
        """
        if self.is_running:
            logger.warning("Automatic backup is already running")
            return
        
        self.is_running = True
        self.backup_thread = threading.Thread(
            target=self._backup_loop,
            args=(get_storage_data_func,),
            daemon=True
        )
        self.backup_thread.start()
        
        logger.info(f"Automatic backup started (interval: {self.backup_interval}s)")
    
    def stop_automatic_backup(self):
        """Stop automatic backup thread."""
        self.is_running = False
        if self.backup_thread and self.backup_thread.is_alive():
            self.backup_thread.join(timeout=5)
        
        logger.info("Automatic backup stopped")
    
    def _backup_loop(self, get_storage_data_func):
        """Main backup loop running in separate thread."""
        while self.is_running:
            try:
                # Wait for backup interval
                for _ in range(self.backup_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                
                if not self.is_running:
                    break
                
                # Create backup
                storage_data = get_storage_data_func()
                if storage_data:
                    self.create_backup(storage_data)
                
            except Exception as e:
                logger.error(f"Error in backup loop: {e}")
                # Continue running even if backup fails
                time.sleep(60)  # Wait 1 minute before retrying
    
    def get_stats(self) -> Dict:
        """Get backup statistics."""
        backups = self.list_backups()
        
        total_size = sum(backup["size_bytes"] for backup in backups)
        
        return {
            "backup_count": len(backups),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "newest_backup": backups[0]["timestamp"].isoformat() if backups else None,
            "oldest_backup": backups[-1]["timestamp"].isoformat() if backups else None,
            "backup_interval": self.backup_interval,
            "max_backups": self.max_backups,
            "is_running": self.is_running
        }

# Global backup instance
_backup_manager = None

def get_backup_manager() -> BackupManager:
    """Get global backup manager instance."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager