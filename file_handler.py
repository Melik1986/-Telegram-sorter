#!/usr/bin/env python3
"""
File handling system for DevDataSorter.
Supports processing of images, documents, and other file types.
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from telegram import Document, PhotoSize, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class FileHandler:
    """Handles file processing and analysis."""
    
    def __init__(self, upload_dir: str = "uploads", max_file_size: int = 50 * 1024 * 1024):
        """
        Initialize file handler.
        
        Args:
            upload_dir: Directory for storing uploaded files
            max_file_size: Maximum file size in bytes (default: 50MB)
        """
        self.upload_dir = upload_dir
        self.max_file_size = max_file_size
        
        # Supported file types
        self.supported_image_types = {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'
        }
        
        self.supported_document_types = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain',
            'text/csv',
            'application/json',
            'application/xml',
            'text/xml'
        }
        
        self.supported_code_types = {
            'text/x-python', 'text/x-java', 'text/x-c', 'text/x-c++',
            'text/javascript', 'text/html', 'text/css', 'text/x-sql'
        }
        
        # Create upload directory
        os.makedirs(upload_dir, exist_ok=True)
        
        logger.info(f"File handler initialized with upload dir: {upload_dir}")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
        """
        Handle photo uploads.
        
        Args:
            update: Telegram update object
            context: Telegram context
            
        Returns:
            File processing result
        """
        try:
            # Get the largest photo size
            photo = update.message.photo[-1]
            
            # Check file size
            if photo.file_size > self.max_file_size:
                return {
                    'success': False,
                    'error': f'Файл слишком большой: {photo.file_size / 1024 / 1024:.1f}MB (макс: {self.max_file_size / 1024 / 1024:.1f}MB)'
                }
            
            # Download file
            file = await context.bot.get_file(photo.file_id)
            file_path = await self._download_file(file, 'photo', 'jpg')
            
            # Analyze image
            analysis = await self._analyze_image(file_path, update.message.caption)
            
            return {
                'success': True,
                'file_type': 'image',
                'file_path': file_path,
                'file_size': photo.file_size,
                'analysis': analysis,
                'mime_type': 'image/jpeg'
            }
            
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            return {
                'success': False,
                'error': f'Ошибка обработки изображения: {str(e)}'
            }
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
        """
        Handle document uploads.
        
        Args:
            update: Telegram update object
            context: Telegram context
            
        Returns:
            File processing result
        """
        try:
            document = update.message.document
            
            # Check file size
            if document.file_size > self.max_file_size:
                return {
                    'success': False,
                    'error': f'Файл слишком большой: {document.file_size / 1024 / 1024:.1f}MB (макс: {self.max_file_size / 1024 / 1024:.1f}MB)'
                }
            
            # Check if file type is supported
            mime_type = document.mime_type or mimetypes.guess_type(document.file_name)[0]
            if not self._is_supported_file_type(mime_type):
                return {
                    'success': False,
                    'error': f'Неподдерживаемый тип файла: {mime_type}'
                }
            
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_extension = os.path.splitext(document.file_name)[1] or '.bin'
            file_path = await self._download_file(file, 'document', file_extension[1:])
            
            # Analyze document
            analysis = await self._analyze_document(file_path, document.file_name, mime_type)
            
            return {
                'success': True,
                'file_type': 'document',
                'file_path': file_path,
                'file_size': document.file_size,
                'file_name': document.file_name,
                'mime_type': mime_type,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            return {
                'success': False,
                'error': f'Ошибка обработки документа: {str(e)}'
            }
    
    async def _download_file(self, file, file_type: str, extension: str) -> str:
        """Download file from Telegram servers."""
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(file.file_id.encode()).hexdigest()[:8]
        filename = f"{file_type}_{timestamp}_{file_hash}.{extension}"
        file_path = os.path.join(self.upload_dir, filename)
        
        # Download file
        await file.download_to_drive(file_path)
        
        logger.info(f"File downloaded: {filename}")
        return file_path
    
    def _is_supported_file_type(self, mime_type: str) -> bool:
        """Check if file type is supported."""
        if not mime_type:
            return False
        
        return (mime_type in self.supported_image_types or
                mime_type in self.supported_document_types or
                mime_type in self.supported_code_types)
    
    async def _analyze_image(self, file_path: str, caption: str = None) -> Dict:
        """Analyze image content."""
        try:
            # Basic image analysis
            file_size = os.path.getsize(file_path)
            
            # Try to get image dimensions (requires PIL/Pillow)
            dimensions = None
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    dimensions = img.size
            except ImportError:
                logger.warning("PIL not available for image analysis")
            except Exception as e:
                logger.warning(f"Error getting image dimensions: {e}")
            
            # Classify based on filename and caption
            category = self._classify_image_content(file_path, caption)
            
            analysis = {
                'category': category,
                'file_size': file_size,
                'dimensions': dimensions,
                'caption': caption,
                'description': self._generate_image_description(category, caption, dimensions)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {
                'category': 'other',
                'description': 'Изображение (ошибка анализа)',
                'error': str(e)
            }
    
    async def _analyze_document(self, file_path: str, filename: str, mime_type: str) -> Dict:
        """Analyze document content."""
        try:
            file_size = os.path.getsize(file_path)
            
            # Classify document type
            category = self._classify_document_content(filename, mime_type)
            
            # Try to extract text content for text files
            text_content = None
            if mime_type.startswith('text/') and file_size < 1024 * 1024:  # Max 1MB for text analysis
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text_content = f.read()[:5000]  # First 5000 chars
                except Exception as e:
                    logger.warning(f"Error reading text file: {e}")
            
            analysis = {
                'category': category,
                'file_size': file_size,
                'filename': filename,
                'mime_type': mime_type,
                'text_preview': text_content,
                'description': self._generate_document_description(category, filename, mime_type)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing document: {e}")
            return {
                'category': 'other',
                'description': 'Документ (ошибка анализа)',
                'error': str(e)
            }
    
    def _classify_image_content(self, file_path: str, caption: str = None) -> str:
        """Classify image based on filename and caption."""
        filename = os.path.basename(file_path).lower()
        caption_lower = (caption or '').lower()
        
        # UI/UX related keywords
        ui_keywords = ['mockup', 'wireframe', 'design', 'ui', 'ux', 'interface', 'prototype']
        if any(keyword in filename or keyword in caption_lower for keyword in ui_keywords):
            return 'mockups'
        
        # Screenshot keywords
        screenshot_keywords = ['screenshot', 'screen', 'capture', 'demo']
        if any(keyword in filename or keyword in caption_lower for keyword in screenshot_keywords):
            return 'code_examples'
        
        # Diagram keywords
        diagram_keywords = ['diagram', 'chart', 'graph', 'flow', 'architecture']
        if any(keyword in filename or keyword in caption_lower for keyword in diagram_keywords):
            return 'documentation'
        
        return 'other'
    
    def _classify_document_content(self, filename: str, mime_type: str) -> str:
        """Classify document based on filename and MIME type."""
        filename_lower = filename.lower()
        
        # Code files
        code_extensions = ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.sql']
        if any(filename_lower.endswith(ext) for ext in code_extensions):
            return 'code_examples'
        
        # Documentation
        doc_keywords = ['readme', 'doc', 'manual', 'guide', 'api', 'reference']
        if any(keyword in filename_lower for keyword in doc_keywords):
            return 'documentation'
        
        # Configuration files
        config_extensions = ['.json', '.xml', '.yaml', '.yml', '.ini', '.conf']
        if any(filename_lower.endswith(ext) for ext in config_extensions):
            return 'tools'
        
        # Based on MIME type
        if mime_type == 'application/pdf':
            return 'documentation'
        elif 'word' in mime_type or 'powerpoint' in mime_type:
            return 'documentation'
        elif 'excel' in mime_type or mime_type == 'text/csv':
            return 'tools'
        
        return 'other'
    
    def _generate_image_description(self, category: str, caption: str, dimensions: Tuple = None) -> str:
        """Generate description for image."""
        desc_parts = []
        
        if category == 'mockups':
            desc_parts.append("UI/UX дизайн или макет")
        elif category == 'code_examples':
            desc_parts.append("Скриншот кода или демонстрация")
        elif category == 'documentation':
            desc_parts.append("Диаграмма или схема")
        else:
            desc_parts.append("Изображение")
        
        if dimensions:
            desc_parts.append(f"({dimensions[0]}x{dimensions[1]})")
        
        if caption:
            desc_parts.append(f"- {caption}")
        
        return " ".join(desc_parts)
    
    def _generate_document_description(self, category: str, filename: str, mime_type: str) -> str:
        """Generate description for document."""
        desc_parts = []
        
        if category == 'code_examples':
            desc_parts.append("Файл с кодом")
        elif category == 'documentation':
            desc_parts.append("Документация")
        elif category == 'tools':
            desc_parts.append("Конфигурационный файл или инструмент")
        else:
            desc_parts.append("Документ")
        
        desc_parts.append(f"({filename})")
        
        return " ".join(desc_parts)
    
    def get_supported_types(self) -> Dict[str, List[str]]:
        """Get list of supported file types."""
        return {
            'images': list(self.supported_image_types),
            'documents': list(self.supported_document_types),
            'code': list(self.supported_code_types)
        }
    
    def cleanup_old_files(self, days_old: int = 30):
        """Clean up old uploaded files."""
        try:
            current_time = datetime.now().timestamp()
            cutoff_time = current_time - (days_old * 24 * 3600)
            
            removed_count = 0
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.isfile(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        removed_count += 1
            
            logger.info(f"Cleaned up {removed_count} old files")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """Get file handler statistics."""
        try:
            file_count = 0
            total_size = 0
            
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.isfile(file_path):
                    file_count += 1
                    total_size += os.path.getsize(file_path)
            
            return {
                'upload_dir': self.upload_dir,
                'file_count': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'max_file_size_mb': round(self.max_file_size / (1024 * 1024), 2),
                'supported_types': self.get_supported_types()
            }
            
        except Exception as e:
            logger.error(f"Error getting file stats: {e}")
            return {'error': str(e)}

# Global file handler instance
_file_handler = None

def get_file_handler() -> FileHandler:
    """Get global file handler instance."""
    global _file_handler
    if _file_handler is None:
        _file_handler = FileHandler()
    return _file_handler