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
        # Создаем экземпляр классификатора для тестов
        self.classifier = ContentClassifier()
    
    @patch('classifier.get_openai_key')
    @patch('classifier.openai.ChatCompletion.create')
    def test_classify_content_code_example(self, mock_create, mock_get_key):
        mock_get_key.return_value = "test_api_key"
        # Подготавливаем мок-ответ от OpenAI API
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "code_examples",
            "subcategory": "python_scripts",
            "confidence": 0.95,
            "description": "Python script for data processing",
            "programming_languages": ["python"],
            "topics": ["data processing", "pandas", "automation"]
        })
        mock_create.return_value = mock_response
        
        # Тестируем классификацию кода
        content = """def process_data(data):
    import pandas as pd
    df = pd.DataFrame(data)
    return df.describe()
"""
        # Используем asyncio для запуска асинхронного метода
        result = asyncio.run(self.classifier.classify_content(content))
        
        # Проверяем результат
        self.assertEqual(result['category'], 'code_examples')
        self.assertEqual(result['subcategory'], 'python_scripts')
        self.assertEqual(result['confidence'], 0.95)
        self.assertEqual(len(result['programming_languages']), 1)
        self.assertEqual(result['programming_languages'][0], 'python')
    
    @patch('classifier.get_openai_key')
    @patch('classifier.openai.ChatCompletion.create')
    def test_classify_content_tutorial(self, mock_create, mock_get_key):
        mock_get_key.return_value = "test_api_key"
        # Подготавливаем мок-ответ от OpenAI API
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "tutorials",
            "subcategory": "python_tutorial",
            "confidence": 0.9,
            "description": "Tutorial on using pandas for data analysis",
            "programming_languages": ["python"],
            "topics": ["pandas", "data analysis", "tutorial"]
        })
        mock_create.return_value = mock_response
        
        # Тестируем классификацию туториала
        content = """# How to Use Pandas for Data Analysis

In this tutorial, we'll learn how to use pandas for data analysis in Python.

## Step 1: Install pandas
```
pip install pandas
```
"""
        # Используем asyncio для запуска асинхронного метода
        result = asyncio.run(self.classifier.classify_content(content))
        
        # Проверяем результат
        self.assertEqual(result['category'], 'tutorials')
        self.assertEqual(result['subcategory'], 'python_tutorial')
        self.assertEqual(result['confidence'], 0.9)
    
    def test_classify_by_patterns_code(self):
        # Тестируем классификацию по паттернам для кода
        content = "def hello_world(): print('Hello, World!')"
        result = self.classifier.classify_by_patterns(content)
        self.assertEqual(result, 'code_examples')
    
    def test_classify_by_patterns_video(self):
        # Тестируем классификацию по паттернам для видео
        content = "Check out this tutorial video on YouTube: https://youtube.com/watch?v=12345"
        result = self.classifier.classify_by_patterns(content)
        self.assertEqual(result, 'videos')
    
    def test_classify_by_patterns_tutorial(self):
        # Тестируем классификацию по паттернам для туториала
        # Используем текст, который не содержит упоминаний языков программирования
        content = "Step by step guide: How to learn programming concepts"
        result = self.classifier.classify_by_patterns(content)
        self.assertEqual(result, 'tutorials')
    
    def test_classify_by_patterns_documentation(self):
        # Тестируем классификацию по паттернам для документации
        # Используем текст, который не содержит упоминаний языков программирования
        content = "Official Documentation: The complete API reference documentation"
        result = self.classifier.classify_by_patterns(content)
        self.assertEqual(result, 'documentation')

if __name__ == '__main__':
    unittest.main()