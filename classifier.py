"""
AI-powered content classifier using OpenAI API.
"""

import json
import logging
import os
import re
from openai import OpenAI
from utils import analyze_url_content

logger = logging.getLogger(__name__)

class ContentClassifier:
    def __init__(self, api_key):
        """Initialize the classifier with OpenAI API."""
        self.client = OpenAI(api_key=api_key)
        
        # Category definitions
        self.categories = {
            'code_examples': 'Code snippets, example implementations, sample code',
            'tutorials': 'Step-by-step guides, how-to articles, learning materials',
            'videos': 'Video content, video tutorials, recorded presentations',
            'mockups': 'UI/UX designs, wireframes, prototypes, design templates',
            'documentation': 'API docs, technical documentation, reference materials',
            'tools': 'Development tools, utilities, software applications',
            'articles': 'Technical articles, blog posts, news',
            'libraries': 'Code libraries, packages, modules',
            'frameworks': 'Development frameworks, boilerplates',
            'other': 'Content that doesn\'t fit other categories'
        }
    
    async def classify_content(self, content: str, urls: list = None) -> dict:
        """Classify content using OpenAI API."""
        try:
            # Check if API key is valid OpenAI format
            api_key = os.getenv('OPENAI_API_KEY', '')
            if not api_key.startswith('sk-'):
                logger.info("Using pattern-based classification (OpenAI key not configured)")
                fallback_category = self.classify_by_patterns(content)
                return {
                    'category': fallback_category,
                    'confidence': 0.8,
                    'description': f'Улучшенная классификация по паттернам: {fallback_category}',
                    'subcategory': None
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
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content classifier for developer resources. "
                        + "Analyze content and classify it into appropriate categories. "
                        + "Respond with JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
            else:
                raise ValueError("Empty response from OpenAI")
            
            # Validate and clean result
            return self._validate_classification(result)
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            # Fallback to pattern-based classification
            fallback_category = self.classify_by_patterns(content)
            return {
                'category': fallback_category,
                'confidence': 0.8,
                'description': f'Улучшенная классификация по паттернам: {fallback_category}',
                'subcategory': None
            }
    
    def _create_classification_prompt(self, content: str) -> str:
        """Create classification prompt for OpenAI."""
        categories_text = "\n".join([f"- {cat}: {desc}" for cat, desc in self.categories.items()])
        
        prompt = f"""
Analyze the following developer resource content and classify it into one of these categories:

{categories_text}

Content to analyze:
{content}

Provide your response in JSON format with these fields:
- "category": the most appropriate category from the list above
- "subcategory": a more specific subcategory if applicable (optional)
- "confidence": confidence score from 0.0 to 1.0
- "description": brief description of the content (max 100 chars)
- "programming_languages": list of detected programming languages (if any)
- "topics": list of main topics/keywords (max 5)

Example response:
{{
    "category": "code_examples",
    "subcategory": "python_scripts",
    "confidence": 0.95,
    "description": "Python script for data processing",
    "programming_languages": ["python"],
    "topics": ["data processing", "pandas", "automation"]
}}

Respond with JSON only, no additional text.
        """
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
        cleaned_result = {
            'category': category,
            'confidence': max(0.0, min(1.0, float(result.get('confidence', 0.0)))),
            'description': str(result.get('description', ''))[:100],
        }
        
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
        
        # Check for programming languages
        if any(lang in content_lower for lang in programming_languages):
            # If mentioned with tutorial keywords, classify as tutorial
            tutorial_keywords = ['tutorial', 'how to', 'step by step', 'guide', 'learn', 'course', 'урок', 'обучение']
            if any(keyword in content_lower for keyword in tutorial_keywords):
                return 'tutorials'
            else:
                return 'code_examples'
        
        # Video patterns (enhanced)
        video_keywords = ['youtube.com', 'vimeo.com', 'youtu.be', 'video', 'watch', 'видео', 'смотреть']
        video_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'twitch.tv']
        if any(keyword in content_lower for keyword in video_keywords) or any(domain in content_lower for domain in video_domains):
            return 'videos'
        
        # Tutorial patterns (enhanced)
        tutorial_keywords = ['tutorial', 'how to', 'step by step', 'guide', 'learn', 'course', 'урок', 'обучение', 'пошагово', 'руководство']
        if any(keyword in content_lower for keyword in tutorial_keywords):
            return 'tutorials'
        
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
