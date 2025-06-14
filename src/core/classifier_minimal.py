"""
Минимальная версия классификатора с поддержкой Groq API и fallback.
"""

import asyncio
import json
import logging
import re
from src.core.config_minimal import get_ai_config

logger = logging.getLogger(__name__)

class ContentClassifier:
    def __init__(self):
        """Инициализация минимального классификатора."""
        self.ai_config = get_ai_config()
        self.provider = self.ai_config['provider']
        
        if self.provider == 'fallback':
            logger.warning("Используется fallback классификация без AI")
        else:
            logger.info(f"AI классификатор инициализирован: {self.provider}")
        
        # Основные категории для веб-разработки
        self.categories = {
            'frontend': {
                'keywords': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'frontend'],
                'description': 'Frontend разработка'
            },
            'backend': {
                'keywords': ['backend', 'server', 'api', 'nodejs', 'python', 'php'],
                'description': 'Backend разработка'
            },
            'database': {
                'keywords': ['database', 'sql', 'mysql', 'postgresql', 'mongodb'],
                'description': 'Базы данных'
            },
            'tools': {
                'keywords': ['webpack', 'vite', 'docker', 'git', 'npm', 'yarn'],
                'description': 'Инструменты разработки'
            },
            'documentation': {
                'keywords': ['docs', 'readme', 'tutorial', 'guide', 'manual'],
                'description': 'Документация'
            },
            'code': {
                'keywords': ['function', 'class', 'import', 'export', 'const', 'var'],
                'description': 'Код и примеры'
            },
            'other': {
                'keywords': [],
                'description': 'Прочее'
            }
        }
    
    async def classify_content(self, content: str, urls: list = None) -> dict:
        """Классификация контента."""
        try:
            if self.provider == 'groq':
                return await self._classify_with_groq(content)
            else:
                return self._fallback_classify(content)
        except Exception as e:
            logger.error(f"Ошибка классификации: {e}")
            return self._fallback_classify(content)
    
    async def _classify_with_groq(self, content: str) -> dict:
        """Классификация с помощью Groq API."""
        try:
            from groq import Groq
            
            client = Groq(api_key=self.ai_config['api_key'])
            
            prompt = f"""
Классифицируй следующий контент в одну из категорий:
- frontend: HTML, CSS, JavaScript, React, Vue, Angular
- backend: серверная разработка, API, Node.js, Python, PHP
- database: базы данных, SQL, MongoDB
- tools: инструменты разработки, Docker, Git
- documentation: документация, туториалы, руководства
- code: примеры кода, функции, классы
- other: всё остальное

Контент: {content[:1000]}

Ответь только JSON в формате:
{{"category": "название_категории", "confidence": 0.8, "description": "краткое описание"}}
"""
            
            response = client.chat.completions.create(
                model=self.ai_config['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            result = json.loads(response.choices[0].message.content)
            return self._validate_result(result)
            
        except Exception as e:
            logger.error(f"Ошибка Groq API: {e}")
            return self._fallback_classify(content)
    
    def _fallback_classify(self, content: str) -> dict:
        """Fallback классификация по ключевым словам."""
        content_lower = content.lower()
        
        # Подсчет совпадений по категориям
        scores = {}
        for category, info in self.categories.items():
            score = sum(1 for keyword in info['keywords'] 
                       if keyword in content_lower)
            if score > 0:
                scores[category] = score
        
        if scores:
            best_category = max(scores.keys(), key=lambda k: scores[k])
            confidence = min(0.8, scores[best_category] / 5)
        else:
            best_category = 'other'
            confidence = 0.5
        
        return {
            'category': best_category,
            'confidence': confidence,
            'description': self.categories[best_category]['description']
        }
    
    def _validate_result(self, result: dict) -> dict:
        """Валидация результата классификации."""
        category = result.get('category', 'other')
        if category not in self.categories:
            category = 'other'
        
        return {
            'category': category,
            'confidence': max(0.0, min(1.0, result.get('confidence', 0.5))),
            'description': result.get('description', self.categories[category]['description'])
        }