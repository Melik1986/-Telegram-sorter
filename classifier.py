"""
AI-powered content classifier using OpenAI API.
"""

import json
import logging
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
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate and clean result
            return self._validate_classification(result)
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return None
    
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
        """Fallback classification using text patterns."""
        content_lower = content.lower()
        
        # Code patterns
        code_patterns = [
            r'def\s+\w+\s*\(',  # Python functions
            r'function\s+\w+\s*\(',  # JavaScript functions
            r'class\s+\w+',  # Class definitions
            r'import\s+\w+',  # Import statements
            r'#include\s*<\w+>',  # C/C++ includes
            r'```[\w]*\n',  # Code blocks
        ]
        
        if any(re.search(pattern, content) for pattern in code_patterns):
            return 'code_examples'
        
        # Video patterns
        video_keywords = ['youtube.com', 'vimeo.com', 'youtu.be', 'video', 'watch', 'tutorial video']
        if any(keyword in content_lower for keyword in video_keywords):
            return 'videos'
        
        # Tutorial patterns
        tutorial_keywords = ['tutorial', 'how to', 'step by step', 'guide', 'learn', 'course']
        if any(keyword in content_lower for keyword in tutorial_keywords):
            return 'tutorials'
        
        # Documentation patterns
        doc_keywords = ['documentation', 'docs', 'api reference', 'manual', 'readme']
        if any(keyword in content_lower for keyword in doc_keywords):
            return 'documentation'
        
        # Tool patterns
        tool_keywords = ['tool', 'utility', 'software', 'application', 'download']
        if any(keyword in content_lower for keyword in tool_keywords):
            return 'tools'
        
        return 'other'
