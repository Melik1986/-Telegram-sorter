#!/usr/bin/env python3
"""
Web interface for DevDataSorter bot management.
Provides a simple web dashboard for monitoring and managing the bot.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from src.utils.storage import ResourceStorage
from src.utils.cache import get_cache_manager
from scripts.backup import get_backup_manager
from src.utils.rate_limiter import get_rate_limiter, get_command_rate_limiter
from src.handlers.file_handler import get_file_handler
from src.core.config import validate_api_keys, get_security_report
from src.core.classifier import ContentClassifier

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize components
storage = ResourceStorage()
cache = get_cache_manager()
backup = get_backup_manager()
rate_limiter = get_rate_limiter()
command_rate_limiter = get_command_rate_limiter()
file_handler = get_file_handler()
classifier = ContentClassifier()

@app.route('/')
def dashboard():
    """Main dashboard page."""
    # Get statistics
    storage_stats = storage.get_storage_stats()
    cache_stats = cache.get_stats()
    file_stats = file_handler.get_stats()
    
    # Get recent resources
    recent_resources = storage.get_all_resources()[-10:]  # Last 10 resources
    
    # Get categories
    categories = storage.get_categories()
    
    return render_template('dashboard.html', 
                         storage_stats=storage_stats,
                         cache_stats=cache_stats,
                         file_stats=file_stats,
                         recent_resources=recent_resources,
                         categories=categories)

@app.route('/resources')
def resources():
    """Resources management page."""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    search_query = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    per_page = 20
    
    if search_query:
        resources_list = storage.search_resources(
            search_query, 
            category_filter=category if category else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None
        )
    elif category or date_from or date_to:
        # Get all resources and apply filters
        all_resources = storage.get_all_resources()
        resources_list = storage._apply_filters(
            all_resources, 
            category_filter=category if category else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None
        )
    else:
        resources_list = storage.get_all_resources()
    
    # Simple pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_resources = resources_list[start:end]
    
    total_pages = (len(resources_list) + per_page - 1) // per_page
    
    categories = storage.get_categories()
    
    return render_template('resources.html',
                         resources=paginated_resources,
                         categories=categories,
                         current_page=page,
                         total_pages=total_pages,
                         current_category=category,
                         search_query=search_query,
                         date_from=date_from,
                         date_to=date_to)

@app.route('/api/resources/<resource_id>', methods=['DELETE'])
def delete_resource(resource_id):
    """Delete a resource via API."""
    try:
        success = storage.delete_resource(resource_id)
        if success:
            return jsonify({'success': True, 'message': 'Resource deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Resource not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/cache')
def cache_management():
    """Cache management page."""
    stats = cache.get_stats()
    return render_template('cache.html', stats=stats)

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear cache via API."""
    try:
        cache.clear()
        return jsonify({'success': True, 'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/backups')
def backup_management():
    """Backup management page."""
    try:
        backups = backup.list_backups()
        return render_template('backups.html', backups=backups)
    except Exception as e:
        flash(f'Error loading backups: {str(e)}', 'error')
        return render_template('backups.html', backups=[])

@app.route('/api/backup/create', methods=['POST'])
def create_backup():
    """Create backup via API."""
    try:
        def get_data():
            return {
                'resources': storage.get_all_resources(),
                'categories': storage.get_categories()
            }
        
        backup_path = backup.create_backup(get_data)
        return jsonify({'success': True, 'message': f'Backup created: {backup_path}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/backup/restore/<backup_name>', methods=['POST'])
def restore_backup(backup_name):
    """Restore backup via API."""
    try:
        backup.restore_backup(backup_name)
        return jsonify({'success': True, 'message': f'Backup {backup_name} restored'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/security')
def security_page():
    """Security and API keys management page."""
    validation = validate_api_keys()
    security_report = get_security_report()
    
    return render_template('security.html', 
                         validation=validation,
                         security_report=security_report)

@app.route('/api/classify', methods=['POST'])
def classify_content():
    """Classify content via API."""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if not content:
            return jsonify({'success': False, 'error': 'Content is required'}), 400
        
        result = classifier.classify_content(content)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_resource', methods=['POST'])
def add_resource():
    """Add resource via API."""
    try:
        data = request.get_json()
        content = data.get('content', '')
        category = data.get('category', '')
        description = data.get('description', '')
        
        if not content:
            return jsonify({'success': False, 'error': 'Content is required'}), 400
        
        # Classify if category not provided
        if not category:
            classification = classifier.classify_content(content)
            category = classification.get('category', 'general')
        
        resource_id = storage.add_resource(
            content=content,
            category=category,
            user_id=0,  # Web interface user
            username='web_user',
            description=description,
            source='web_interface'
        )
        
        return jsonify({
            'success': True, 
            'message': 'Resource added successfully',
            'resource_id': resource_id,
            'category': category
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def api_search():
    """Search resources via API with filters."""
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        use_semantic = request.args.get('semantic', 'true').lower() == 'true'
        
        if not query:
            return jsonify({'success': False, 'error': 'Query parameter is required'}), 400
        
        results = storage.search_resources(
            query,
            use_semantic=use_semantic,
            category_filter=category if category else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Get all statistics via API."""
    try:
        return jsonify({
            'storage': storage.get_storage_stats(),
            'cache': cache.get_stats(),
            'file_handler': file_handler.get_stats(),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_templates():
    """Create HTML templates for the web interface."""
    templates_dir = 'templates'
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    # Base template
    base_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}DevDataSorter Dashboard{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="fas fa-robot"></i> DevDataSorter
            </a>
            <div class="navbar-nav">
                <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="nav-link" href="{{ url_for('resources') }}">Resources</a>
                <a class="nav-link" href="{{ url_for('cache_management') }}">Cache</a>
                <a class="nav-link" href="{{ url_for('backup_management') }}">Backups</a>
                <a class="nav-link" href="{{ url_for('security_page') }}">Security</a>
            </div>
        </div>
    </nav>
    
    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
    '''
    
    with open(os.path.join(templates_dir, 'base.html'), 'w', encoding='utf-8') as f:
        f.write(base_template)
    
    # Dashboard template
    dashboard_template = '''
{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title">Resources</h5>
                <h2 class="text-primary">{{ storage_stats.total_resources }}</h2>
                <p class="text-muted">Total stored</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title">Categories</h5>
                <h2 class="text-success">{{ storage_stats.total_categories }}</h2>
                <p class="text-muted">Active categories</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title">Cache</h5>
                <h2 class="text-info">{{ cache_stats.total_items }}</h2>
                <p class="text-muted">Cached items</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title">Files</h5>
                <h2 class="text-warning">{{ file_stats.total_processed }}</h2>
                <p class="text-muted">Files processed</p>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5>Recent Resources</h5>
            </div>
            <div class="card-body">
                {% if recent_resources %}
                    <div class="list-group">
                        {% for resource in recent_resources %}
                            <div class="list-group-item">
                                <div class="d-flex w-100 justify-content-between">
                                    <h6 class="mb-1">{{ resource.content[:100] }}...</h6>
                                    <small class="text-muted">{{ resource.category }}</small>
                                </div>
                                {% if resource.description %}
                                    <p class="mb-1">{{ resource.description[:150] }}...</p>
                                {% endif %}
                            </div>
                        {% endfor %}
                    </div>
                {% else %}
                    <p class="text-muted">No resources found</p>
                {% endif %}
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5>Categories</h5>
            </div>
            <div class="card-body">
                {% if categories %}
                    {% for category, count in categories.items() %}
                        <div class="d-flex justify-content-between">
                            <span>{{ category }}</span>
                            <span class="badge bg-primary">{{ count }}</span>
                        </div>
                    {% endfor %}
                {% else %}
                    <p class="text-muted">No categories found</p>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
    '''
    
    with open(os.path.join(templates_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(dashboard_template)
    
    # Resources template with filters
    resources_template = '''
{% extends "base.html" %}
{% block title %}Resources - DevDataSorter{% endblock %}
{% block content %}
<div class="container mt-4">
    <h1><i class="fas fa-database"></i> Resources</h1>
    
    <!-- Filters -->
    <div class="card mb-4">
        <div class="card-header">
            <h5><i class="fas fa-filter"></i> Filters</h5>
        </div>
        <div class="card-body">
            <form method="GET" action="{{ url_for('resources') }}">
                <div class="row">
                    <div class="col-md-4">
                        <label for="search" class="form-label">Search Query</label>
                        <input type="text" class="form-control" id="search" name="search" 
                               value="{{ search_query }}" placeholder="Enter search terms...">
                    </div>
                    <div class="col-md-2">
                        <label for="category" class="form-label">Category</label>
                        <select class="form-select" id="category" name="category">
                            <option value="">All Categories</option>
                            {% for cat in categories %}
                                <option value="{{ cat }}" {% if cat == current_category %}selected{% endif %}>
                                    {{ cat }}
                                </option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label for="date_from" class="form-label">Date From</label>
                        <input type="date" class="form-control" id="date_from" name="date_from" 
                               value="{{ date_from }}">
                    </div>
                    <div class="col-md-2">
                        <label for="date_to" class="form-label">Date To</label>
                        <input type="date" class="form-control" id="date_to" name="date_to" 
                               value="{{ date_to }}">
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
                        <button type="submit" class="btn btn-primary me-2">
                            <i class="fas fa-search"></i> Filter
                        </button>
                        <a href="{{ url_for('resources') }}" class="btn btn-secondary">
                            <i class="fas fa-times"></i> Clear
                        </a>
                    </div>
                </div>
            </form>
        </div>
    </div>
    
    <!-- Resources List -->
    <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5>Resources ({{ resources|length }} found)</h5>
            <button class="btn btn-success btn-sm" data-bs-toggle="modal" data-bs-target="#addResourceModal">
                <i class="fas fa-plus"></i> Add Resource
            </button>
        </div>
        <div class="card-body">
            {% if resources %}
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Content</th>
                                <th>Category</th>
                                <th>Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for resource in resources %}
                                <tr>
                                    <td>
                                        <div class="fw-bold">{{ resource.content[:100] }}...</div>
                                        {% if resource.description %}
                                            <small class="text-muted">{{ resource.description[:150] }}...</small>
                                        {% endif %}
                                    </td>
                                    <td><span class="badge bg-info">{{ resource.category }}</span></td>
                                    <td>{{ resource.timestamp }}</td>
                                    <td>
                                        <button class="btn btn-danger btn-sm" 
                                                onclick="deleteResource('{{ resource.id }}')">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                
                <!-- Pagination -->
                {% if total_pages > 1 %}
                    <nav aria-label="Page navigation">
                        <ul class="pagination justify-content-center">
                            {% for page_num in range(1, total_pages + 1) %}
                                <li class="page-item {% if page_num == current_page %}active{% endif %}">
                                    <a class="page-link" href="{{ url_for('resources', page=page_num, 
                                       category=current_category, search=search_query, 
                                       date_from=date_from, date_to=date_to) }}">
                                        {{ page_num }}
                                    </a>
                                </li>
                            {% endfor %}
                        </ul>
                    </nav>
                {% endif %}
            {% else %}
                <div class="text-center py-4">
                    <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">No resources found</h5>
                    <p class="text-muted">Try adjusting your filters or add some resources.</p>
                </div>
            {% endif %}
        </div>
    </div>
</div>

<script>
function deleteResource(resourceId) {
    if (confirm('Are you sure you want to delete this resource?')) {
        fetch(`/api/resources/${resourceId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error deleting resource: ' + data.error);
            }
        })
        .catch(error => {
            alert('Error deleting resource: ' + error);
        });
    }
}
</script>
{% endblock %}
    '''
    
    with open(os.path.join(templates_dir, 'resources.html'), 'w', encoding='utf-8') as f:
        f.write(resources_template)

def run_web_interface(host='127.0.0.1', port=5000, debug=True):
    """Run the web interface."""
    create_templates()
    print(f"🌐 Starting web interface at http://{host}:{port}")
    print("📊 Dashboard features:")
    print("  • Resource management")
    print("  • Cache monitoring")
    print("  • Backup management")
    print("  • Security monitoring")
    print("  • API endpoints")
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_web_interface()