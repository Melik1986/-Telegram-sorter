import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_sorter import MessageSorter
from classifier import ContentClassifier

class TestMessageSorter(unittest.TestCase):
    
    def setUp(self):
        # Создаем мок-объект классификатора
        self.mock_classifier = MagicMock(spec=ContentClassifier)
        # Настраиваем мок-метод classify_content, чтобы он возвращал Future объект
        # для совместимости с асинхронным методом
        self.mock_classifier.classify_content = MagicMock()
        # Создаем экземпляр сортировщика сообщений с мок-классификатором
        self.sorter = MessageSorter(classifier=self.mock_classifier)
    
    def test_sort_message_code_examples(self):
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'def hello_world(): print("Hello, World!")',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        async def run_test():
            # Настраиваем мок-классификатор для возврата категории code_examples
            classification_result = {
                'category': 'code_examples',
                'subcategory': 'python_scripts',
                'confidence': 0.95,
                'description': 'Python script for data processing',
                'programming_languages': ['python'],
                'topics': ['data processing', 'pandas', 'automation']
            }
            # Настраиваем мок-метод, чтобы он возвращал Future объект с результатом
            future = asyncio.Future()
            future.set_result(classification_result)
            self.mock_classifier.classify_content.return_value = future
            
            # Вызываем метод сортировки
            result = await self.sorter.sort_message(message)
            return result
        
        # Запускаем асинхронный тест
        result = asyncio.run(run_test())
        
        # Проверяем, что классификатор был вызван с правильным текстом
        self.mock_classifier.classify_content.assert_called_once_with(message['text'])
        
        # Проверяем результат сортировки
        self.assertEqual(result['category'], 'code_examples')
        self.assertEqual(result['subcategory'], 'python_scripts')
        self.assertEqual(result['confidence'], 0.95)
        self.assertEqual(result['programming_languages'], ['python'])
    
    def test_sort_message_tutorials(self):
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': '# How to Use Pandas for Data Analysis\n\nIn this tutorial...',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        async def run_test():
            # Настраиваем мок-классификатор для возврата категории tutorials
            classification_result = {
                'category': 'tutorials',
                'subcategory': 'python_tutorial',
                'confidence': 0.9,
                'description': 'Tutorial on using pandas for data analysis',
                'programming_languages': ['python'],
                'topics': ['pandas', 'data analysis', 'tutorial']
            }
            # Настраиваем мок-метод, чтобы он возвращал Future объект с результатом
            future = asyncio.Future()
            future.set_result(classification_result)
            self.mock_classifier.classify_content.return_value = future
            
            # Вызываем метод сортировки
            result = await self.sorter.sort_message(message)
            return result
        
        # Запускаем асинхронный тест
        result = asyncio.run(run_test())
        
        # Проверяем результат сортировки
        self.assertEqual(result['category'], 'tutorials')
        self.assertEqual(result['subcategory'], 'python_tutorial')
        self.assertEqual(result['confidence'], 0.9)
    
    def test_sort_message_videos(self):
        # Создаем тестовое сообщение с URL видео
        message = {
            'message_id': 123,
            'text': 'Check out this tutorial video: https://youtube.com/watch?v=12345',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        async def run_test():
            # Настраиваем мок-классификатор для возврата категории videos
            classification_result = {
                'category': 'videos',
                'subcategory': 'tutorial_video',
                'confidence': 0.85,
                'description': 'Video tutorial on Python programming',
                'topics': ['python', 'programming', 'tutorial']
            }
            # Настраиваем мок-метод, чтобы он возвращал Future объект с результатом
            future = asyncio.Future()
            future.set_result(classification_result)
            self.mock_classifier.classify_content.return_value = future
            
            # Вызываем метод сортировки
            result = await self.sorter.sort_message(message)
            return result
        
        # Запускаем асинхронный тест
        result = asyncio.run(run_test())
        
        # Проверяем результат сортировки
        self.assertEqual(result['category'], 'videos')
        self.assertEqual(result['subcategory'], 'tutorial_video')
        self.assertEqual(result['confidence'], 0.85)
    
    def test_sort_message_documentation(self):
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'Python Documentation: The official Python API reference documentation',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        async def run_test():
            # Настраиваем мок-классификатор для возврата категории documentation
            classification_result = {
                'category': 'documentation',
                'subcategory': 'api_reference',
                'confidence': 0.92,
                'description': 'Python API documentation',
                'programming_languages': ['python'],
                'topics': ['api', 'documentation', 'reference']
            }
            # Настраиваем мок-метод, чтобы он возвращал Future объект с результатом
            future = asyncio.Future()
            future.set_result(classification_result)
            self.mock_classifier.classify_content.return_value = future
            
            # Вызываем метод сортировки
            result = await self.sorter.sort_message(message)
            return result
        
        # Запускаем асинхронный тест
        result = asyncio.run(run_test())
        
        # Проверяем результат сортировки
        self.assertEqual(result['category'], 'documentation')
        self.assertEqual(result['subcategory'], 'api_reference')
        self.assertEqual(result['confidence'], 0.92)

if __name__ == '__main__':
    unittest.main()