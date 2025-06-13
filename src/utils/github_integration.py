#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Integration Module for DevDataSorter

Предоставляет функциональность для:
- Создания и управления репозиториями
- Автоматического резервного копирования данных
- Синхронизации файлов с GitHub
- Управления коммитами и версионированием
"""

import os
import json
import base64
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

from ..core.config import get_github_config, is_github_available

logger = logging.getLogger(__name__)

class GitHubIntegration:
    """Класс для интеграции с GitHub API."""
    
    def __init__(self):
        """Инициализация GitHub интеграции."""
        if not requests:
            raise ImportError("Модуль requests не установлен. Установите: pip install requests")
        
        if not is_github_available():
            raise ValueError("GitHub не настроен. Проверьте GITHUB_TOKEN и GITHUB_USERNAME")
        
        self.config = get_github_config()
        self.token = self.config['token']
        self.username = self.config['username']
        self.repo_name = self.config['repo_name']
        self.auto_commit = self.config['auto_commit']
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevDataSorter/1.0"
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Тестирование соединения с GitHub API."""
        try:
            response = requests.get(
                f"{self.base_url}/user",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'success': True,
                    'user': user_data.get('login'),
                    'name': user_data.get('name'),
                    'message': 'Соединение с GitHub успешно установлено'
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'message': 'Ошибка авторизации GitHub'
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Ошибка соединения с GitHub'
            }
    
    def create_repository(self, description: str = "DevDataSorter backup repository") -> Dict[str, Any]:
        """Создание нового репозитория."""
        try:
            data = {
                "name": self.repo_name,
                "description": description,
                "private": True,
                "auto_init": True
            }
            
            response = requests.post(
                f"{self.base_url}/user/repos",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 201:
                repo_data = response.json()
                logger.info(f"Репозиторий {self.repo_name} успешно создан")
                return {
                    'success': True,
                    'repo_url': repo_data.get('html_url'),
                    'clone_url': repo_data.get('clone_url'),
                    'message': f'Репозиторий {self.repo_name} создан'
                }
            elif response.status_code == 422:
                # Репозиторий уже существует
                return {
                    'success': True,
                    'message': f'Репозиторий {self.repo_name} уже существует',
                    'existing': True
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'message': 'Ошибка создания репозитория'
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Ошибка соединения при создании репозитория'
            }
    
    def upload_file(self, file_path: str, content: str, commit_message: str = None) -> Dict[str, Any]:
        """Загрузка файла в репозиторий."""
        try:
            if commit_message is None:
                commit_message = f"Update {file_path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Кодирование содержимого в base64
            content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # Проверка существования файла
            existing_file = self.get_file(file_path)
            
            data = {
                "message": commit_message,
                "content": content_encoded
            }
            
            # Если файл существует, добавляем SHA для обновления
            if existing_file.get('success'):
                data["sha"] = existing_file['sha']
            
            response = requests.put(
                f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/{file_path}",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result_data = response.json()
                action = "обновлен" if existing_file.get('success') else "создан"
                logger.info(f"Файл {file_path} {action} в репозитории")
                return {
                    'success': True,
                    'sha': result_data['content']['sha'],
                    'download_url': result_data['content']['download_url'],
                    'message': f'Файл {file_path} {action}'
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'message': f'Ошибка загрузки файла {file_path}'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Ошибка при загрузке файла {file_path}'
            }
    
    def get_file(self, file_path: str) -> Dict[str, Any]:
        """Получение информации о файле из репозитория."""
        try:
            response = requests.get(
                f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/{file_path}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                file_data = response.json()
                return {
                    'success': True,
                    'sha': file_data['sha'],
                    'content': file_data['content'],
                    'encoding': file_data['encoding'],
                    'download_url': file_data['download_url']
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': 'Файл не найден',
                    'not_found': True
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def backup_data(self, data: Dict[str, Any], backup_name: str = None) -> Dict[str, Any]:
        """Создание резервной копии данных."""
        try:
            if backup_name is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"backup_{timestamp}.json"
            
            # Подготовка данных для резервного копирования
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'version': '1.0',
                'data': data
            }
            
            content = json.dumps(backup_data, ensure_ascii=False, indent=2)
            file_path = f"backups/{backup_name}"
            
            result = self.upload_file(
                file_path,
                content,
                f"Автоматическое резервное копирование - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            if result['success']:
                logger.info(f"Резервная копия {backup_name} создана")
                return {
                    'success': True,
                    'backup_name': backup_name,
                    'file_path': file_path,
                    'message': f'Резервная копия {backup_name} создана'
                }
            else:
                return result
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Ошибка создания резервной копии'
            }
    
    def list_backups(self) -> Dict[str, Any]:
        """Получение списка резервных копий."""
        try:
            response = requests.get(
                f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/backups",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                files = response.json()
                backups = []
                
                for file_info in files:
                    if file_info['type'] == 'file' and file_info['name'].endswith('.json'):
                        backups.append({
                            'name': file_info['name'],
                            'size': file_info['size'],
                            'download_url': file_info['download_url'],
                            'sha': file_info['sha']
                        })
                
                return {
                    'success': True,
                    'backups': backups,
                    'count': len(backups)
                }
            elif response.status_code == 404:
                return {
                    'success': True,
                    'backups': [],
                    'count': 0,
                    'message': 'Папка backups не найдена'
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_repository_info(self) -> Dict[str, Any]:
        """Получение информации о репозитории."""
        try:
            response = requests.get(
                f"{self.base_url}/repos/{self.username}/{self.repo_name}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                repo_data = response.json()
                return {
                    'success': True,
                    'name': repo_data['name'],
                    'full_name': repo_data['full_name'],
                    'description': repo_data['description'],
                    'private': repo_data['private'],
                    'html_url': repo_data['html_url'],
                    'clone_url': repo_data['clone_url'],
                    'size': repo_data['size'],
                    'created_at': repo_data['created_at'],
                    'updated_at': repo_data['updated_at']
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }

def create_github_integration() -> Optional[GitHubIntegration]:
    """Создание экземпляра GitHub интеграции."""
    try:
        if not is_github_available():
            logger.warning("GitHub интеграция не настроена")
            return None
        
        github = GitHubIntegration()
        
        # Тестирование соединения
        test_result = github.test_connection()
        if not test_result['success']:
            logger.error(f"Ошибка подключения к GitHub: {test_result['error']}")
            return None
        
        logger.info(f"GitHub интеграция инициализирована для пользователя {test_result['user']}")
        return github
    
    except Exception as e:
        logger.error(f"Ошибка инициализации GitHub интеграции: {e}")
        return None

def backup_to_github(data: Dict[str, Any], github: GitHubIntegration = None) -> Dict[str, Any]:
    """Быстрое создание резервной копии в GitHub."""
    try:
        if github is None:
            github = create_github_integration()
            if github is None:
                return {
                    'success': False,
                    'error': 'GitHub интеграция недоступна'
                }
        
        # Создание репозитория если не существует
        repo_result = github.create_repository()
        if not repo_result['success'] and not repo_result.get('existing'):
            return repo_result
        
        # Создание резервной копии
        return github.backup_data(data)
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Ошибка создания резервной копии'
        }