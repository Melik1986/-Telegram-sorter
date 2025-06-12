import sys
import os
import unittest
import json
import asyncio
from unittest.mock import patch, MagicMock

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.classifier import ContentClassifier

class TestContentClassifier(unittest.TestCase):
    
    def setUp(self):
        # Классификатор будет создаваться в каждом тесте после применения патчей
        pass
    
    @patch('src.core.classifier.get_ai_config')
    @patch('src.core.classifier.ContentClassifier._call_groq_api')
    def test_classify_content_code_example(self, mock_groq_api, mock_get_config):
        # Настраиваем мок конфигурации
        mock_get_config.return_value = {'provider': 'groq', 'api_key': 'test_api_key', 'model': 'llama3-8b-8192'}
        
        # Подготавливаем мок-ответ от Groq API
        mock_groq_api.return_value = json.dumps({
            "category": "code_examples",
            "subcategory": "python_scripts",
            "confidence": 0.95,
            "description": "Python script for data processing",
            "programming_languages": ["python"],
            "topics": ["data processing", "pandas", "automation"]
        })
        
        # Создаем классификатор после применения патчей
        classifier = ContentClassifier()
        
        # Тестируем классификацию кода
        content = """def process_data(data):
    import pandas as pd
    df = pd.DataFrame(data)
    return df.describe()
"""
        # Используем asyncio для запуска асинхронного метода
        result = asyncio.run(classifier.classify_content(content))
        
        # Проверяем результат
        self.assertEqual(result['category'], 'code_examples')
        self.assertEqual(result['subcategory'], 'python_scripts')
        self.assertEqual(result['confidence'], 0.95)
        self.assertEqual(len(result['programming_languages']), 1)
        self.assertEqual(result['programming_languages'][0], 'python')
    
    @patch('src.core.classifier.get_ai_config')
    @patch('src.core.classifier.ContentClassifier._call_groq_api')
    def test_classify_content_tutorial(self, mock_groq_api, mock_get_config):
        # Настраиваем мок конфигурации
        mock_get_config.return_value = {'provider': 'groq', 'api_key': 'test_api_key', 'model': 'llama3-8b-8192'}
        
        # Подготавливаем мок-ответ от Groq API
        mock_groq_api.return_value = json.dumps({
            "category": "tutorials",
            "subcategory": "python_tutorial",
            "confidence": 0.9,
            "description": "Tutorial on using pandas for data analysis",
            "programming_languages": ["python"],
            "topics": ["pandas", "data analysis", "tutorial"]
        })
        
        # Создаем классификатор после применения патчей
        classifier = ContentClassifier()
        
        # Тестируем классификацию туториала
        content = """# How to Use Pandas for Data Analysis

In this tutorial, we'll learn how to use pandas for data analysis in Python.

## Step 1: Install pandas
```
pip install pandas
```
"""
        # Используем asyncio для запуска асинхронного метода
        result = asyncio.run(classifier.classify_content(content))
        
        # Проверяем результат
        self.assertEqual(result['category'], 'tutorials')
        self.assertEqual(result['subcategory'], 'python_tutorial')
        self.assertEqual(result['confidence'], 0.9)
    
    def test_classify_by_patterns_code(self):
        # Тестируем классификацию по паттернам для кода
        classifier = ContentClassifier()
        content = """def hello_world():
    print("Hello, World!")
"""
        result = classifier.classify_by_patterns(content)
        self.assertEqual(result, 'code_examples')
        
    def test_classify_by_patterns_video(self):
        # Тестируем классификацию по паттернам для видео
        classifier = ContentClassifier()
        content = "Check out this amazing tutorial: https://youtube.com/watch?v=abc123"
        result = classifier.classify_by_patterns(content)
        self.assertEqual(result, 'videos')
        
    def test_classify_by_patterns_tutorial(self):
        # Тестируем классификацию по паттернам для туториала
        classifier = ContentClassifier()
        content = "# Tutorial: How to learn Python\n\nStep 1: Install Python"
        result = classifier.classify_by_patterns(content)
        self.assertEqual(result, 'tutorials')
        
    def test_classify_by_patterns_documentation(self):
        # Тестируем классификацию по паттернам для документации
        classifier = ContentClassifier()
        content = "## API Reference\n\nThis function returns the user data"
        result = classifier.classify_by_patterns(content)
        self.assertEqual(result, 'documentation')

if __name__ == '__main__':
    unittest.main()