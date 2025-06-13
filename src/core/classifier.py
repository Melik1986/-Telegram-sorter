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
        
        # Define content categories optimized for web development
        self.categories = {
            # Frontend Development
            'frontend': {
                'keywords': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'svelte', 'frontend', 'client-side', 'browser', 'dom', 'responsive', 'mobile-first'],
                'description': 'Frontend technologies, frameworks, and client-side development'
            },
            'css_styling': {
                'keywords': ['css', 'sass', 'scss', 'less', 'tailwind', 'bootstrap', 'styled-components', 'emotion', 'flexbox', 'grid', 'animation', 'transition'],
                'description': 'CSS frameworks, styling libraries, and design systems'
            },
            'javascript': {
                'keywords': ['javascript', 'js', 'typescript', 'ts', 'es6', 'es2015', 'vanilla', 'jquery', 'lodash', 'moment'],
                'description': 'JavaScript libraries, utilities, and vanilla JS solutions'
            },
            'react_ecosystem': {
                'keywords': ['react', 'jsx', 'next.js', 'gatsby', 'redux', 'mobx', 'react-router', 'hooks', 'context', 'component'],
                'description': 'React framework, libraries, and ecosystem tools'
            },
            'vue_ecosystem': {
                'keywords': ['vue', 'vuex', 'nuxt', 'vue-router', 'composition-api', 'pinia', 'quasar'],
                'description': 'Vue.js framework, libraries, and ecosystem tools'
            },
            'angular_ecosystem': {
                'keywords': ['angular', 'typescript', 'rxjs', 'ngrx', 'angular-cli', 'material', 'ionic'],
                'description': 'Angular framework, libraries, and ecosystem tools'
            },
            
            # Backend Development
            'backend': {
                'keywords': ['backend', 'server', 'api', 'rest', 'graphql', 'microservices', 'serverless', 'lambda', 'node.js', 'express', 'fastify'],
                'description': 'Backend technologies, APIs, and server-side development'
            },
            'nodejs': {
                'keywords': ['node.js', 'nodejs', 'npm', 'yarn', 'express', 'koa', 'fastify', 'nest.js', 'socket.io'],
                'description': 'Node.js runtime, frameworks, and server-side JavaScript'
            },
            'python_web': {
                'keywords': ['django', 'flask', 'fastapi', 'pyramid', 'tornado', 'python', 'wsgi', 'asgi'],
                'description': 'Python web frameworks and server-side development'
            },
            'php_web': {
                'keywords': ['php', 'laravel', 'symfony', 'codeigniter', 'wordpress', 'drupal', 'composer'],
                'description': 'PHP frameworks and content management systems'
            },
            
            # Database & Storage
            'database': {
                'keywords': ['database', 'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'prisma', 'sequelize', 'mongoose'],
                'description': 'Database systems, ORMs, and data storage solutions'
            },
            
            # Development Tools
            'build_tools': {
                'keywords': ['webpack', 'vite', 'rollup', 'parcel', 'gulp', 'grunt', 'babel', 'esbuild', 'swc'],
                'description': 'Build tools, bundlers, and development workflow'
            },
            'testing': {
                'keywords': ['jest', 'mocha', 'chai', 'cypress', 'playwright', 'testing-library', 'vitest', 'unit-test', 'e2e'],
                'description': 'Testing frameworks, tools, and methodologies'
            },
            'devops_web': {
                'keywords': ['docker', 'kubernetes', 'ci/cd', 'github-actions', 'jenkins', 'vercel', 'netlify', 'aws', 'heroku'],
                'description': 'DevOps tools, deployment, and infrastructure for web development'
            },
            
            # Design & UI/UX
            'ui_design': {
                'keywords': ['ui', 'ux', 'design-system', 'figma', 'sketch', 'adobe-xd', 'wireframe', 'prototype', 'mockup'],
                'description': 'UI/UX design, design systems, and prototyping tools'
            },
            'icons_assets': {
                'keywords': ['icons', 'svg', 'fonts', 'images', 'assets', 'illustrations', 'graphics', 'logo'],
                'description': 'Icons, fonts, images, and visual assets'
            },
            
            # Learning Resources
            'tutorials': {
                'keywords': ['tutorial', 'guide', 'how-to', 'walkthrough', 'step-by-step', 'lesson', 'course', 'learning'],
                'description': 'Educational content, tutorials, and learning materials'
            },
            'videos': {
                'keywords': ['video', 'youtube', 'vimeo', 'watch', 'stream', 'recording', 'webinar', 'conference'],
                'description': 'Video content, tutorials, and educational streams'
            },
            'documentation': {
                'keywords': ['docs', 'documentation', 'api-docs', 'readme', 'manual', 'wiki', 'reference', 'specification'],
                'description': 'Documentation, API references, and technical guides'
            },
            
            # Code Resources
            'code_snippets': {
                'keywords': ['snippet', 'code', 'example', 'gist', 'codepen', 'jsfiddle', 'sandbox', 'playground'],
                'description': 'Code snippets, examples, and interactive demos'
            },
            'templates': {
                'keywords': ['template', 'boilerplate', 'starter', 'scaffold', 'theme', 'layout', 'component-library'],
                'description': 'Project templates, boilerplates, and starter kits'
            },
            'libraries': {
                'keywords': ['library', 'package', 'npm', 'yarn', 'cdn', 'plugin', 'extension', 'module'],
                'description': 'Third-party libraries, packages, and plugins'
            },
            
            # Specialized
            'animation': {
                'keywords': ['animation', 'gsap', 'framer-motion', 'lottie', 'three.js', 'webgl', 'canvas', 'svg-animation'],
                'description': 'Animation libraries, WebGL, and interactive graphics'
            },
            'performance': {
                'keywords': ['performance', 'optimization', 'lighthouse', 'web-vitals', 'lazy-loading', 'caching', 'compression'],
                'description': 'Performance optimization, monitoring, and best practices'
            },
            'security': {
                'keywords': ['security', 'authentication', 'authorization', 'jwt', 'oauth', 'cors', 'csrf', 'xss'],
                'description': 'Web security, authentication, and security best practices'
            },
            
            # General
            'articles': {
                'keywords': ['article', 'blog', 'post', 'news', 'story', 'opinion', 'review'],
                'description': 'Articles, blog posts, and technical writing'
            },
            'tools': {
                'keywords': ['tool', 'utility', 'software', 'application', 'extension', 'addon', 'helper'],
                'description': 'Development tools, utilities, and productivity software'
            },
            'other': {
                'keywords': ['misc', 'general', 'various', 'other', 'uncategorized'],
                'description': 'Miscellaneous content that doesn\'t fit other categories'
            }
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
        """Create enhanced classification prompt optimized for web development."""
        categories_info = []
        for category, info in self.categories.items():
            keywords = ', '.join(info['keywords'][:8])  # Limit keywords for prompt size
            categories_info.append(f"- {category}: {info['description']} (keywords: {keywords}...)")
        
        categories_text = '\n'.join(categories_info)
        
        prompt = f"""\nAnalyze the following developer resource content and classify it into one of these categories:\n\n{categories_text}\n\nCLASSIFICATION GUIDELINES:\n1. Prioritize web development technologies (frontend, backend, databases)\n2. Consider the primary purpose and target audience of the content\n3. Look for specific technology mentions, frameworks, and tools\n4. Distinguish between learning resources (tutorials, videos) and practical resources (code, tools)\n5. For mixed content, choose the most prominent or useful aspect\n\nEXAMPLES:\n- "React hooks tutorial" → react_ecosystem (not tutorials, as React is more specific)\n- "CSS Grid complete guide" → css_styling (specific CSS technology)\n- "Node.js REST API example" → nodejs (backend technology focus)\n- "Figma design system" → ui_design (design tool focus)\n- "JavaScript performance optimization" → performance (optimization focus)\n\nContent to analyze:\n{content}\n\nProvide your response in JSON format with these fields:\n- "category": the most appropriate category from the list above\n- "subcategory": a more specific subcategory if applicable (optional)\n- "confidence": confidence score from 0.0 to 1.0 (be conservative, use 0.7+ only for clear matches)\n- "description": brief description of the content (max 100 chars)\n- "programming_languages": list of detected programming languages (if any)\n- "topics": list of main topics/keywords (max 5)\n- "technology_stack": array of specific technologies mentioned (e.g., ["React", "TypeScript", "Node.js"])\n\nExample response:\n{{\n    "category": "react_ecosystem",\n    "subcategory": "hooks",\n    "confidence": 0.85,\n    "description": "React hooks tutorial with practical examples",\n    "programming_languages": ["javascript"],\n    "topics": ["react", "hooks", "tutorial", "frontend", "components"],\n    "technology_stack": ["React", "JavaScript"]\n}}\n\nRespond with JSON only, no additional text.\n        """
        return prompt
    
    def _validate_classification(self, result: dict) -> dict:
        """Validate and clean classification result with enhanced validation."""
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
        
        # Optional fields with enhanced validation
        if result.get('subcategory'):
            cleaned_result['subcategory'] = str(result['subcategory'])[:50]
        
        if result.get('programming_languages'):
            langs = result['programming_languages']
            if isinstance(langs, list):
                # Clean and normalize programming languages
                cleaned_langs = [lang.lower().strip() for lang in langs if isinstance(lang, str)][:5]
                if cleaned_langs:
                    cleaned_result['programming_languages'] = cleaned_langs
        
        if result.get('topics'):
            topics = result['topics']
            if isinstance(topics, list):
                # Clean and normalize topics
                cleaned_topics = [topic.lower().strip() for topic in topics if isinstance(topic, str)][:5]
                if cleaned_topics:
                    cleaned_result['topics'] = cleaned_topics
        
        if result.get('technology_stack'):
            tech_stack = result['technology_stack']
            if isinstance(tech_stack, list):
                # Clean and normalize technology stack
                cleaned_tech = [tech.strip() for tech in tech_stack if isinstance(tech, str)][:8]
                if cleaned_tech:
                    cleaned_result['technology_stack'] = cleaned_tech
        
        if result.get('reasoning'):
            cleaned_result['reasoning'] = str(result['reasoning'])[:200]
        
        return cleaned_result
    
    def classify_by_patterns(self, content: str) -> str:
        """Enhanced fallback classification using text patterns."""
        content_lower = content.lower()
        
        # Score each category based on keyword matches with weighted scoring
        category_scores = {}
        
        for category, category_info in self.categories.items():
            keywords = category_info['keywords']
            score = 0
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in content_lower:
                    # Weight scoring based on keyword specificity
                    weight = self._get_keyword_weight(keyword_lower)
                    score += weight
            
            if score > 0:
                category_scores[category] = score
        
        if not category_scores:
            return 'other'
        
        # Find the category with the highest score
        best_category = max(category_scores.keys(), key=lambda k: category_scores[k])
        
        return best_category
    
    def _get_keyword_weight(self, keyword: str) -> float:
        """Calculate weight for keyword based on specificity."""
        # More specific technology keywords get higher weight
        high_weight_keywords = {
            'react', 'vue', 'angular', 'svelte', 'next.js', 'nuxt', 'gatsby',
            'typescript', 'javascript', 'python', 'php', 'node.js',
            'mongodb', 'postgresql', 'mysql', 'redis',
            'webpack', 'vite', 'docker', 'kubernetes',
            'figma', 'sketch', 'tailwind', 'bootstrap'
        }
        
        medium_weight_keywords = {
            'frontend', 'backend', 'api', 'database', 'css', 'html',
            'tutorial', 'guide', 'documentation', 'testing'
        }
        
        if keyword in high_weight_keywords:
            return 3.0
        elif keyword in medium_weight_keywords:
            return 2.0
        else:
            return 1.0
    
    def get_subcategory_for_pattern(self, content: str, category: str) -> str:
        """Get more specific subcategory based on content patterns for web development."""
        content_lower = content.lower()
        
        # Frontend subcategories
        if category == 'frontend':
            if any(word in content_lower for word in ['responsive', 'mobile-first', 'breakpoint']):
                return 'responsive_design'
            elif any(word in content_lower for word in ['component', 'ui-component']):
                return 'components'
            elif any(word in content_lower for word in ['spa', 'single-page']):
                return 'spa'
        
        elif category == 'css_styling':
            if any(word in content_lower for word in ['flexbox', 'flex']):
                return 'flexbox'
            elif any(word in content_lower for word in ['grid', 'css-grid']):
                return 'css_grid'
            elif any(word in content_lower for word in ['animation', 'transition']):
                return 'animations'
            elif any(word in content_lower for word in ['sass', 'scss']):
                return 'preprocessors'
        
        elif category == 'javascript':
            if any(word in content_lower for word in ['es6', 'es2015', 'arrow-function']):
                return 'modern_js'
            elif any(word in content_lower for word in ['async', 'await', 'promise']):
                return 'async_programming'
            elif any(word in content_lower for word in ['dom', 'manipulation']):
                return 'dom_manipulation'
        
        elif category == 'react_ecosystem':
            if any(word in content_lower for word in ['hooks', 'usestate', 'useeffect']):
                return 'hooks'
            elif any(word in content_lower for word in ['redux', 'state-management']):
                return 'state_management'
            elif any(word in content_lower for word in ['next.js', 'nextjs']):
                return 'nextjs'
            elif any(word in content_lower for word in ['testing', 'jest', 'react-testing-library']):
                return 'testing'
        
        elif category == 'vue_ecosystem':
            if any(word in content_lower for word in ['composition-api', 'composition']):
                return 'composition_api'
            elif any(word in content_lower for word in ['vuex', 'pinia']):
                return 'state_management'
            elif any(word in content_lower for word in ['nuxt', 'nuxtjs']):
                return 'nuxtjs'
        
        elif category == 'angular_ecosystem':
            if any(word in content_lower for word in ['component', 'directive']):
                return 'components'
            elif any(word in content_lower for word in ['service', 'dependency-injection']):
                return 'services'
            elif any(word in content_lower for word in ['rxjs', 'observable']):
                return 'rxjs'
        
        # Backend subcategories
        elif category == 'backend':
            if any(word in content_lower for word in ['rest', 'restful']):
                return 'rest_api'
            elif any(word in content_lower for word in ['graphql']):
                return 'graphql'
            elif any(word in content_lower for word in ['microservices', 'microservice']):
                return 'microservices'
            elif any(word in content_lower for word in ['serverless', 'lambda']):
                return 'serverless'
        
        elif category == 'nodejs':
            if any(word in content_lower for word in ['express', 'expressjs']):
                return 'express'
            elif any(word in content_lower for word in ['nest', 'nestjs']):
                return 'nestjs'
            elif any(word in content_lower for word in ['socket', 'websocket']):
                return 'realtime'
        
        elif category == 'database':
            if any(word in content_lower for word in ['mongodb', 'mongo']):
                return 'mongodb'
            elif any(word in content_lower for word in ['postgresql', 'postgres']):
                return 'postgresql'
            elif any(word in content_lower for word in ['mysql']):
                return 'mysql'
            elif any(word in content_lower for word in ['redis']):
                return 'redis'
            elif any(word in content_lower for word in ['prisma', 'orm']):
                return 'orm'
        
        # Development tools subcategories
        elif category == 'build_tools':
            if any(word in content_lower for word in ['webpack']):
                return 'webpack'
            elif any(word in content_lower for word in ['vite']):
                return 'vite'
            elif any(word in content_lower for word in ['rollup']):
                return 'rollup'
        
        elif category == 'testing':
            if any(word in content_lower for word in ['jest']):
                return 'jest'
            elif any(word in content_lower for word in ['cypress']):
                return 'cypress'
            elif any(word in content_lower for word in ['playwright']):
                return 'playwright'
            elif any(word in content_lower for word in ['unit', 'unit-test']):
                return 'unit_testing'
            elif any(word in content_lower for word in ['e2e', 'end-to-end']):
                return 'e2e_testing'
        
        elif category == 'devops_web':
            if any(word in content_lower for word in ['docker']):
                return 'docker'
            elif any(word in content_lower for word in ['kubernetes', 'k8s']):
                return 'kubernetes'
            elif any(word in content_lower for word in ['ci/cd', 'github-actions']):
                return 'ci_cd'
            elif any(word in content_lower for word in ['vercel', 'netlify']):
                return 'hosting'
        
        # Design subcategories
        elif category == 'ui_design':
            if any(word in content_lower for word in ['figma']):
                return 'figma'
            elif any(word in content_lower for word in ['design-system', 'design system']):
                return 'design_systems'
            elif any(word in content_lower for word in ['wireframe']):
                return 'wireframing'
            elif any(word in content_lower for word in ['prototype']):
                return 'prototyping'
        
        # Learning subcategories
        elif category == 'tutorials':
            if any(word in content_lower for word in ['beginner', 'basics', 'introduction']):
                return 'beginner'
            elif any(word in content_lower for word in ['advanced', 'expert']):
                return 'advanced'
            elif any(word in content_lower for word in ['project', 'build']):
                return 'project_based'
        
        elif category == 'videos':
            if any(word in content_lower for word in ['course', 'series']):
                return 'course'
            elif any(word in content_lower for word in ['conference', 'talk']):
                return 'conference'
            elif any(word in content_lower for word in ['live', 'stream']):
                return 'live_stream'
        
        # Legacy fallback patterns
        elif category == 'code_snippets':
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
                
        elif category == 'documentation':
            # API documentation
            if any(pattern in content_lower for pattern in ['api', 'endpoint', 'get /', 'post /']):
                return 'api_reference'
            # Library documentation
            elif any(pattern in content_lower for pattern in ['библиотек', 'library', 'pandas', 'numpy']):
                return 'library_docs'
            else:
                return 'general_docs'
                
        elif category == 'tools':
            return 'development_tools'
            
        elif category == 'libraries':
            return 'code_libraries'
            
        elif category == 'articles':
            return 'tech_articles'
            
        return 'general'
