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
        # Создаем экземпляр классификатора
        self.classifier = ContentClassifier()
        
        # Создаем экземпляр сортировщика сообщений
        self.sorter = MessageSorter(classifier=self.classifier)
    
    @patch('classifier.openai.ChatCompletion.create')
    @patch('classifier.get_openai_key')
    def test_openai_api_error(self, mock_get_key, mock_openai_create):
        # Настраиваем мок для возврата валидного ключа
        mock_get_key.return_value = "test_api_key"
        # Настраиваем мок для имитации ошибки API
        mock_openai_create.side_effect = Exception("OpenAI API Error")
        
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'def hello_world(): print("Hello, World!")',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки и проверяем, что он корректно обрабатывает ошибку
        result = asyncio.run(self.sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию, определенную по паттернам
        self.assertIn('category', result)
        # Проверяем, что была добавлена информация об ошибке
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'OpenAI API Error')
    
    @patch('classifier.openai.ChatCompletion.create')
    @patch('classifier.get_openai_key')
    def test_invalid_api_response(self, mock_get_key, mock_openai_create):
        # Настраиваем мок для возврата валидного ключа
        mock_get_key.return_value = "test_api_key"
        # Настраиваем мок для возврата некорректного ответа
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = {'content': 'Invalid JSON response'}
        mock_openai_create.return_value = mock_response
        
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'def hello_world(): print("Hello, World!")',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(self.sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию, определенную по паттернам
        self.assertIn('category', result)
        # Проверяем, что была добавлена информация об ошибке
        self.assertIn('error', result)
    
    def test_empty_message(self):
        # Создаем пустое сообщение
        message = {
            'message_id': 123,
            'text': '',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(self.sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию 'other' для пустого сообщения
        self.assertEqual(result['category'], 'other')
    
    def test_message_without_text(self):
        # Создаем сообщение без текста
        message = {
            'message_id': 123,
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(self.sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию 'other' для сообщения без текста
        self.assertEqual(result['category'], 'other')
    
    @patch('classifier.openai.ChatCompletion.create')
    @patch('classifier.get_openai_key')
    def test_low_confidence_classification(self, mock_get_key, mock_openai_create):
        # Настраиваем мок для возврата валидного ключа
        mock_get_key.return_value = "test_api_key"
        # Настраиваем мок для возврата классификации с низкой уверенностью
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"category": "code_examples", "confidence": 0.3, "subcategory": "python_scripts"}'
        mock_openai_create.return_value = mock_response
        
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'def hello_world(): print("Hello, World!")',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(self.sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию и низкую уверенность
        self.assertEqual(result['category'], 'code_examples')
        self.assertEqual(result['confidence'], 0.3)
        # Проверяем, что добавлена пометка о низкой уверенности
        self.assertIn('low_confidence', result)
        self.assertTrue(result['low_confidence'])
    
    @patch('classifier.openai.ChatCompletion.create')
    @patch('classifier.get_openai_key')
    def test_timeout_handling(self, mock_get_key, mock_openai_create):
        # Настраиваем мок для возврата валидного ключа
        mock_get_key.return_value = "test_api_key"
        # Настраиваем мок для имитации таймаута
        mock_openai_create.side_effect = asyncio.TimeoutError("Request timed out")
        
        # Создаем тестовое сообщение
        message = {
            'message_id': 123,
            'text': 'def hello_world(): print("Hello, World!")',
            'from': {'id': 456, 'username': 'test_user'},
            'chat': {'id': 789, 'type': 'private'}
        }
        
        # Вызываем метод сортировки
        result = asyncio.run(self.sorter.sort_message(message))
        
        # Проверяем, что результат содержит категорию, определенную по паттернам
        self.assertIn('category', result)
        # Проверяем, что была добавлена информация об ошибке таймаута
        self.assertIn('error', result)
        self.assertIn('timeout', result['error'].lower())

if __name__ == '__main__':
    unittest.main()