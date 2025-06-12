import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.classifier import ContentClassifier
from src.handlers.message_sorter import MessageSorter

class TestErrorHandling(unittest.TestCase):
    
    def setUp(self):
        # Инициализация будет происходить в каждом тесте после применения патчей
        pass
    
    @patch('src.core.classifier.ContentClassifier._call_groq_api')
    @patch('src.core.classifier.get_ai_config')
    def test_openai_api_error(self, mock_get_key, mock_groq_api):
        # Настраиваем мок для возврата валидного ключа
        mock_get_key.return_value = {'provider': 'groq', 'api_key': 'test_api_key', 'model': 'llama3-8b-8192'}
        # Настраиваем мок для имитации ошибки API
        mock_groq_api.side_effect = Exception("OpenAI API Error")
        
        # Создаем экземпляр классификатора после применения патчей
        classifier = ContentClassifier()
        sorter = MessageSorter(classifier=classifier)
        
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'def hello_world(): print("Hello, World!")',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки и проверяем, что он корректно обрабатывает ошибку
        result = asyncio.run(sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию, определенную по паттернам
        self.assertIn('category', result)
        # Проверяем, что была добавлена информация об ошибке
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'OpenAI API Error')
    
    @patch('src.core.classifier.ContentClassifier._call_groq_api')
    @patch('src.core.classifier.get_ai_config')
    def test_invalid_api_response(self, mock_get_key, mock_groq_api):
        # Настраиваем мок для возврата валидного ключа
        mock_get_key.return_value = {'provider': 'groq', 'api_key': 'test_api_key', 'model': 'llama3-8b-8192'}
        # Настраиваем мок для возврата невалидного JSON
        mock_groq_api.return_value = 'Invalid JSON response'
        
        # Создаем экземпляр классификатора после применения патчей
        classifier = ContentClassifier()
        sorter = MessageSorter(classifier=classifier)
        
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'def hello_world(): print("Hello, World!")',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию, определенную по паттернам
        self.assertIn('category', result)
        # Проверяем, что была добавлена информация об ошибке
        self.assertIn('error', result)
    
    def test_empty_message(self):
        # Создаем экземпляр классификатора и сортировщика
        classifier = ContentClassifier()
        sorter = MessageSorter(classifier=classifier)
        
        # Создаем пустое сообщение
        message = {
            'message_id': 123,
            'text': '',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию 'other' для пустого сообщения
        self.assertEqual(result['category'], 'other')
    
    def test_message_without_text(self):
        # Создаем экземпляр классификатора и сортировщика
        classifier = ContentClassifier()
        sorter = MessageSorter(classifier=classifier)
        
        # Создаем сообщение без текста
        message = {
            'message_id': 123,
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию 'other' для сообщения без текста
        self.assertEqual(result['category'], 'other')
    
    @patch('src.core.classifier.ContentClassifier._call_groq_api')
    @patch('src.core.classifier.get_ai_config')
    def test_low_confidence_classification(self, mock_get_key, mock_groq_api):
        # Настраиваем мок для возврата валидного ключа
        mock_get_key.return_value = {'provider': 'groq', 'api_key': 'test_api_key', 'model': 'llama3-8b-8192'}
        # Настраиваем мок для возврата классификации с низкой уверенностью
        mock_groq_api.return_value = '{"category": "code_examples", "confidence": 0.3, "subcategory": "python_scripts"}'
        
        # Создаем экземпляр классификатора после применения патчей
        classifier = ContentClassifier()
        sorter = MessageSorter(classifier=classifier)
        
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'def hello_world(): print("Hello, World!")',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию (может быть из паттернов или API)
        self.assertIn('category', result)
        # Проверяем, что есть информация о низкой уверенности или ошибке
        self.assertTrue('low_confidence' in result or 'error' in result)
    
    @patch('src.core.classifier.ContentClassifier._call_groq_api')
    @patch('src.core.classifier.get_ai_config')
    def test_timeout_handling(self, mock_get_key, mock_groq_api):
        # Настраиваем мок для возврата валидного ключа
        mock_get_key.return_value = {'provider': 'groq', 'api_key': 'test_api_key', 'model': 'llama3-8b-8192'}
        # Настраиваем мок для имитации таймаута
        mock_groq_api.side_effect = asyncio.TimeoutError("Request timed out")
        
        # Создаем экземпляр классификатора после применения патчей
        classifier = ContentClassifier()
        sorter = MessageSorter(classifier=classifier)
        
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'def hello_world(): print("Hello, World!")',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию, определенную по паттернам
        self.assertIn('category', result)
        # Проверяем, что была добавлена информация об ошибке таймаута
        self.assertIn('error', result)
        self.assertIn('timeout', result['error'].lower())

if __name__ == '__main__':
    unittest.main()