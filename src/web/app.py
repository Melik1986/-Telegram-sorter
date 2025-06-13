"""Веб-приложение для DevDataSorter.

Этот модуль предоставляет веб-интерфейс для:
- Дашборд с визуализацией структуры папок
- Статистика классификации
- Управление настройками
- Поиск и фильтрация ресурсов
- Экспорт и архивирование
"""

import os
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict

try:
    from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None
    render_template = jsonify = request = send_file = redirect = url_for = flash = None
    CORS = None

try:
    import plotly.graph_objs as go
    import plotly.utils
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    plotly = None

from ..core.classifier import DevDataClassifier
from ..utils.semantic_search import SemanticSearchEngine
from ..utils.natural_commands import NaturalCommandProcessor
from ..utils.metadata_extractor import MetadataExtractor
from ..utils.github_integration import create_github_integration, backup_to_github
from ..core.config import is_github_available

logger = logging.getLogger(__name__)

class WebApp:
    """Веб-приложение для DevDataSorter."""
    
    def __init__(self, data_dir: str = "data", debug: bool = False):
        """Инициализация веб-приложения.
        
        Args:
            data_dir: Директория с данными
            debug: Режим отладки
        """
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is required for web interface. Install with: pip install flask flask-cors")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Инициализация компонентов
        self.classifier = DevDataClassifier(str(self.data_dir))
        self.search_engine = SemanticSearchEngine(str(self.data_dir))
        self.command_processor = NaturalCommandProcessor(str(self.data_dir))
        self.metadata_extractor = MetadataExtractor()
        
        # Инициализация GitHub интеграции
        self.github = create_github_integration() if is_github_available() else None
        if self.github:
            logger.info("GitHub интеграция инициализирована")
        else:
            logger.warning("GitHub интеграция недоступна")
        
        # Создание Flask приложения
        self.app = Flask(__name__, 
                        template_folder=str(Path(__file__).parent / 'templates'),
                        static_folder=str(Path(__file__).parent / 'static'))
        self.app.secret_key = 'dev-data-sorter-secret-key'
        self.app.config['DEBUG'] = debug
        
        # Включение CORS
        CORS(self.app)
        
        # Регистрация маршрутов
        self._register_routes()
        
        logger.info("Web application initialized")
    
    def _register_routes(self):
        """Регистрация маршрутов Flask."""
        
        @self.app.route('/')
        def index():
            """Главная страница."""
            return render_template('index.html')
        
        @self.app.route('/dashboard')
        def dashboard():
            """Дашборд."""
            try:
                # Получение статистики
                stats = self._get_dashboard_stats()
                
                # Создание графиков
                charts = self._create_charts(stats)
                
                return render_template('dashboard.html', 
                                     stats=stats, 
                                     charts=charts)
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
                flash(f"Ошибка загрузки дашборда: {str(e)}", 'error')
                return render_template('dashboard.html', stats={}, charts={})
        
        @self.app.route('/search')
        def search_page():
            """Страница поиска."""
            return render_template('search.html')
        
        @self.app.route('/settings')
        def settings_page():
            """Страница настроек."""
            try:
                settings = self._load_settings()
                return render_template('settings.html', settings=settings)
            except Exception as e:
                logger.error(f"Settings page error: {e}")
                flash(f"Ошибка загрузки настроек: {str(e)}", 'error')
                return render_template('settings.html', settings={})
        
        # API маршруты
        @self.app.route('/api/search', methods=['POST'])
        def api_search():
            """API поиска."""
            try:
                data = request.get_json()
                query = data.get('query', '')
                filters = data.get('filters', {})
                
                # Выполнение поиска
                results = self.search_engine.search(
                    query=query,
                    filters=self._convert_filters(filters),
                    top_k=data.get('limit', 20)
                )
                
                return jsonify({
                    'success': True,
                    'results': [asdict(result) for result in results],
                    'total': len(results)
                })
                
            except Exception as e:
                logger.error(f"Search API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # GitHub API маршруты
        @self.app.route('/api/github/status')
        def api_github_status():
            """API статуса GitHub интеграции."""
            try:
                if not self.github:
                    return jsonify({
                        'success': False,
                        'configured': False,
                        'message': 'GitHub интеграция не настроена'
                    })
                
                # Тестирование соединения
                test_result = self.github.test_connection()
                
                # Получение информации о репозитории
                repo_info = self.github.get_repository_info()
                
                return jsonify({
                    'success': True,
                    'configured': True,
                    'connection': test_result,
                    'repository': repo_info,
                    'auto_commit': self.github.auto_commit
                })
                
            except Exception as e:
                logger.error(f"GitHub status API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/github/backup', methods=['POST'])
        def api_github_backup():
            """API создания резервной копии в GitHub."""
            try:
                if not self.github:
                    return jsonify({
                        'success': False,
                        'error': 'GitHub интеграция не настроена'
                    }), 400
                
                data = request.get_json()
                backup_name = data.get('backup_name')
                include_files = data.get('include_files', True)
                include_settings = data.get('include_settings', True)
                
                # Подготовка данных для резервного копирования
                backup_data = {
                    'metadata': {
                        'created_at': datetime.now().isoformat(),
                        'version': '1.0',
                        'source': 'DevDataSorter Web Interface'
                    }
                }
                
                if include_settings:
                    backup_data['settings'] = self._load_settings()
                
                if include_files:
                    backup_data['file_structure'] = self._get_folder_structure()
                    backup_data['statistics'] = self._get_dashboard_stats()
                
                # Создание резервной копии
                result = self.github.backup_data(backup_data, backup_name)
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"GitHub backup API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/github/backups')
        def api_github_backups():
            """API списка резервных копий в GitHub."""
            try:
                if not self.github:
                    return jsonify({
                        'success': False,
                        'error': 'GitHub интеграция не настроена'
                    }), 400
                
                result = self.github.list_backups()
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"GitHub backups list API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/github/repository', methods=['POST'])
        def api_github_create_repository():
            """API создания репозитория GitHub."""
            try:
                if not self.github:
                    return jsonify({
                        'success': False,
                        'error': 'GitHub интеграция не настроена'
                    }), 400
                
                data = request.get_json()
                description = data.get('description', 'DevDataSorter backup repository')
                
                result = self.github.create_repository(description)
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"GitHub create repository API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/github/sync', methods=['POST'])
        def api_github_sync():
            """API синхронизации с GitHub."""
            try:
                if not self.github:
                    return jsonify({
                        'success': False,
                        'error': 'GitHub интеграция не настроена'
                    }), 400
                
                # Автоматическое создание резервной копии
                backup_data = {
                    'settings': self._load_settings(),
                    'file_structure': self._get_folder_structure(),
                    'statistics': self._get_dashboard_stats(),
                    'metadata': {
                        'sync_time': datetime.now().isoformat(),
                        'version': '1.0',
                        'source': 'Auto Sync'
                    }
                }
                
                result = backup_to_github(backup_data, self.github)
                
                if result['success']:
                    logger.info("Автоматическая синхронизация с GitHub выполнена")
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"GitHub sync API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/github/settings', methods=['GET', 'POST'])
        def api_github_settings():
            """API для работы с настройками GitHub."""
            try:
                if request.method == 'GET':
                    # Загрузка настроек GitHub
                    settings_file = self.data_dir / 'github_settings.json'
                    if settings_file.exists():
                        with open(settings_file, 'r', encoding='utf-8') as f:
                            settings = json.load(f)
                        # Не возвращаем токен по соображениям безопасности
                        safe_settings = {
                            'username': settings.get('username', '')
                        }
                        return jsonify({
                            'success': True,
                            'settings': safe_settings
                        })
                    else:
                        return jsonify({
                            'success': True,
                            'settings': {}
                        })
                
                elif request.method == 'POST':
                    # Сохранение настроек GitHub
                    data = request.get_json()
                    token = data.get('token', '').strip()
                    username = data.get('username', '').strip()
                    
                    if not token or not username:
                        return jsonify({
                            'success': False,
                            'error': 'Токен и имя пользователя обязательны'
                        }), 400
                    
                    # Сохранение настроек в файл
                    settings = {
                        'token': token,
                        'username': username,
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    settings_file = self.data_dir / 'github_settings.json'
                    with open(settings_file, 'w', encoding='utf-8') as f:
                        json.dump(settings, f, indent=2, ensure_ascii=False)
                    
                    # Обновление переменных окружения для текущей сессии
                    os.environ['GITHUB_TOKEN'] = token
                    os.environ['GITHUB_USERNAME'] = username
                    
                    # Пересоздание GitHub интеграции с новыми настройками
                    try:
                        from ..utils.github_integration import create_github_integration
                        self.github = create_github_integration()
                        if self.github:
                            logger.info(f"GitHub интеграция обновлена для пользователя {username}")
                        else:
                            logger.warning("Не удалось создать GitHub интеграцию с новыми настройками")
                    except Exception as e:
                        logger.error(f"Ошибка обновления GitHub интеграции: {e}")
                    
                    return jsonify({
                        'success': True,
                        'message': 'Настройки GitHub успешно сохранены'
                    })
                    
            except Exception as e:
                logger.error(f"GitHub settings API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/github/test', methods=['POST'])
        def api_github_test():
            """API для тестирования подключения к GitHub."""
            try:
                data = request.get_json()
                token = data.get('token', '').strip()
                username = data.get('username', '').strip()
                
                if not token or not username:
                    return jsonify({
                        'success': False,
                        'error': 'Токен и имя пользователя обязательны'
                    }), 400
                
                # Создание временного объекта для тестирования
                import requests
                
                headers = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "DevDataSorter/1.0"
                }
                
                # Тестирование подключения
                response = requests.get(
                    "https://api.github.com/user",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    if user_data.get('login') == username:
                        return jsonify({
                            'success': True,
                            'message': f'Подключение успешно! Пользователь: {user_data.get("name", username)}'
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': f'Имя пользователя не совпадает. Ожидается: {username}, получено: {user_data.get("login")}'
                        })
                elif response.status_code == 401:
                    return jsonify({
                        'success': False,
                        'error': 'Неверный токен GitHub'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Ошибка GitHub API: {response.status_code}'
                    })
                    
            except requests.exceptions.RequestException as e:
                return jsonify({
                    'success': False,
                    'error': f'Ошибка соединения: {str(e)}'
                })
            except Exception as e:
                logger.error(f"GitHub test API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/command', methods=['POST'])
        def api_command():
            """API обработки естественных команд."""
            try:
                data = request.get_json()
                command_text = data.get('command', '')
                
                # Парсинг команды
                parsed_command = self.command_processor.parse_command(command_text)
                
                # Выполнение команды
                result = self.command_processor.execute_command(
                    parsed_command,
                    search_engine=self.search_engine,
                    organizer=self.classifier
                )
                
                return jsonify({
                    'success': True,
                    'command': asdict(parsed_command),
                    'result': result
                })
                
            except Exception as e:
                logger.error(f"Command API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/classify', methods=['POST'])
        def api_classify():
            """API классификации файлов."""
            try:
                data = request.get_json()
                file_path = data.get('file_path', '')
                
                if not file_path or not os.path.exists(file_path):
                    return jsonify({
                        'success': False,
                        'error': 'File not found'
                    }), 400
                
                # Классификация файла
                result = self.classifier.classify_file(file_path)
                
                return jsonify({
                    'success': True,
                    'classification': asdict(result)
                })
                
            except Exception as e:
                logger.error(f"Classify API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/stats')
        def api_stats():
            """API статистики."""
            try:
                stats = self._get_dashboard_stats()
                return jsonify({
                    'success': True,
                    'stats': stats
                })
                
            except Exception as e:
                logger.error(f"Stats API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/export', methods=['POST'])
        def api_export():
            """API экспорта данных."""
            try:
                data = request.get_json()
                export_format = data.get('format', 'json')
                filters = data.get('filters', {})
                
                # Создание экспорта
                export_path = self._create_export(export_format, filters)
                
                return send_file(
                    export_path,
                    as_attachment=True,
                    download_name=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"
                )
                
            except Exception as e:
                logger.error(f"Export API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/settings', methods=['GET', 'POST'])
        def api_settings():
            """API настроек."""
            try:
                if request.method == 'GET':
                    settings = self._load_settings()
                    return jsonify({
                        'success': True,
                        'settings': settings
                    })
                
                elif request.method == 'POST':
                    data = request.get_json()
                    self._save_settings(data)
                    return jsonify({
                        'success': True,
                        'message': 'Settings saved successfully'
                    })
                    
            except Exception as e:
                logger.error(f"Settings API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/folder-structure')
        def api_folder_structure():
            """API структуры папок."""
            try:
                structure = self._get_folder_structure()
                return jsonify({
                    'success': True,
                    'structure': structure
                })
                
            except Exception as e:
                logger.error(f"Folder structure API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/advanced-search', methods=['POST'])
        def api_advanced_search():
            """API расширенного поиска."""
            try:
                data = request.get_json()
                query = data.get('query', '')
                search_types = data.get('search_types', {})
                filters = data.get('filters', {})
                sort = data.get('sort', {'by': 'relevance', 'order': 'desc'})
                page = data.get('page', 1)
                per_page = data.get('per_page', 20)
                
                # Выполнение расширенного поиска
                results = self.search_engine.search(
                    query=query,
                    filters=self._convert_advanced_filters(filters),
                    search_types=search_types,
                    top_k=per_page * 10  # Получаем больше для сортировки
                )
                
                # Применение сортировки
                sorted_results = self._sort_search_results(results, sort)
                
                # Пагинация
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                paginated_results = sorted_results[start_idx:end_idx]
                
                # Подготовка результатов для frontend
                formatted_results = []
                for result in paginated_results:
                    formatted_result = {
                        'id': getattr(result, 'id', str(hash(result.path))),
                        'title': getattr(result, 'title', result.path.name),
                        'name': result.path.name,
                        'path': str(result.path),
                        'category': getattr(result, 'category', 'other'),
                        'subcategory': getattr(result, 'subcategory', ''),
                        'description': getattr(result, 'description', ''),
                        'tags': getattr(result, 'tags', []),
                        'score': getattr(result, 'score', 0.0),
                        'size': getattr(result, 'size', 0),
                        'modified_date': getattr(result, 'modified_date', ''),
                        'preview': self._get_file_preview(result.path)
                    }
                    formatted_results.append(formatted_result)
                
                total_results = len(sorted_results)
                total_pages = (total_results + per_page - 1) // per_page
                
                return jsonify({
                    'success': True,
                    'results': formatted_results,
                    'total_results': total_results,
                    'total_pages': total_pages,
                    'current_page': page,
                    'per_page': per_page
                })
                
            except Exception as e:
                logger.error(f"Advanced search API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/search-suggestions', methods=['POST'])
        def api_search_suggestions():
            """API подсказок для поиска."""
            try:
                data = request.get_json()
                query = data.get('query', '').strip()
                
                if len(query) < 2:
                    return jsonify({
                        'success': True,
                        'suggestions': []
                    })
                
                suggestions = self._get_search_suggestions(query)
                
                return jsonify({
                    'success': True,
                    'suggestions': suggestions
                })
                
            except Exception as e:
                logger.error(f"Search suggestions API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/popular-tags')
        def api_popular_tags():
            """API популярных тегов."""
            try:
                tags = self._get_popular_tags()
                
                return jsonify({
                    'success': True,
                    'tags': tags
                })
                
            except Exception as e:
                logger.error(f"Popular tags API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/categories')
        def api_categories():
            """API категорий и подкатегорий."""
            try:
                categories = self._get_categories_hierarchy()
                
                return jsonify({
                    'success': True,
                    'categories': categories
                })
                
            except Exception as e:
                logger.error(f"Categories API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/saved-searches', methods=['GET', 'POST', 'DELETE'])
        def api_saved_searches():
            """API сохраненных поисков."""
            try:
                if request.method == 'GET':
                    searches = self._load_saved_searches()
                    return jsonify({
                        'success': True,
                        'searches': searches
                    })
                
                elif request.method == 'POST':
                    data = request.get_json()
                    search_data = {
                        'id': str(uuid.uuid4()),
                        'name': data.get('name', ''),
                        'query': data.get('query', ''),
                        'filters': data.get('filters', {}),
                        'search_types': data.get('search_types', {}),
                        'created_at': datetime.now().isoformat()
                    }
                    
                    self._save_search(search_data)
                    
                    return jsonify({
                        'success': True,
                        'message': 'Search saved successfully',
                        'search': search_data
                    })
                
                elif request.method == 'DELETE':
                    data = request.get_json()
                    search_id = data.get('id')
                    
                    self._delete_saved_search(search_id)
                    
                    return jsonify({
                        'success': True,
                        'message': 'Search deleted successfully'
                    })
                    
            except Exception as e:
                logger.error(f"Saved searches API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _get_dashboard_stats(self) -> Dict[str, Any]:
        """Получение статистики для дашборда."""
        try:
            # Базовая статистика
            stats = {
                'total_files': 0,
                'categories': {},
                'languages': {},
                'frameworks': {},
                'difficulty_levels': {},
                'file_types': {},
                'recent_activity': [],
                'size_distribution': {},
                'timeline': {}
            }
            
            # Получение статистики из поискового движка
            search_stats = self.search_engine.get_stats()
            if search_stats:
                stats.update(search_stats)
            
            # Анализ файлов в директории
            if self.data_dir.exists():
                for file_path in self.data_dir.rglob('*'):
                    if file_path.is_file():
                        stats['total_files'] += 1
                        
                        # Анализ типа файла
                        file_ext = file_path.suffix.lower()
                        stats['file_types'][file_ext] = stats['file_types'].get(file_ext, 0) + 1
                        
                        # Анализ размера
                        try:
                            size = file_path.stat().st_size
                            size_category = self._categorize_file_size(size)
                            stats['size_distribution'][size_category] = stats['size_distribution'].get(size_category, 0) + 1
                        except:
                            pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {}
    
    def _create_charts(self, stats: Dict[str, Any]) -> Dict[str, str]:
        """Создание графиков для дашборда."""
        charts = {}
        
        if not PLOTLY_AVAILABLE:
            return charts
        
        try:
            # График категорий
            if stats.get('categories'):
                categories = stats['categories']
                fig = go.Figure(data=[
                    go.Pie(
                        labels=list(categories.keys()),
                        values=list(categories.values()),
                        hole=0.3
                    )
                ])
                fig.update_layout(
                    title="Распределение по категориям",
                    showlegend=True
                )
                charts['categories'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
            # График языков программирования
            if stats.get('languages'):
                languages = stats['languages']
                fig = go.Figure(data=[
                    go.Bar(
                        x=list(languages.keys()),
                        y=list(languages.values()),
                        marker_color='lightblue'
                    )
                ])
                fig.update_layout(
                    title="Языки программирования",
                    xaxis_title="Язык",
                    yaxis_title="Количество"
                )
                charts['languages'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
            # График типов файлов
            if stats.get('file_types'):
                file_types = stats['file_types']
                fig = go.Figure(data=[
                    go.Pie(
                        labels=list(file_types.keys()),
                        values=list(file_types.values())
                    )
                ])
                fig.update_layout(
                    title="Типы файлов"
                )
                charts['file_types'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
            # График размеров файлов
            if stats.get('size_distribution'):
                sizes = stats['size_distribution']
                fig = go.Figure(data=[
                    go.Bar(
                        x=list(sizes.keys()),
                        y=list(sizes.values()),
                        marker_color='lightgreen'
                    )
                ])
                fig.update_layout(
                    title="Распределение размеров файлов",
                    xaxis_title="Размер",
                    yaxis_title="Количество"
                )
                charts['sizes'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            logger.error(f"Error creating charts: {e}")
        
        return charts
    
    def _get_folder_structure(self) -> Dict[str, Any]:
        """Получение структуры папок."""
        try:
            def build_tree(path: Path) -> Dict[str, Any]:
                """Рекурсивное построение дерева папок."""
                node = {
                    'name': path.name,
                    'path': str(path),
                    'type': 'folder' if path.is_dir() else 'file',
                    'children': []
                }
                
                if path.is_dir():
                    try:
                        for child in sorted(path.iterdir()):
                            if not child.name.startswith('.'):
                                node['children'].append(build_tree(child))
                    except PermissionError:
                        pass
                else:
                    # Добавление метаданных файла
                    try:
                        stat = path.stat()
                        node.update({
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'extension': path.suffix.lower()
                        })
                    except:
                        pass
                
                return node
            
            if self.data_dir.exists():
                return build_tree(self.data_dir)
            else:
                return {'name': 'data', 'type': 'folder', 'children': []}
                
        except Exception as e:
            logger.error(f"Error getting folder structure: {e}")
            return {'name': 'data', 'type': 'folder', 'children': []}
    
    def _convert_filters(self, filters: Dict[str, Any]) -> Any:
        """Конвертация фильтров из веб-формата."""
        # Здесь должна быть логика конвертации фильтров
        # в формат, понятный поисковому движку
        return filters
    
    def _convert_advanced_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертация расширенных фильтров."""
        converted = {}
        
        # Конвертация фильтров категорий
        if filters.get('category'):
            converted['category'] = filters['category']
        if filters.get('subcategory'):
            converted['subcategory'] = filters['subcategory']
        
        # Конвертация фильтров файлов
        if filters.get('file_extension'):
            converted['file_extension'] = filters['file_extension']
        if filters.get('min_size') is not None:
            converted['min_size'] = filters['min_size']
        if filters.get('max_size') is not None:
            converted['max_size'] = filters['max_size']
        
        # Конвертация фильтров даты
        if filters.get('date_from'):
            converted['date_from'] = filters['date_from']
        if filters.get('date_to'):
            converted['date_to'] = filters['date_to']
        
        # Конвертация тегов
        if filters.get('tags'):
            converted['tags'] = [tag.strip() for tag in filters['tags'] if tag.strip()]
        
        # Конвертация пути
        if filters.get('path'):
            converted['path'] = filters['path']
            converted['include_subfolders'] = filters.get('include_subfolders', True)
        
        return converted
    
    def _sort_search_results(self, results: List[Any], sort: Dict[str, str]) -> List[Any]:
        """Сортировка результатов поиска."""
        sort_by = sort.get('by', 'relevance')
        sort_order = sort.get('order', 'desc')
        reverse = sort_order == 'desc'
        
        if sort_by == 'relevance':
            return sorted(results, key=lambda x: getattr(x, 'score', 0), reverse=reverse)
        elif sort_by == 'name':
            return sorted(results, key=lambda x: x.path.name.lower(), reverse=reverse)
        elif sort_by == 'date':
            return sorted(results, key=lambda x: getattr(x, 'modified_date', ''), reverse=reverse)
        elif sort_by == 'size':
            return sorted(results, key=lambda x: getattr(x, 'size', 0), reverse=reverse)
        else:
            return results
    
    def _get_file_preview(self, file_path: Path, max_lines: int = 10) -> str:
        """Получение превью файла."""
        try:
            if not file_path.exists() or file_path.stat().st_size > 1024 * 1024:  # > 1MB
                return ''
            
            # Определение типа файла
            text_extensions = {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.yml', '.yaml'}
            if file_path.suffix.lower() not in text_extensions:
                return ''
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip())
                
                preview = '\n'.join(lines)
                if len(preview) > 500:  # Ограничение по символам
                    preview = preview[:500] + '...'
                
                return preview
                
        except Exception as e:
            logger.debug(f"Error getting file preview for {file_path}: {e}")
            return ''
    
    def _get_search_suggestions(self, query: str) -> List[Dict[str, str]]:
        """Получение подсказок для поиска."""
        suggestions = []
        
        try:
            # Подсказки на основе популярных тегов
            popular_tags = self._get_popular_tags()
            for tag in popular_tags[:5]:
                if query.lower() in tag['name'].lower():
                    suggestions.append({
                        'text': tag['name'],
                        'type': 'tag',
                        'icon': 'tag'
                    })
            
            # Подсказки на основе категорий
            categories = self._get_categories_hierarchy()
            for category, subcategories in categories.items():
                if query.lower() in category.lower():
                    suggestions.append({
                        'text': category,
                        'type': 'category',
                        'icon': 'folder'
                    })
                
                for subcategory in subcategories:
                    if query.lower() in subcategory.lower():
                        suggestions.append({
                            'text': subcategory,
                            'type': 'subcategory',
                            'icon': 'folder-open'
                        })
            
            # Подсказки на основе расширений файлов
            common_extensions = ['.py', '.js', '.html', '.css', '.json', '.md', '.txt', '.yml']
            for ext in common_extensions:
                if query.lower() in ext:
                    suggestions.append({
                        'text': f'files with {ext} extension',
                        'type': 'extension',
                        'icon': 'file-code'
                    })
            
            # Естественные команды
            natural_commands = [
                'найди все React компоненты',
                'покажи Python скрипты за последний месяц',
                'найди документацию по API',
                'покажи большие файлы',
                'найди файлы с ошибками'
            ]
            
            for command in natural_commands:
                if any(word in command.lower() for word in query.lower().split()):
                    suggestions.append({
                        'text': command,
                        'type': 'command',
                        'icon': 'comments'
                    })
            
            # Ограничение количества подсказок
            return suggestions[:10]
            
        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return []
    
    def _get_popular_tags(self) -> List[Dict[str, Any]]:
        """Получение популярных тегов."""
        try:
            # Получение тегов из поискового движка
            if hasattr(self.search_engine, 'get_popular_tags'):
                return self.search_engine.get_popular_tags()
            
            # Заглушка с популярными тегами
            return [
                {'name': 'python', 'count': 45},
                {'name': 'javascript', 'count': 38},
                {'name': 'react', 'count': 25},
                {'name': 'api', 'count': 22},
                {'name': 'tutorial', 'count': 18},
                {'name': 'documentation', 'count': 15},
                {'name': 'web', 'count': 12},
                {'name': 'database', 'count': 10}
            ]
            
        except Exception as e:
            logger.error(f"Error getting popular tags: {e}")
            return []
    
    def _get_categories_hierarchy(self) -> Dict[str, List[str]]:
        """Получение иерархии категорий."""
        return {
            'code': ['scripts', 'libraries', 'frameworks', 'utilities'],
            'documentation': ['api', 'tutorials', 'guides', 'references'],
            'tutorial': ['beginner', 'intermediate', 'advanced', 'examples'],
            'reference': ['cheatsheets', 'specifications', 'standards'],
            'project': ['web', 'mobile', 'desktop', 'data-science'],
            'other': ['configs', 'templates', 'resources']
        }
    
    def _load_saved_searches(self) -> List[Dict[str, Any]]:
        """Загрузка сохраненных поисков."""
        searches_path = self.data_dir / 'saved_searches.json'
        
        try:
            if searches_path.exists():
                with open(searches_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading saved searches: {e}")
        
        return []
    
    def _save_search(self, search_data: Dict[str, Any]):
        """Сохранение поиска."""
        searches_path = self.data_dir / 'saved_searches.json'
        
        try:
            searches = self._load_saved_searches()
            searches.append(search_data)
            
            with open(searches_path, 'w', encoding='utf-8') as f:
                json.dump(searches, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving search: {e}")
            raise
    
    def _delete_saved_search(self, search_id: str):
        """Удаление сохраненного поиска."""
        searches_path = self.data_dir / 'saved_searches.json'
        
        try:
            searches = self._load_saved_searches()
            searches = [s for s in searches if s.get('id') != search_id]
            
            with open(searches_path, 'w', encoding='utf-8') as f:
                json.dump(searches, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error deleting saved search: {e}")
            raise
    
    def _categorize_file_size(self, size: int) -> str:
        """Категоризация размера файла."""
        if size < 1024:  # < 1KB
            return 'Очень маленький'
        elif size < 1024 * 1024:  # < 1MB
            return 'Маленький'
        elif size < 10 * 1024 * 1024:  # < 10MB
            return 'Средний'
        elif size < 100 * 1024 * 1024:  # < 100MB
            return 'Большой'
        else:
            return 'Очень большой'
    
    def _create_export(self, export_format: str, filters: Dict[str, Any]) -> str:
        """Создание файла экспорта."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_path = self.data_dir / f"export_{timestamp}.{export_format}"
        
        # Получение данных для экспорта
        export_data = {
            'timestamp': timestamp,
            'format': export_format,
            'filters': filters,
            'stats': self._get_dashboard_stats(),
            'data': []
        }
        
        # Сохранение в зависимости от формата
        if export_format == 'json':
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        elif export_format == 'csv':
            import csv
            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Format', 'Total Files'])
                writer.writerow([timestamp, export_format, export_data['stats'].get('total_files', 0)])
        
        return str(export_path)
    
    def _load_settings(self) -> Dict[str, Any]:
        """Загрузка настроек."""
        settings_path = self.data_dir / 'settings.json'
        
        default_settings = {
            'search': {
                'default_limit': 20,
                'enable_semantic_search': True,
                'similarity_threshold': 0.7
            },
            'classification': {
                'auto_classify': True,
                'confidence_threshold': 0.8,
                'create_folders': True
            },
            'interface': {
                'theme': 'light',
                'language': 'ru',
                'items_per_page': 10
            },
            'export': {
                'default_format': 'json',
                'include_metadata': True,
                'compress_exports': False
            }
        }
        
        try:
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    # Объединение с настройками по умолчанию
                    for category, options in default_settings.items():
                        if category in saved_settings:
                            options.update(saved_settings[category])
                        saved_settings[category] = options
                    return saved_settings
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
        
        return default_settings
    
    def _save_settings(self, settings: Dict[str, Any]):
        """Сохранение настроек."""
        settings_path = self.data_dir / 'settings.json'
        
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            raise
    
    def run(self, host: str = '127.0.0.1', port: int = 5000, debug: bool = None):
        """Запуск веб-приложения.
        
        Args:
            host: Хост для запуска
            port: Порт для запуска
            debug: Режим отладки
        """
        if debug is None:
            debug = self.app.config['DEBUG']
        
        logger.info(f"Starting web application on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_app(data_dir: str = "data", debug: bool = False) -> Flask:
    """Фабрика для создания Flask приложения.
    
    Args:
        data_dir: Директория с данными
        debug: Режим отладки
        
    Returns:
        Экземпляр Flask приложения
    """
    web_app = WebApp(data_dir, debug)
    return web_app.app

if __name__ == '__main__':
    # Запуск приложения
    import argparse
    
    parser = argparse.ArgumentParser(description='DevDataSorter Web Interface')
    parser.add_argument('--data-dir', default='data', help='Data directory')
    parser.add_argument('--host', default='127.0.0.1', help='Host to run on')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    try:
        web_app = WebApp(args.data_dir, args.debug)
        web_app.run(args.host, args.port, args.debug)
    except ImportError as e:
        print(f"Error: {e}")
        print("Please install required dependencies: pip install flask flask-cors plotly")
    except Exception as e:
        print(f"Error starting web application: {e}")