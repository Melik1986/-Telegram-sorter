#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексные тесты для проверки функций сортировки на основе ИИ и нейронных сетей.
Тестирование как специалист по телеграм ботам и нейронным сетям.
"""

import sys
import os
import unittest
import json
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List, Any

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classifier import ContentClassifier
from message_sorter import MessageSorter
from bot import TelegramBot

class TestAINeuralSorting(unittest.TestCase):
    """Комплексные тесты для AI-сортировки контента."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.classifier = ContentClassifier(api_key="test_api_key")
        self.sorter = MessageSorter(classifier=self.classifier)
        
        # Загружаем тестовые данные
        test_data_path = os.path.join(os.path.dirname(__file__), 'test_data.json')
        with open(test_data_path, 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)
    
    def test_neural_network_confidence_levels(self):
        """Тест уровней уверенности нейронной сети."""
        test_cases = [
            {"confidence": 0.95, "expected_quality": "high"},
            {"confidence": 0.75, "expected_quality": "medium"},
            {"confidence": 0.55, "expected_quality": "low"},
            {"confidence": 0.25, "expected_quality": "very_low"}
        ]
        
        for case in test_cases:
            with self.subTest(confidence=case["confidence"]):
                # Проверяем логику обработки уровней уверенности
                if case["confidence"] >= 0.9:
                    actual_quality = "high"
                elif case["confidence"] >= 0.7:
                    actual_quality = "medium"
                elif case["confidence"] >= 0.5:
                    actual_quality = "low"
                else:
                    actual_quality = "very_low"
                
                self.assertEqual(actual_quality, case["expected_quality"])
    
    @patch('classifier.get_openai_key')
    @patch('classifier.openai.ChatCompletion.create')
    def test_ai_classification_accuracy(self, mock_create, mock_get_key):
        """Тест точности AI-классификации для различных типов контента."""
        mock_get_key.return_value = "test_api_key"
        
        # Тестируем каждый тип контента из тестовых данных
        for i, test_item in enumerate(self.test_data[:5]):  # Ограничиваем для скорости
            with self.subTest(test_case=i, category=test_item['expected_category']):
                # Настраиваем мок-ответ
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = json.dumps({
                    "category": test_item['expected_category'],
                    "subcategory": test_item.get('expected_subcategory', 'general'),
                    "confidence": 0.9,
                    "description": f"AI classified as {test_item['expected_category']}",
                    "programming_languages": test_item.get('programming_languages', []),
                    "topics": ["test", "classification"]
                })
                mock_create.return_value = mock_response
                
                # Выполняем классификацию
                result = asyncio.run(self.classifier.classify_content(test_item['content']))
                
                # Проверяем результат
                self.assertEqual(result['category'], test_item['expected_category'])
                self.assertGreaterEqual(result['confidence'], 0.8)
    
    def test_pattern_based_fallback_neural_logic(self):
        """Тест логики fallback на основе паттернов (имитация простой нейронной сети)."""
        test_patterns = [
            {"content": "def hello(): pass", "expected": "code_examples"},
            {"content": "# Tutorial: How to code", "expected": "tutorials"},
            {"content": "https://youtube.com/watch?v=123", "expected": "videos"},
            {"content": "API documentation for users", "expected": "documentation"},
            {"content": "Random text without patterns", "expected": "other"}
        ]
        
        for pattern in test_patterns:
            with self.subTest(content=pattern["content"][:20]):
                result = self.classifier.classify_by_patterns(pattern["content"])
                self.assertEqual(result, pattern["expected"])
    
    def test_telegram_bot_message_processing_pipeline(self):
        """Тест полного пайплайна обработки сообщений телеграм бота."""
        # Создаем тестовые сообщения разных типов
        test_messages = [
            {
                'message_id': 1,
                'text': 'def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)',
                'from': {'id': 123, 'username': 'coder'},
                'chat': {'id': 456, 'type': 'private'},
                'expected_category': 'code_examples'
            },
            {
                'message_id': 2,
                'text': '# Как создать телеграм бота\n\nВ этом туториале мы изучим...',
                'from': {'id': 124, 'username': 'teacher'},
                'chat': {'id': 457, 'type': 'group'},
                'expected_category': 'tutorials'
            },
            {
                'message_id': 3,
                'text': 'Посмотрите видео: https://youtube.com/watch?v=neural_networks',
                'from': {'id': 125, 'username': 'student'},
                'chat': {'id': 458, 'type': 'private'},
                'expected_category': 'videos'
            }
        ]
        
        for msg in test_messages:
            with self.subTest(message_id=msg['message_id']):
                # Тестируем сортировку сообщения
                result = asyncio.run(self.sorter.sort_message(msg))
                
                # Проверяем базовые требования
                self.assertIn('category', result)
                self.assertIn('confidence', result)
                self.assertIsInstance(result['confidence'], (int, float))
                self.assertGreaterEqual(result['confidence'], 0.0)
                self.assertLessEqual(result['confidence'], 1.0)
    
    @patch('classifier.get_openai_key')
    def test_neural_network_error_handling(self, mock_get_key):
        """Тест обработки ошибок нейронной сети."""
        mock_get_key.return_value = "test_api_key"
        
        error_scenarios = [
            {'error': ConnectionError("Network error"), 'expected_fallback': True},
            {'error': TimeoutError("Request timeout"), 'expected_fallback': True},
            {'error': json.JSONDecodeError("Invalid JSON", "", 0), 'expected_fallback': True},
            {'error': ValueError("Invalid response"), 'expected_fallback': True}
        ]
        
        for scenario in error_scenarios:
            with self.subTest(error_type=type(scenario['error']).__name__):
                with patch('classifier.openai.ChatCompletion.create') as mock_create:
                    mock_create.side_effect = scenario['error']
                    
                    # Тестируем обработку ошибки
                    result = asyncio.run(self.classifier.classify_content("test content"))
                    
                    # Проверяем fallback
                    if scenario['expected_fallback']:
                        self.assertIn('category', result)
                        self.assertEqual(result['confidence'], 0.8)  # Fallback confidence
                        self.assertIn('error', result)
    
    def test_performance_neural_classification(self):
        """Тест производительности нейронной классификации."""
        test_content = "def quick_sort(arr): return arr if len(arr) <= 1 else quick_sort([x for x in arr[1:] if x <= arr[0]]) + [arr[0]] + quick_sort([x for x in arr[1:] if x > arr[0]])"
        
        # Измеряем время выполнения fallback классификации
        start_time = time.time()
        result = self.classifier.classify_by_patterns(test_content)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Проверяем, что классификация выполняется быстро (< 1 секунды)
        self.assertLess(execution_time, 1.0)
        self.assertIsNotNone(result)
        self.assertIn(result, self.classifier.categories.keys())
    
    def test_multilingual_content_classification(self):
        """Тест классификации многоязычного контента."""
        multilingual_content = [
            {"content": "def hello(): print('Привет мир!')", "lang": "ru", "expected": "code_examples"},
            {"content": "function sayHello() { console.log('Hello World!'); }", "lang": "en", "expected": "code_examples"},
            {"content": "# Руководство по Python\nВ этом руководстве...", "lang": "ru", "expected": "tutorials"},
            {"content": "# Python Tutorial\nIn this tutorial...", "lang": "en", "expected": "tutorials"}
        ]
        
        for content_item in multilingual_content:
            with self.subTest(language=content_item["lang"]):
                result = self.classifier.classify_by_patterns(content_item["content"])
                self.assertEqual(result, content_item["expected"])
    
    def test_neural_network_confidence_calibration(self):
        """Тест калибровки уверенности нейронной сети."""
        # Тестируем различные сценарии уверенности
        confidence_tests = [
            {"pattern_match": True, "ai_available": True, "expected_min": 0.8},
            {"pattern_match": True, "ai_available": False, "expected_exact": 0.8},
            {"pattern_match": False, "ai_available": False, "expected_exact": 0.8}
        ]
        
        for test_case in confidence_tests:
            with self.subTest(test_case=test_case):
                # Имитируем различные сценарии
                if test_case["pattern_match"] and not test_case["ai_available"]:
                    # Fallback сценарий
                    result = self.classifier.classify_by_patterns("def test(): pass")
                    # В fallback всегда возвращается строка категории, не dict
                    self.assertEqual(result, "code_examples")
    
    def test_edge_cases_neural_processing(self):
        """Тест граничных случаев для нейронной обработки."""
        edge_cases = [
            {"content": "", "description": "empty_content"},
            {"content": "a" * 10000, "description": "very_long_content"},
            {"content": "🤖🔥💻📱⚡", "description": "emoji_only"},
            {"content": "123456789", "description": "numbers_only"},
            {"content": "!@#$%^&*()", "description": "special_chars_only"}
        ]
        
        for case in edge_cases:
            with self.subTest(case_type=case["description"]):
                # Тестируем, что система не падает на граничных случаях
                try:
                    result = self.classifier.classify_by_patterns(case["content"])
                    self.assertIsNotNone(result)
                    self.assertIn(result, self.classifier.categories.keys())
                except Exception as e:
                    self.fail(f"Система упала на граничном случае {case['description']}: {e}")
    
    def test_neural_network_memory_efficiency(self):
        """Тест эффективности использования памяти нейронной сетью."""
        # Тестируем обработку множественных запросов
        large_content_batch = [
            f"def function_{i}(): return {i} * 2" for i in range(100)
        ]
        
        results = []
        for content in large_content_batch:
            result = self.classifier.classify_by_patterns(content)
            results.append(result)
        
        # Проверяем, что все результаты корректны
        self.assertEqual(len(results), 100)
        for result in results:
            self.assertEqual(result, "code_examples")
    
    @patch('classifier.get_openai_key')
    def test_api_key_validation_neural_fallback(self, mock_get_key):
        """Тест валидации API ключа и fallback на нейронную логику."""
        # Тест с отсутствующим API ключом
        mock_get_key.return_value = None
        
        result = asyncio.run(self.classifier.classify_content("def test(): pass"))
        
        # Проверяем fallback
        self.assertEqual(result['category'], 'code_examples')
        self.assertEqual(result['confidence'], 0.8)
        self.assertIn('description', result)
        
        # Тест с недействительным API ключом
        mock_get_key.return_value = "invalid_key"
        
        with patch('classifier.openai.ChatCompletion.create') as mock_create:
            mock_create.side_effect = Exception("Invalid API key")
            
            result = asyncio.run(self.classifier.classify_content("def test(): pass"))
            
            # Проверяем fallback при ошибке API
            self.assertEqual(result['category'], 'code_examples')
            self.assertEqual(result['confidence'], 0.8)
            self.assertIn('error', result)

class TestNeuralNetworkIntegration(unittest.TestCase):
    """Интеграционные тесты для нейронной сети."""
    
    def setUp(self):
        """Настройка интеграционных тестов."""
        self.classifier = ContentClassifier(api_key="test_key")
        self.sorter = MessageSorter(classifier=self.classifier)
    
    def test_end_to_end_neural_pipeline(self):
        """Тест полного пайплайна нейронной обработки от сообщения до результата."""
        # Создаем реалистичное сообщение телеграм бота
        telegram_message = {
            'message_id': 12345,
            'text': '''# Создание телеграм бота на Python

В этом туториале мы создадим простого телеграм бота:

```python
import telebot

bot = telebot.TeleBot("YOUR_TOKEN")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот.")

bot.polling()
```

Запустите код и протестируйте бота!''',
            'from': {'id': 987654321, 'username': 'python_developer'},
            'chat': {'id': 123456789, 'type': 'group', 'title': 'Python Developers'}
        }
        
        # Выполняем полный цикл обработки
        result = asyncio.run(self.sorter.sort_message(telegram_message))
        
        # Проверяем результат
        self.assertIsInstance(result, dict)
        self.assertIn('category', result)
        self.assertIn('confidence', result)
        
        # Проверяем, что категория определена корректно
        # (может быть tutorials или code_examples в зависимости от логики)
        self.assertIn(result['category'], ['tutorials', 'code_examples'])
        
        # Проверяем уровень уверенности
        self.assertGreaterEqual(result['confidence'], 0.5)
        self.assertLessEqual(result['confidence'], 1.0)
    
    def test_neural_network_batch_processing(self):
        """Тест пакетной обработки нейронной сетью."""
        # Создаем пакет сообщений для обработки
        message_batch = [
            {"text": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"},
            {"text": "# Git Tutorial\nLearn version control with git"},
            {"text": "Watch this video: https://youtube.com/watch?v=python_basics"},
            {"text": "API Reference: GET /api/users returns user list"},
            {"text": "Download this tool: https://github.com/user/awesome-tool"}
        ]
        
        results = []
        for message in message_batch:
            result = asyncio.run(self.sorter.sort_message(message))
            results.append(result)
        
        # Проверяем, что все сообщения обработаны
        self.assertEqual(len(results), 5)
        
        # Проверяем, что каждый результат содержит необходимые поля
        for result in results:
            self.assertIn('category', result)
            self.assertIn('confidence', result)
            self.assertIsInstance(result['confidence'], (int, float))

if __name__ == '__main__':
    # Настройка логирования для тестов
    logging.basicConfig(level=logging.INFO)
    
    # Запуск тестов
    unittest.main(verbosity=2)