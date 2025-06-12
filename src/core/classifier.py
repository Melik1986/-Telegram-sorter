"""
AI-powered content classifier using OpenAI API.
"""

import asyncio
import json
import logging
import os
import re
import requests
from src.utils.utils import analyze_url_content
from src.core.config import get_ai_config, get_ollama_config, is_ollama_available, is_groq_available

logger = logging.getLogger(__name__)

class ContentClassifier:
    def __init__(self):
        """Initialize the classifier."""
        self.ai_config = get_ai_config()
        self.provider = self.ai_config['provider']
        
        # Legacy support
        self.ollama_config = get_ollama_config()
        self.ollama_available = is_ollama_available()
        
        if self.provider == 'fallback':
            logger.warning("No AI provider available. Using fallback classification.")
        else:
            logger.info(f"AI classifier initialized with provider: {self.provider}")
        
        # Define content categories with improved keywords
        self.categories = {
            'documentation': ['docs', 'documentation', 'guide', 'tutorial', 'readme', 'manual', 'wiki', 'help', 'instructions'],
            'code_examples': ['code', 'programming', 'script', 'function', 'class', 'algorithm', 'source', 'implementation', 'snippet'],
            'tutorials': ['tutorial', 'guide', 'how-to', 'walkthrough', 'step-by-step', 'lesson', 'course'],
            'videos': ['video', 'youtube', 'vimeo', 'watch', 'stream', 'recording'],
            'mockups': ['mockup', 'wireframe', 'prototype', 'design', 'figma', 'sketch'],
            'libraries': ['library', 'package', 'npm', 'pip', 'composer', 'dependency'],
            'frameworks': ['framework', 'boilerplate', 'template', 'scaffold'],
            'tools': ['tool', 'utility', 'software', 'application', 'plugin', 'extension'],
            'articles': ['article', 'blog', 'post', 'news', 'story'],
            'api': ['api', 'endpoint', 'rest', 'graphql', 'webhook', 'service', 'microservice', 'integration'],
            'database': ['database', 'sql', 'query', 'schema', 'table', 'migration', 'mongodb', 'postgresql', 'mysql'],
            'learning': ['course', 'tutorial', 'lesson', 'education', 'training', 'workshop', 'webinar', 'certification'],
            'reference': ['reference', 'cheatsheet', 'quick', 'summary', 'overview', 'specification', 'standard'],
            'design': ['design', 'ui', 'ux', 'mockup', 'wireframe', 'prototype', 'figma', 'sketch'],
            'media': ['image', 'video', 'audio', 'photo', 'picture', 'screenshot', 'diagram', 'chart'],
            'document': ['document', 'pdf', 'report', 'presentation', 'spreadsheet', 'text', 'file'],
            'security': ['security', 'authentication', 'authorization', 'encryption', 'vulnerability', 'penetration'],
            'devops': ['devops', 'deployment', 'ci/cd', 'docker', 'kubernetes', 'infrastructure', 'monitoring'],
            'other': ['misc', 'general', 'various', 'other', 'uncategorized']
        }
    
    async def classify_content(self, content: str, urls: list = None) -> dict:
        """Classify content using available AI provider."""
        try:
            # Check if AI is available
            if self.provider == 'fallback':
                logger.info("Using pattern-based classification (no AI provider available)")
                fallback_category = self.classify_by_patterns(content)
                subcategory = self.get_subcategory_for_pattern(content, fallback_category)
                return {
                    'category': fallback_category,
                    'confidence': 0.8,
                    'description': f'Улучшенная классификация по паттернам: {fallback_category}',
                    'subcategory': subcategory
                }
            
            # Prepare content for analysis
            analysis_content = content
            
            # Add URL analysis if URLs are present
            if urls:
                url_info = []
                for url in urls[:3]:  # Limit to first 3 URLs
                    url_analysis = analyze_url_content(url)
                    if url_analysis:
                        url_info.append(f"URL: {url} - {url_analysis}")
                
                if url_info:
                    analysis_content += "\n\nURL Analysis:\n" + "\n".join(url_info)
            
            # Create classification prompt
            prompt = self._create_classification_prompt(analysis_content)
            
            # Make request to AI API based on provider
            if self.provider == 'groq':
                response = await self._call_groq_api(prompt)
            elif self.provider == 'ollama':
                response = await self._call_ollama_api(prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
            
            if response:
                result = json.loads(response)
            else:
                raise ValueError(f"Empty response from {self.provider}")
            
            # Validate and clean result
            return self._validate_classification(result)
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            # Fallback to pattern-based classification
            fallback_category = self.classify_by_patterns(content)
            subcategory = self.get_subcategory_for_pattern(content, fallback_category)
            
            # Special handling for timeout errors
            error_message = str(e)
            if 'timeout' in error_message.lower() or isinstance(e, asyncio.TimeoutError):
                error_message = 'Request timeout'
            
            return {
                'category': fallback_category,
                'confidence': 0.8,
                'description': f'Улучшенная классификация по паттернам: {fallback_category}',
                'subcategory': subcategory,
                'error': error_message
            }
    
    async def _call_groq_api(self, prompt: str) -> str:
        """Make async request to Groq API."""
        try:
            from groq import Groq
            
            client = Groq(api_key=self.ai_config['api_key'])
            
            system_prompt = (
                "You are an expert content classifier for developer resources. "
                "Analyze content and classify it into appropriate categories. "
                "Respond with JSON only, no additional text."
            )
            
            # Use asyncio to make non-blocking request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=self.ai_config['model'],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1000,
                    timeout=30
                )
            )
            
            if response and response.choices:
                return response.choices[0].message.content
            else:
                logger.error("Groq API returned empty response")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            raise e
    
    async def _call_ollama_api(self, prompt: str) -> str:
        """Make async request to Ollama API."""
        try:
            url = f"{self.ollama_config['base_url']}/api/generate"
            
            system_prompt = (
                "You are an expert content classifier for developer resources. "
                "Analyze content and classify it into appropriate categories. "
                "Respond with JSON only, no additional text."
            )
            
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            payload = {
                "model": self.ollama_config['model'],
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            }
            
            # Use asyncio to make non-blocking request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(url, json=payload, timeout=30)
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            raise e
    
    def _create_classification_prompt(self, content: str) -> str:
        """Create classification prompt for Ollama."""
        categories_text = "\n".join([f"- {cat}: {desc}" for cat, desc in self.categories.items()])
        
        prompt = f"""\nAnalyze the following developer resource content and classify it into one of these categories:\n\n{categories_text}\n\nContent to analyze:\n{content}\n\nProvide your response in JSON format with these fields:\n- "category": the most appropriate category from the list above\n- "subcategory": a more specific subcategory if applicable (optional)\n- "confidence": confidence score from 0.0 to 1.0\n- "description": brief description of the content (max 100 chars)\n- "programming_languages": list of detected programming languages (if any)\n- "topics": list of main topics/keywords (max 5)\n\nExample response:\n{{\n    "category": "code_examples",\n    "subcategory": "python_scripts",\n    "confidence": 0.95,\n    "description": "Python script for data processing",\n    "programming_languages": ["python"],\n    "topics": ["data processing", "pandas", "automation"]\n}}\n\nRespond with JSON only, no additional text.\n        """
        return prompt
    
    def _validate_classification(self, result: dict) -> dict:
        """Validate and clean classification result."""
        if not result or not isinstance(result, dict):
            return None
        
        # Ensure category is valid
        category = result.get('category', '').lower()
        if category not in self.categories:
            category = 'other'
        
        # Clean and validate fields
        confidence = max(0.0, min(1.0, float(result.get('confidence', 0.0))))
        cleaned_result = {
            'category': category,
            'confidence': confidence,
            'description': str(result.get('description', ''))[:100],
        }
        
        # Add low confidence flag if confidence is below threshold
        if confidence < 0.5:
            cleaned_result['low_confidence'] = True
        
        # Optional fields
        if result.get('subcategory'):
            cleaned_result['subcategory'] = str(result['subcategory'])[:50]
        
        if result.get('programming_languages'):
            langs = result['programming_languages']
            if isinstance(langs, list):
                cleaned_result['programming_languages'] = langs[:5]
        
        if result.get('topics'):
            topics = result['topics']
            if isinstance(topics, list):
                cleaned_result['topics'] = topics[:5]
        
        return cleaned_result
    
    def classify_by_patterns(self, content: str) -> str:
        """Enhanced fallback classification using text patterns."""
        content_lower = content.lower()
        
        # Code patterns (enhanced)
        code_patterns = [
            r'def\s+\w+\s*\(',  # Python functions
            r'function\s+\w+\s*\(',  # JavaScript functions
            r'class\s+\w+',  # Class definitions
            r'import\s+\w+',  # Import statements
            r'#include\s*<\w+>',  # C/C++ includes
            r'```[\w]*\n',  # Code blocks
            r'<\w+[^>]*>.*</\w+>',  # HTML tags
            r'{\s*["\w]+\s*:\s*["\w]+',  # JSON objects
            r'public\s+class\s+\w+',  # Java classes
            r'const\s+\w+\s*=',  # JavaScript const
            r'var\s+\w+\s*=',  # Variable declarations
            r'\$\w+\s*=',  # PHP variables
        ]
        
        # Code repository patterns
        code_repo_keywords = ['github.com', 'gitlab.com', 'bitbucket.org', 'repository', 'repo', 'source code', 'git clone']
        
        # Programming language keywords
        programming_languages = ['python', 'javascript', 'java', 'cpp', 'c++', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'typescript', 'react', 'vue', 'angular', 'node.js', 'django', 'flask', 'spring']
        
        # Check for code patterns first
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in code_patterns):
            return 'code_examples'
        
        # Check for code repositories
        if any(keyword in content_lower for keyword in code_repo_keywords):
            return 'code_examples'
        
        # Video patterns (enhanced) - check first
        video_keywords = ['youtube.com', 'vimeo.com', 'youtu.be', 'video', 'watch', 'видео', 'смотреть']
        video_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'twitch.tv']
        if any(keyword in content_lower for keyword in video_keywords) or any(domain in content_lower for domain in video_domains):
            return 'videos'
        
        # Tutorial patterns (enhanced) - check before programming languages
        tutorial_keywords = ['tutorial', 'туториале', 'how to', 'step by step', 'guide', 'learn', 'course', 'урок', 'обучение', 'пошагово', 'руководство']
        if any(keyword in content_lower for keyword in tutorial_keywords):
            return 'tutorials'
        
        # Check for programming languages - only if not already classified as tutorial
        if any(lang in content_lower for lang in programming_languages):
            return 'code_examples'
        
        # Documentation patterns (enhanced)
        doc_keywords = ['documentation', 'docs', 'api reference', 'manual', 'readme', 'документация', 'справочник']
        if any(keyword in content_lower for keyword in doc_keywords):
            return 'documentation'
        
        # Design/Mockup patterns
        design_keywords = ['figma', 'sketch', 'adobe', 'design', 'mockup', 'wireframe', 'prototype', 'ui', 'ux', 'дизайн', 'макет']
        if any(keyword in content_lower for keyword in design_keywords):
            return 'mockups'
        
        # Library patterns
        library_keywords = ['library', 'package', 'npm', 'pip install', 'composer', 'библиотека', 'пакет']
        if any(keyword in content_lower for keyword in library_keywords):
            return 'libraries'
        
        # Framework patterns
        framework_keywords = ['framework', 'boilerplate', 'template', 'фреймворк', 'шаблон']
        frameworks = ['react', 'vue', 'angular', 'django', 'flask', 'spring', 'laravel', 'express']
        if any(keyword in content_lower for keyword in framework_keywords) or any(fw in content_lower for fw in frameworks):
            return 'frameworks'
        
        # Tool patterns (enhanced)
        tool_keywords = ['tool', 'utility', 'software', 'application', 'download', 'инструмент', 'утилита', 'программа']
        if any(keyword in content_lower for keyword in tool_keywords):
            return 'tools'
        
        # Article patterns
        article_keywords = ['article', 'blog', 'post', 'статья', 'блог']
        if any(keyword in content_lower for keyword in article_keywords):
            return 'articles'
        
        return 'other'
    
    def get_subcategory_for_pattern(self, content: str, category: str) -> str:
        """Determine subcategory based on content patterns."""
        content_lower = content.lower()
        
        if category == 'code_examples':
            # Python patterns
            if any(pattern in content_lower for pattern in ['def ', 'import ', 'python', '.py']):
                return 'python_scripts'
            # JavaScript patterns
            elif any(pattern in content_lower for pattern in ['function ', 'javascript', 'js', 'const ', 'var ', 'let ']):
                return 'javascript_snippets'
            # SQL patterns
            elif any(pattern in content_lower for pattern in ['select ', 'from ', 'where ', 'join ', 'sql']):
                return 'database_queries'
            # HTML/CSS patterns
            elif any(pattern in content_lower for pattern in ['<html', '<div', '<p>', 'css', 'html']):
                return 'web_markup'
            else:
                return 'general_code'
                
        elif category == 'tutorials':
            # Web development tutorials
            if any(pattern in content_lower for pattern in ['веб', 'web', 'сайт', 'website', 'html', 'css']):
                return 'web_development'
            # Git/Version control tutorials
            elif any(pattern in content_lower for pattern in ['git', 'github', 'версий', 'version control']):
                return 'version_control'
            # Python tutorials
            elif any(pattern in content_lower for pattern in ['python', 'pandas', 'numpy']):
                return 'python_tutorial'
            else:
                return 'general_tutorial'
                
        elif category == 'documentation':
            # API documentation
            if any(pattern in content_lower for pattern in ['api', 'endpoint', 'get /', 'post /']):
                return 'api_reference'
            # Library documentation
            elif any(pattern in content_lower for pattern in ['библиотек', 'library', 'pandas', 'numpy']):
                return 'library_docs'
            else:
                return 'general_docs'
                
        elif category == 'videos':
            return 'video_content'
            
        elif category == 'mockups':
            return 'ui_design'
            
        elif category == 'tools':
            return 'development_tools'
            
        elif category == 'libraries':
            return 'code_libraries'
            
        elif category == 'frameworks':
            return 'dev_frameworks'
            
        elif category == 'articles':
            return 'tech_articles'
            
        return 'general'
