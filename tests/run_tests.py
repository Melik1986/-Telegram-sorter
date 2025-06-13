import unittest
import sys
import os
import unittest

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Загружаем все тесты из текущей директории
loader = unittest.TestLoader()
start_dir = os.path.dirname(os.path.abspath(__file__))
suite = loader.discover(start_dir, pattern="test_*.py")

# Запускаем тесты
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Выходим с кодом ошибки, если тесты не прошли
sys.exit(not result.wasSuccessful())