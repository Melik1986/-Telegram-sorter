# Автоматическое создание папок

Этот документ описывает новую функциональность автоматического создания папок в DevDataSorter.

## Обзор

Система автоматически создает структурированные папки на основе классификации контента. Каждое сообщение анализируется и помещается в соответствующую категорию с автоматическим созданием папок.

## Структура папок

### Основные категории

```
sorted_content/
├── Frontend/
│   ├── General/
│   ├── CSS-Styling/
│   ├── JavaScript/
│   ├── React/
│   ├── Vue/
│   └── Angular/
├── Backend/
│   ├── General/
│   ├── NodeJS/
│   ├── Python/
│   └── PHP/
├── Database/
├── DevTools/
│   ├── Build-Tools/
│   ├── Testing/
│   └── DevOps/
├── Design/
│   ├── UI-UX/
│   └── Assets/
├── Learning/
│   ├── Tutorials/
│   ├── Videos/
│   └── Documentation/
├── Code/
│   ├── Snippets/
│   ├── Templates/
│   └── Libraries/
├── Specialized/
│   ├── Animation/
│   ├── Performance/
│   └── Security/
└── General/
    ├── Articles/
    ├── Tools/
    └── Other/
```

## Использование

### Базовое использование

```python
from src.handlers.message_sorter import MessageSorter

# Инициализация с автоматическим созданием папок
sorter = MessageSorter(base_folder='./my_content')

# Классификация с созданием папок
message = {'text': 'React hooks tutorial with TypeScript'}
result = await sorter.sort_message(message, auto_create_folders=True)

print(f"Категория: {result['category']}")
print(f"Папка: {result['folder_path']}")
print(f"Создана: {result['folder_created']}")
```

### Отключение автоматического создания

```python
# Только классификация без создания папок
result = await sorter.sort_message(message, auto_create_folders=False)
```

### Получение статистики папок

```python
# Структура папок
structure = sorter.get_folder_structure()
print(structure)

# Статистика по категориям
stats = sorter.get_category_stats()
for category, info in stats.items():
    if info['exists']:
        print(f"{category}: {info['subfolders_count']} подпапок")
```

## Логика создания папок

### 1. Базовая категория
Определяется основная папка на основе категории классификации:
- `frontend` → `Frontend/General/`
- `react_ecosystem` → `Frontend/React/`
- `nodejs` → `Backend/NodeJS/`

### 2. Подкатегория
Если определена подкатегория, создается дополнительная папка:
- `Frontend/React/Hooks/`
- `Backend/NodeJS/Express/`

### 3. Технологический стек
Если определена одна конкретная технология, создается папка для неё:
- `Frontend/React/TypeScript/`
- `Backend/NodeJS/MongoDB/`

### 4. Очистка имен папок
Имена папок автоматически очищаются:
- Удаляются специальные символы
- Пробелы заменяются дефисами
- Применяется капитализация
- `"react hooks"` → `"React-Hooks"`

## Примеры классификации

### Frontend разработка
```python
message = {'text': 'CSS Grid layout tutorial'}
# Результат: Frontend/CSS-Styling/

message = {'text': 'React hooks with TypeScript'}
# Результат: Frontend/React/TypeScript/
```

### Backend разработка
```python
message = {'text': 'Node.js Express API'}
# Результат: Backend/NodeJS/Express/

message = {'text': 'Python Django tutorial'}
# Результат: Backend/Python/Django/
```

### Инструменты разработки
```python
message = {'text': 'Webpack configuration guide'}
# Результат: DevTools/Build-Tools/Webpack/

message = {'text': 'Jest testing setup'}
# Результат: DevTools/Testing/Jest/
```

## Конфигурация

### Настройка базовой папки
```python
# Пользовательская базовая папка
sorter = MessageSorter(base_folder='/path/to/my/content')

# Папка по умолчанию: './sorted_content'
sorter = MessageSorter()
```

### Маппинг категорий
Маппинг категорий на папки настраивается в `category_folders`:

```python
category_folders = {
    'frontend': 'Frontend/General',
    'react_ecosystem': 'Frontend/React',
    'nodejs': 'Backend/NodeJS',
    # ... другие категории
}
```

## Логирование

Система ведет логи создания папок:

```
INFO: Base folder ensured: ./sorted_content
INFO: Created folder: ./sorted_content/Frontend/React/TypeScript
```

## Обработка ошибок

- Если создание папки не удается, возвращается `None` для `folder_path`
- Ошибки логируются с подробностями
- Классификация продолжается даже при ошибках создания папок

## Тестирование

Запустите тестовый скрипт для проверки функциональности:

```bash
python test_auto_folders.py
```

Тест создаст папки для различных типов контента и покажет:
- Результаты классификации
- Созданную структуру папок
- Статистику по категориям
- Точность классификации

## Производительность

- Папки создаются только при необходимости
- Используется `mkdir(parents=True, exist_ok=True)` для эффективности
- Кэширование структуры папок для быстрого доступа

## Безопасность

- Имена папок очищаются от опасных символов
- Проверка существования папок перед созданием
- Обработка исключений при работе с файловой системой