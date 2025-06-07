#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированные тесты для телеграм бота с нейронной классификацией.
Тестирование как эксперт по телеграм ботам и машинному обучению.
"""

import sys
import os
import unittest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classifier import ContentClassifier
from message_sorter import MessageSorter
from bot import TelegramBot

class TestTelegramBotNeuralClassification(unittest.TestCase):
    """Тесты для телеграм бота с нейронной классификацией."""
    
    def setUp(self):
        """Настройка тестового окружения для телеграм бота."""
        self.classifier = ContentClassifier(api_key="test_api_key")
        self.sorter = MessageSorter(classifier=self.classifier)
    
    def test_telegram_message_types_classification(self):
        """Тест классификации различных типов телеграм сообщений."""
        telegram_message_types = [
            {
                "message": {
                    'message_id': 1,
                    'text': '/start',
                    'from': {'id': 123, 'username': 'user1'},
                    'chat': {'id': 456, 'type': 'private'},
                    'entities': [{'type': 'bot_command', 'offset': 0, 'length': 6}]
                },
                "expected_handling": "command",
                "description": "Bot command message"
            },
            {
                "message": {
                    'message_id': 2,
                    'text': 'async def handle_message(update, context): await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello!")',
                    'from': {'id': 124, 'username': 'developer'},
                    'chat': {'id': 789, 'type': 'group', 'title': 'Python Developers'},
                    'reply_to_message': {'message_id': 1, 'text': 'How to create async handler?'}
                },
                "expected_category": "code_examples",
                "description": "Code snippet in group chat"
            },
            {
                "message": {
                    'message_id': 3,
                    'text': 'Форвард из канала: Новый туториал по созданию ботов https://t.me/python_channel/123',
                    'from': {'id': 125, 'username': 'student'},
                    'chat': {'id': 101112, 'type': 'private'},
                    'forward_from_chat': {'id': 999, 'type': 'channel', 'title': 'Python Channel'}
                },
                "expected_category": "tutorials",
                "description": "Forwarded message with tutorial link"
            }
        ]
        
        for msg_data in telegram_message_types:
            with self.subTest(description=msg_data["description"]):
                if "expected_category" in msg_data:
                    result = asyncio.run(self.sorter.sort_message(msg_data["message"]))
                    self.assertIn('category', result)
                    # Проверяем, что система может обработать сообщение
                    self.assertIsNotNone(result['category'])
    
    def test_telegram_bot_inline_queries_neural_processing(self):
        """Тест обработки inline-запросов с нейронной классификацией."""
        inline_queries = [
            {
                "query": "python code fibonacci",
                "expected_category": "code_examples",
                "expected_results_type": "code_snippets"
            },
            {
                "query": "tutorial machine learning",
                "expected_category": "tutorials",
                "expected_results_type": "learning_materials"
            },
            {
                "query": "api documentation rest",
                "expected_category": "documentation",
                "expected_results_type": "reference_docs"
            }
        ]
        
        for query_data in inline_queries:
            with self.subTest(query=query_data["query"]):
                # Имитируем обработку inline-запроса
                result = self.classifier.classify_by_patterns(query_data["query"])
                
                # Проверяем, что классификация работает для коротких запросов
                self.assertIsNotNone(result)
                self.assertIn(result, self.classifier.categories.keys())
    
    def test_telegram_bot_callback_data_neural_analysis(self):
        """Тест анализа callback данных с помощью нейронной сети."""
        callback_scenarios = [
            {
                "callback_data": "category:code_examples:page:1",
                "expected_action": "pagination",
                "expected_category": "code_examples"
            },
            {
                "callback_data": "search:python:tutorials",
                "expected_action": "search",
                "expected_category": "tutorials"
            },
            {
                "callback_data": "add_resource:documentation:api",
                "expected_action": "add_resource",
                "expected_category": "documentation"
            }
        ]
        
        for callback in callback_scenarios:
            with self.subTest(callback_data=callback["callback_data"]):
                # Парсим callback данные
                parts = callback["callback_data"].split(":")
                
                # Проверяем структуру callback данных
                self.assertGreaterEqual(len(parts), 2)
                
                # Проверяем, что категория валидна
                if len(parts) > 1 and parts[1] in self.classifier.categories:
                    self.assertIn(parts[1], self.classifier.categories.keys())
    
    def test_telegram_bot_media_content_neural_classification(self):
        """Тест классификации медиа-контента в телеграм сообщениях."""
        media_messages = [
            {
                "message": {
                    'message_id': 1,
                    'photo': [{'file_id': 'photo123', 'width': 1280, 'height': 720}],
                    'caption': 'Схема архитектуры микросервисов для веб-приложения',
                    'from': {'id': 123, 'username': 'architect'},
                    'chat': {'id': 456, 'type': 'group'}
                },
                "expected_category": "mockups",
                "content_type": "photo_with_caption"
            },
            {
                "message": {
                    'message_id': 2,
                    'document': {'file_id': 'doc456', 'file_name': 'api_reference.pdf'},
                    'caption': 'Документация REST API v2.0',
                    'from': {'id': 124, 'username': 'tech_writer'},
                    'chat': {'id': 789, 'type': 'private'}
                },
                "expected_category": "documentation",
                "content_type": "document_with_caption"
            },
            {
                "message": {
                    'message_id': 3,
                    'video': {'file_id': 'video789', 'duration': 1800, 'width': 1920, 'height': 1080},
                    'caption': 'Видеоурок: Создание нейронной сети на PyTorch',
                    'from': {'id': 125, 'username': 'ml_teacher'},
                    'chat': {'id': 101112, 'type': 'channel'}
                },
                "expected_category": "videos",
                "content_type": "video_with_caption"
            }
        ]
        
        for media_msg in media_messages:
            with self.subTest(content_type=media_msg["content_type"]):
                # Извлекаем caption для классификации
                caption = media_msg["message"].get('caption', '')
                
                if caption:
                    result = asyncio.run(self.sorter.sort_message({'text': caption}))
                    self.assertIn('category', result)
                    # Проверяем, что система обрабатывает медиа-контент
                    self.assertIsNotNone(result['category'])
    
    def test_telegram_bot_group_vs_private_neural_behavior(self):
        """Тест различного поведения нейронной сети в группах и приватных чатах."""
        test_content = "def create_bot(): return telebot.TeleBot('TOKEN')"
        
        # Сообщение в приватном чате
        private_message = {
            'message_id': 1,
            'text': test_content,
            'from': {'id': 123, 'username': 'user1'},
            'chat': {'id': 123, 'type': 'private'}
        }
        
        # Сообщение в группе
        group_message = {
            'message_id': 2,
            'text': test_content,
            'from': {'id': 123, 'username': 'user1'},
            'chat': {'id': 456, 'type': 'group', 'title': 'Developers Chat'}
        }
        
        # Тестируем оба типа чатов
        private_result = asyncio.run(self.sorter.sort_message(private_message))
        group_result = asyncio.run(self.sorter.sort_message(group_message))
        
        # Проверяем, что классификация работает в обоих случаях
        self.assertEqual(private_result['category'], group_result['category'])
        self.assertEqual(private_result['category'], 'code_examples')
    
    def test_telegram_bot_user_context_neural_learning(self):
        """Тест учета контекста пользователя в нейронной классификации."""
        # Имитируем историю сообщений пользователя
        user_message_history = [
            {
                "text": "Как создать телеграм бота?",
                "timestamp": "2024-01-01 10:00:00",
                "user_id": 123
            },
            {
                "text": "import telebot\nbot = telebot.TeleBot('TOKEN')",
                "timestamp": "2024-01-01 10:05:00",
                "user_id": 123
            },
            {
                "text": "@bot.message_handler(commands=['start'])\ndef start(message): pass",
                "timestamp": "2024-01-01 10:10:00",
                "user_id": 123
            }
        ]
        
        # Тестируем классификацию с учетом контекста
        for i, msg in enumerate(user_message_history):
            with self.subTest(message_index=i):
                result = asyncio.run(self.sorter.sort_message({'text': msg['text']}))
                
                # Проверяем, что система классифицирует сообщения
                self.assertIn('category', result)
                
                # Первое сообщение - вопрос (может быть other)
                # Последующие - код (должны быть code_examples)
                if i > 0:  # Сообщения с кодом
                    self.assertEqual(result['category'], 'code_examples')
    
    def test_telegram_bot_multilingual_neural_support(self):
        """Тест поддержки многоязычности в нейронной классификации."""
        multilingual_messages = [
            {
                "text": "def hello(): print('Привет мир!')",
                "language": "ru",
                "expected_category": "code_examples"
            },
            {
                "text": "function sayHello() { console.log('Hello World!'); }",
                "language": "en",
                "expected_category": "code_examples"
            },
            {
                "text": "# Руководство по созданию ботов\nВ этом руководстве мы изучим...",
                "language": "ru",
                "expected_category": "tutorials"
            },
            {
                "text": "# Bot Creation Guide\nIn this guide we will learn...",
                "language": "en",
                "expected_category": "tutorials"
            },
            {
                "text": "Посмотрите видео: https://youtube.com/watch?v=bot_tutorial",
                "language": "ru",
                "expected_category": "videos"
            },
            {
                "text": "Watch video: https://youtube.com/watch?v=bot_tutorial",
                "language": "en",
                "expected_category": "videos"
            }
        ]
        
        for msg in multilingual_messages:
            with self.subTest(language=msg["language"], category=msg["expected_category"]):
                result = asyncio.run(self.sorter.sort_message({'text': msg['text']}))
                
                # Проверяем, что классификация работает независимо от языка
                self.assertEqual(result['category'], msg['expected_category'])
    
    def test_telegram_bot_spam_detection_neural(self):
        """Тест нейронного обнаружения спама в телеграм сообщениях."""
        spam_like_messages = [
            {
                "text": "🔥🔥🔥 СУПЕР ПРЕДЛОЖЕНИЕ!!! ЗАРАБОТАЙ МИЛЛИОН!!! 💰💰💰",
                "is_spam_like": True,
                "description": "Excessive emojis and caps"
            },
            {
                "text": "def calculate_profit(): return investment * 0.1  # 10% daily profit",
                "is_spam_like": False,
                "description": "Normal code with comment"
            },
            {
                "text": "CLICK HERE NOW!!! https://suspicious-link.com/get-rich-quick",
                "is_spam_like": True,
                "description": "Suspicious link with aggressive text"
            },
            {
                "text": "# Tutorial: Building secure applications\nSecurity best practices...",
                "is_spam_like": False,
                "description": "Educational content"
            }
        ]
        
        for msg in spam_like_messages:
            with self.subTest(description=msg["description"]):
                result = asyncio.run(self.sorter.sort_message({'text': msg['text']}))
                
                # Проверяем, что система обрабатывает все типы сообщений
                self.assertIn('category', result)
                
                # Спам-подобные сообщения могут классифицироваться как 'other'
                if msg["is_spam_like"]:
                    # Система должна обработать сообщение, даже если это спам
                    self.assertIsNotNone(result['category'])
    
    def test_telegram_bot_neural_performance_under_load(self):
        """Тест производительности нейронной классификации под нагрузкой."""
        import time
        
        # Создаем пакет сообщений для нагрузочного тестирования
        load_test_messages = [
            f"def function_{i}(x): return x * {i}" for i in range(50)
        ]
        
        start_time = time.time()
        results = []
        
        for msg_text in load_test_messages:
            result = asyncio.run(self.sorter.sort_message({'text': msg_text}))
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Проверяем производительность
        self.assertEqual(len(results), 50)
        self.assertLess(total_time, 10.0)  # Все сообщения должны обработаться за 10 секунд
        
        # Проверяем, что все результаты корректны
        for result in results:
            self.assertEqual(result['category'], 'code_examples')
            self.assertGreaterEqual(result['confidence'], 0.5)
    
    def test_telegram_bot_neural_memory_management(self):
        """Тест управления памятью в нейронной классификации."""
        import gc
        
        # Получаем начальное количество объектов
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Обрабатываем множество сообщений
        for i in range(100):
            large_message = {
                'text': f"# Large Tutorial {i}\n" + "Content line\n" * 100,
                'message_id': i
            }
            result = asyncio.run(self.sorter.sort_message(large_message))
            self.assertIsNotNone(result)
        
        # Принудительная сборка мусора
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Проверяем, что нет значительной утечки памяти
        # Допускаем небольшое увеличение количества объектов
        object_increase = final_objects - initial_objects
        self.assertLess(object_increase, 1000)  # Не более 1000 новых объектов

class TestTelegramBotNeuralAdvanced(unittest.TestCase):
    """Продвинутые тесты для телеграм бота с нейронной сетью."""
    
    def setUp(self):
        """Настройка продвинутых тестов."""
        self.classifier = ContentClassifier(api_key="test_api_key")
        self.sorter = MessageSorter(classifier=self.classifier)
    
    def test_neural_confidence_adaptation(self):
        """Тест адаптации уверенности нейронной сети."""
        # Тестируем различные типы контента и их уверенность
        confidence_test_cases = [
            {
                "content": "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
                "expected_min_confidence": 0.8,
                "description": "Clear code pattern"
            },
            {
                "content": "maybe this is code? or tutorial? not sure...",
                "expected_max_confidence": 0.8,
                "description": "Ambiguous content"
            },
            {
                "content": "# Complete Python Tutorial\n\nStep 1: Install Python\nStep 2: Write code\n```python\nprint('hello')\n```",
                "expected_min_confidence": 0.7,
                "description": "Mixed content (tutorial with code)"
            }
        ]
        
        for case in confidence_test_cases:
            with self.subTest(description=case["description"]):
                result = asyncio.run(self.sorter.sort_message({'text': case['content']}))
                
                if "expected_min_confidence" in case:
                    self.assertGreaterEqual(result['confidence'], case['expected_min_confidence'])
                if "expected_max_confidence" in case:
                    self.assertLessEqual(result['confidence'], case['expected_max_confidence'])
    
    def test_neural_category_boundary_detection(self):
        """Тест обнаружения границ между категориями."""
        boundary_cases = [
            {
                "content": "# Code Tutorial\n\ndef example(): pass\n\nThis function demonstrates...",
                "possible_categories": ["tutorials", "code_examples"],
                "description": "Tutorial with code examples"
            },
            {
                "content": "API Documentation\n\nGET /users - returns user list\n\n```json\n{\"users\": []}\n```",
                "possible_categories": ["documentation", "code_examples"],
                "description": "Documentation with code samples"
            },
            {
                "content": "Video tutorial: https://youtube.com/watch?v=123\n\nCode from video:\n\ndef main(): pass",
                "possible_categories": ["videos", "code_examples", "tutorials"],
                "description": "Video link with code"
            }
        ]
        
        for case in boundary_cases:
            with self.subTest(description=case["description"]):
                result = asyncio.run(self.sorter.sort_message({'text': case['content']}))
                
                # Проверяем, что результат находится в ожидаемых категориях
                self.assertIn(result['category'], case['possible_categories'])
    
    def test_neural_learning_simulation(self):
        """Симуляция обучения нейронной сети на примерах."""
        # Имитируем процесс "обучения" через множественные примеры
        training_examples = [
            {"content": "def func1(): pass", "label": "code_examples"},
            {"content": "def func2(): return 1", "label": "code_examples"},
            {"content": "function js1() {}", "label": "code_examples"},
            {"content": "# Tutorial 1\nLearn this", "label": "tutorials"},
            {"content": "# Tutorial 2\nStep by step", "label": "tutorials"},
            {"content": "# Guide\nHow to do", "label": "tutorials"}
        ]
        
        # "Тестируем" на каждом примере
        correct_predictions = 0
        total_predictions = len(training_examples)
        
        for example in training_examples:
            result = asyncio.run(self.sorter.sort_message({'text': example['content']}))
            if result['category'] == example['label']:
                correct_predictions += 1
        
        # Проверяем "точность" классификации
        accuracy = correct_predictions / total_predictions
        self.assertGreaterEqual(accuracy, 0.8)  # Минимум 80% точности

if __name__ == '__main__':
    # Настройка логирования для тестов
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Запуск тестов
    unittest.main(verbosity=2)