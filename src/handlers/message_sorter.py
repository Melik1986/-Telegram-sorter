"""Module for sorting and classifying messages."""

import os
import logging
from pathlib import Path
from src.core.classifier import ContentClassifier

logger = logging.getLogger(__name__)

class MessageSorter:
    """Enhanced class for sorting, classifying messages and auto-creating folders."""
    
    def __init__(self, classifier=None, base_folder=None):
        """Initialize the MessageSorter with a classifier and base folder.
        
        Args:
            classifier: An instance of ContentClassifier. If None, a new instance will be created.
            base_folder: Base directory for organizing content. Defaults to './sorted_content'
        """
        self.classifier = classifier or ContentClassifier()
        self.base_folder = Path(base_folder) if base_folder else Path('./sorted_content')
        
        # Category to folder mapping for better organization
        self.category_folders = {
            # Frontend Development
            'frontend': 'Frontend/General',
            'css_styling': 'Frontend/CSS-Styling',
            'javascript': 'Frontend/JavaScript',
            'react_ecosystem': 'Frontend/React',
            'vue_ecosystem': 'Frontend/Vue',
            'angular_ecosystem': 'Frontend/Angular',
            
            # Backend Development
            'backend': 'Backend/General',
            'nodejs': 'Backend/NodeJS',
            'python_web': 'Backend/Python',
            'php_web': 'Backend/PHP',
            
            # Database & Storage
            'database': 'Database',
            
            # Development Tools
            'build_tools': 'DevTools/Build-Tools',
            'testing': 'DevTools/Testing',
            'devops_web': 'DevTools/DevOps',
            
            # Design & UI/UX
            'ui_design': 'Design/UI-UX',
            'icons_assets': 'Design/Assets',
            
            # Learning Resources
            'tutorials': 'Learning/Tutorials',
            'videos': 'Learning/Videos',
            'documentation': 'Learning/Documentation',
            
            # Code Resources
            'code_snippets': 'Code/Snippets',
            'templates': 'Code/Templates',
            'libraries': 'Code/Libraries',
            
            # Specialized
            'animation': 'Specialized/Animation',
            'performance': 'Specialized/Performance',
            'security': 'Specialized/Security',
            
            # General
            'articles': 'General/Articles',
            'tools': 'General/Tools',
            'other': 'General/Other'
        }
        
        # Ensure base folder exists
        self._ensure_base_folder()
    
    def _ensure_base_folder(self):
        """Ensure the base folder exists."""
        try:
            self.base_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Base folder ensured: {self.base_folder}")
        except Exception as e:
            logger.error(f"Failed to create base folder {self.base_folder}: {e}")
    
    async def sort_message(self, message, auto_create_folders=True):
        """Sort and classify a message with optional folder creation.
        
        Args:
            message: A dictionary containing message data with at least a 'text' field.
            auto_create_folders: Whether to automatically create folders based on classification.
            
        Returns:
            A dictionary with classification results and folder information.
        """
        if not message or 'text' not in message:
            return {
                'category': 'other',
                'confidence': 0.0,
                'description': 'Empty or invalid message',
                'folder_path': None
            }
        
        # Extract message text
        text = message['text']
        
        # Classify the content
        classification = await self.classifier.classify_content(text)
        
        # Add folder information
        folder_info = None
        if auto_create_folders:
            folder_info = self._create_folder_for_classification(classification)
            classification['folder_path'] = folder_info['path'] if folder_info else None
            classification['folder_created'] = folder_info['created'] if folder_info else False
        
        return classification
    
    def _create_folder_for_classification(self, classification):
        """Create folder structure based on classification results.
        
        Args:
            classification: Classification result dictionary
            
        Returns:
            Dictionary with folder path and creation status
        """
        try:
            category = classification.get('category', 'other')
            subcategory = classification.get('subcategory')
            
            # Get base folder path for category
            base_category_path = self.category_folders.get(category, f'General/{category.title()}')
            folder_path = self.base_folder / base_category_path
            
            # Add subcategory if available
            if subcategory:
                # Clean subcategory name for folder
                clean_subcategory = self._clean_folder_name(subcategory)
                folder_path = folder_path / clean_subcategory
            
            # Add technology-specific subfolder if available
            tech_stack = classification.get('technology_stack', [])
            if tech_stack and len(tech_stack) == 1:
                # If only one technology, create a subfolder for it
                tech_name = self._clean_folder_name(tech_stack[0])
                folder_path = folder_path / tech_name
            
            # Create the folder structure
            folder_created = False
            if not folder_path.exists():
                folder_path.mkdir(parents=True, exist_ok=True)
                folder_created = True
                logger.info(f"Created folder: {folder_path}")
            
            return {
                'path': str(folder_path),
                'created': folder_created,
                'relative_path': str(folder_path.relative_to(self.base_folder))
            }
            
        except Exception as e:
            logger.error(f"Failed to create folder for classification {classification}: {e}")
            return None
    
    def _clean_folder_name(self, name):
        """Clean a string to be used as a folder name.
        
        Args:
            name: String to clean
            
        Returns:
            Cleaned string safe for use as folder name
        """
        if not name:
            return 'Unknown'
        
        # Replace common problematic characters
        cleaned = str(name).strip()
        
        # Replace spaces and special characters with hyphens
        import re
        cleaned = re.sub(r'[\s_]+', '-', cleaned)
        cleaned = re.sub(r'[^a-zA-Z0-9\-.]', '', cleaned)
        
        # Remove multiple consecutive hyphens
        cleaned = re.sub(r'-+', '-', cleaned)
        
        # Remove leading/trailing hyphens
        cleaned = cleaned.strip('-')
        
        # Capitalize for better readability
        cleaned = '-'.join(word.capitalize() for word in cleaned.split('-'))
        
        return cleaned or 'Unknown'
    
    def get_folder_structure(self):
        """Get the current folder structure.
        
        Returns:
            Dictionary representing the folder structure
        """
        structure = {}
        
        try:
            if self.base_folder.exists():
                for item in self.base_folder.rglob('*'):
                    if item.is_dir():
                        rel_path = item.relative_to(self.base_folder)
                        parts = rel_path.parts
                        
                        current = structure
                        for part in parts:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
        except Exception as e:
            logger.error(f"Failed to get folder structure: {e}")
        
        return structure
    
    def get_category_stats(self):
        """Get statistics about folder usage.
        
        Returns:
            Dictionary with category statistics
        """
        stats = {}
        
        try:
            for category, folder_path in self.category_folders.items():
                full_path = self.base_folder / folder_path
                if full_path.exists():
                    # Count subfolders
                    subfolders = [d for d in full_path.iterdir() if d.is_dir()]
                    stats[category] = {
                        'folder_path': folder_path,
                        'exists': True,
                        'subfolders_count': len(subfolders),
                        'subfolders': [d.name for d in subfolders]
                    }
                else:
                    stats[category] = {
                        'folder_path': folder_path,
                        'exists': False,
                        'subfolders_count': 0,
                        'subfolders': []
                    }
        except Exception as e:
            logger.error(f"Failed to get category stats: {e}")
        
        return stats