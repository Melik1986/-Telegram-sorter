"""
Оптимизированный классификатор для Render.
"""

import asyncio
import json
import logging
import re
from .config_render import get_ai_config

logger = logging.getLogger(__name__)

class ContentClassifier:
    def __init__(self):
        """Инициализация классификатора для Render."""
        self.ai_config = get_ai_config()
        self.provider = self.ai_config['provider']
        
        if self.provider == 'fallback':
            logger.warning("Используется fallback классификация без AI")
        else:
            logger.info(f"AI классификатор инициализирован: {self.provider}")
        
        # Расширенные категории для веб-разработки
        self.categories = {
            # Frontend Development
            'frontend': {
                'keywords': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'svelte', 'frontend', 'client-side'],
                'description': 'Frontend разработка'
            },
            'css_styling': {
                'keywords': ['css', 'sass', 'scss', 'less', 'tailwind', 'bootstrap', 'styled-components'],
                'description': 'CSS и стилизация'
            },
            'javascript': {
                'keywords': ['javascript', 'js', 'typescript', 'ts', 'es6', 'vanilla', 'jquery'],
                'description': 'JavaScript и TypeScript'
            },
            'react_ecosystem': {
                'keywords': ['react', 'jsx', 'next.js', 'gatsby', 'redux', 'mobx', 'react-router'],
                'description': 'React экосистема'
            },
            'vue_ecosystem': {
                'keywords': ['vue', 'vuex', 'nuxt', 'vue-router', 'composition-api', 'pinia'],
                'description': 'Vue.js экосистема'
            },
            'angular_ecosystem': {
                'keywords': ['angular', 'typescript', 'rxjs', 'ngrx', 'angular-cli'],
                'description': 'Angular экосистема'
            },
            
            # Backend Development
            'backend': {
                'keywords': ['backend', 'server', 'api', 'rest', 'graphql', 'microservices'],
                'description': 'Backend разработка'
            },
            'nodejs': {
                'keywords': ['node.js', 'nodejs', 'npm', 'yarn', 'express', 'fastify', 'nest.js'],
                'description': 'Node.js разработка'
            },
            'python_web': {
                'keywords': ['django', 'flask', 'fastapi', 'pyramid', 'python'],
                'description': 'Python веб-разработка'
            },
            'php_web': {
                'keywords': ['php', 'laravel', 'symfony', 'wordpress', 'composer'],
                'description': 'PHP разработка'
            },
            
            # Database & Storage
            'database': {
                'keywords': ['database', 'sql', 'mysql', 'postgresql', 'mongodb', 'redis'],
                'description': 'Базы данных'
            },
            
            # Development Tools
            'build_tools': {
                'keywords': ['webpack', 'vite', 'rollup', 'parcel', 'gulp', 'babel'],
                'description': 'Инструменты сборки'
            },
            'testing': {
                'keywords': ['jest', 'mocha', 'cypress', 'playwright', 'testing-library'],
                'description': 'Тестирование'
            },
            'devops_web': {
                'keywords': ['docker', 'kubernetes', 'ci/cd', 'github-actions', 'vercel', 'netlify'],
                'description': 'DevOps и развертывание'
            },
            
            # Design & UI/UX
            'ui_design': {
                'keywords': ['ui', 'ux', 'design-system', 'figma', 'sketch', 'wireframe'],
                'description': 'UI/UX дизайн'
            },
            
            # Learning Resources
            'tutorials': {
                'keywords': ['tutorial', 'guide', 'how-to', 'walkthrough', 'lesson', 'course'],
                'description': 'Туториалы и обучение'
            },
            'documentation': {
                'keywords': ['docs', 'documentation', 'api-docs', 'readme', 'manual', 'wiki'],
                'description': 'Документация'
            },
            
            # Code Resources
            'code_snippets': {
                'keywords': ['snippet', 'code', 'example', 'gist', 'codepen', 'jsfiddle'],
                'description': 'Примеры кода'
            },
            'templates': {
                'keywords': ['template', 'boilerplate', 'starter', 'scaffold', 'theme'],
                'description': 'Шаблоны и заготовки'
            },
            'libraries': {
                'keywords': ['library', 'package', 'npm', 'cdn', 'plugin', 'module'],
                'description': 'Библиотеки и пакеты'
            },
            
            # General
            'articles': {
                'keywords': ['article', 'blog', 'post', 'news', 'story'],
                'description': 'Статьи и блоги'
            },
            'tools': {
                'keywords': ['tool', 'utility', 'software', 'application', 'extension'],
                'description': 'Инструменты и утилиты'
            },
            'other': {
                'keywords': [],
                'description': 'Прочее'
            }
        }
    
    async def classify_content(self, content: str, urls: list = None) -> dict:
        """Классификация контента с улучшенной обработкой."""
        try:
            if self.provider == 'groq':
                return await self._classify_with_groq(content, urls)
            else:
                return self._enhanced_fallback_classify(content, urls)
        except Exception as e:
            logger.error(f"Ошибка классификации: {e}")
            return self._enhanced_fallback_classify(content, urls)
    
    async def _classify_with_groq(self, content: str, urls: list = None) -> dict:
        """Классификация с помощью Groq API."""
        try:
            from groq import Groq
            
            client = Groq(api_key=self.ai_config['api_key'])
            
            # Подготовка контента для анализа
            analysis_content = content
            if urls:
                url_info = []
                for url in urls[:3]:  # Ограничиваем до 3 URL
                    url_info.append(f"URL: {url}")
                if url_info:
                    analysis_content += "\n\nURL Analysis:\n" + "\n".join(url_info)
            
            prompt = f"""
Классифицируй следующий контент разработчика в одну из категорий:

Основные категории:
- frontend: HTML, CSS, JavaScript, React, Vue, Angular
- backend: серверная разработка, API, Node.js, Python, PHP
- database: базы данных, SQL, MongoDB, Redis
- build_tools: инструменты сборки, Webpack, Vite
- testing: тестирование, Jest, Cypress
- devops_web: DevOps, Docker, CI/CD
- ui_design: UI/UX дизайн, Figma
- tutorials: туториалы, обучение
- documentation: документация, API docs
- code_snippets: примеры кода
- templates: шаблоны, boilerplate
- libraries: библиотеки, пакеты
- articles: статьи, блоги
- tools: инструменты, утилиты
- other: всё остальное

Контент: {analysis_content[:1500]}

Ответь только JSON в формате:
{{
    "category": "название_категории",
    "subcategory": "подкатегория_если_есть",
    "confidence": 0.85,
    "description": "краткое описание",
    "programming_languages": ["javascript", "python"],
    "technology_stack": ["React", "Node.js"],
    "topics": ["frontend", "web development"]
}}
"""
            
            response = client.chat.completions.create(
                model=self.ai_config['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            return self._validate_result(result)
            
        except Exception as e:
            logger.error(f"Ошибка Groq API: {e}")
            return self._enhanced_fallback_classify(content, urls)
    
    def _enhanced_fallback_classify(self, content: str, urls: list = None) -> dict:
        """Улучшенная fallback классификация."""
        content_lower = content.lower()
        
        # Подсчет совпадений по категориям с весами
        scores = {}
        for category, info in self.categories.items():
            score = 0
            for keyword in info['keywords']:
                if keyword in content_lower:
                    # Вес зависит от специфичности ключевого слова
                    weight = self._get_keyword_weight(keyword)
                    score += weight
            
            if score > 0:
                scores[category] = score
        
        # Определение лучшей категории
        if scores:
            best_category = max(scores.keys(), key=lambda k: scores[k])
            confidence = min(0.9, scores[best_category] / 10)
        else:
            best_category = 'other'
            confidence = 0.5
        
        # Определение подкатегории
        subcategory = self._get_subcategory(content_lower, best_category)
        
        # Извлечение языков программирования
        programming_languages = self._extract_programming_languages(content_lower)
        
        # Извлечение технологий
        technology_stack = self._extract_technologies(content_lower)
        
        # Извлечение тем
        topics = self._extract_topics(content_lower, best_category)
        
        return {
            'category': best_category,
            'subcategory': subcategory,
            'confidence': confidence,
            'description': self.categories[best_category]['description'],
            'programming_languages': programming_languages,
            'technology_stack': technology_stack,
            'topics': topics
        }
    
    def _get_keyword_weight(self, keyword: str) -> float:
        """Получить вес ключевого слова."""
        # Специфичные технологии имеют больший вес
        high_weight_keywords = {
            'react', 'vue', 'angular', 'next.js', 'nuxt', 'gatsby',
            'typescript', 'javascript', 'python', 'node.js',
            'mongodb', 'postgresql', 'redis',
            'webpack', 'vite', 'docker'
        }
        
        if keyword in high_weight_keywords:
            return 3.0
        elif len(keyword) > 6:  # Длинные ключевые слова более специфичны
            return 2.0
        else:
            return 1.0
    
    def _get_subcategory(self, content: str, category: str) -> str:
        """Определить подкатегорию."""
        subcategory_patterns = {
            'frontend': {
                'responsive': ['responsive', 'mobile-first', 'breakpoint'],
                'components': ['component', 'ui-component'],
                'spa': ['spa', 'single-page']
            },
            'react_ecosystem': {
                'hooks': ['hooks', 'usestate', 'useeffect'],
                'redux': ['redux', 'state-management'],
                'nextjs': ['next.js', 'nextjs']
            },
            'backend': {
                'api': ['rest', 'restful', 'api'],
                'microservices': ['microservices', 'microservice'],
                'serverless': ['serverless', 'lambda']
            }
        }
        
        if category in subcategory_patterns:
            for subcat, keywords in subcategory_patterns[category].items():
                if any(keyword in content for keyword in keywords):
                    return subcat
        
        return None
    
    def _extract_programming_languages(self, content: str) -> list:
        """Извлечь языки программирования."""
        languages = {
            'javascript': ['javascript', 'js', 'node'],
            'typescript': ['typescript', 'ts'],
            'python': ['python', 'py', 'django', 'flask'],
            'php': ['php', 'laravel'],
            'java': ['java', 'spring'],
            'csharp': ['c#', 'csharp', '.net'],
            'go': ['golang', ' go '],
            'rust': ['rust'],
            'swift': ['swift'],
            'kotlin': ['kotlin']
        }
        
        found_languages = []
        for lang, keywords in languages.items():
            if any(keyword in content for keyword in keywords):
                found_languages.append(lang)
        
        return found_languages[:3]  # Максимум 3 языка
    
    def _extract_technologies(self, content: str) -> list:
        """Извлечь технологии."""
        technologies = {
            'React': ['react', 'jsx'],
            'Vue.js': ['vue', 'vuejs'],
            'Angular': ['angular'],
            'Node.js': ['node.js', 'nodejs'],
            'Express': ['express'],
            'Django': ['django'],
            'Flask': ['flask'],
            'MongoDB': ['mongodb', 'mongo'],
            'PostgreSQL': ['postgresql', 'postgres'],
            'Redis': ['redis'],
            'Docker': ['docker'],
            'Kubernetes': ['kubernetes', 'k8s'],
            'Webpack': ['webpack'],
            'Vite': ['vite']
        }
        
        found_tech = []
        for tech, keywords in technologies.items():
            if any(keyword in content for keyword in keywords):
                found_tech.append(tech)
        
        return found_tech[:5]  # Максимум 5 технологий
    
    def _extract_topics(self, content: str, category: str) -> list:
        """Извлечь темы."""
        topics = [category]
        
        topic_keywords = {
            'web_development': ['web', 'website', 'webapp'],
            'mobile_development': ['mobile', 'ios', 'android'],
            'api_development': ['api', 'rest', 'graphql'],
            'testing': ['test', 'testing', 'unit'],
            'performance': ['performance', 'optimization'],
            'security': ['security', 'auth', 'authentication']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content for keyword in keywords):
                topics.append(topic)
        
        return list(set(topics))[:5]  # Максимум 5 тем, убираем дубликаты
    
    def _validate_result(self, result: dict) -> dict:
        """Валидация результата классификации."""
        category = result.get('category', 'other')
        if category not in self.categories:
            category = 'other'
        
        validated = {
            'category': category,
            'confidence': max(0.0, min(1.0, result.get('confidence', 0.5))),
            'description': result.get('description', self.categories[category]['description'])
        }
        
        # Опциональные поля
        if result.get('subcategory'):
            validated['subcategory'] = str(result['subcategory'])[:50]
        
        if result.get('programming_languages') and isinstance(result['programming_languages'], list):
            validated['programming_languages'] = result['programming_languages'][:5]
        
        if result.get('technology_stack') and isinstance(result['technology_stack'], list):
            validated['technology_stack'] = result['technology_stack'][:8]
        
        if result.get('topics') and isinstance(result['topics'], list):
            validated['topics'] = result['topics'][:5]
        
        return validated