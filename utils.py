"""
Utility functions for content processing and analysis.
"""

import re
import requests
import logging
from urllib.parse import urlparse
from typing import List, Optional

logger = logging.getLogger(__name__)

def extract_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    return list(set(urls))  # Remove duplicates

def analyze_url_content(url: str) -> Optional[str]:
    """Analyze URL to determine content type."""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        
        # Video platforms
        video_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'twitch.tv']
        if any(domain.endswith(vd) for vd in video_domains):
            return "Video content"
        
        # Code repositories
        if 'github.com' in domain or 'gitlab.com' in domain or 'bitbucket.org' in domain:
            if '/blob/' in path or any(ext in path for ext in ['.py', '.js', '.java', '.cpp', '.c']):
                return "Code repository/file"
            else:
                return "Code repository"
        
        # Documentation sites
        doc_indicators = ['docs.', 'documentation', 'wiki', 'readme']
        if any(indicator in domain for indicator in doc_indicators):
            return "Documentation"
        
        # Design/mockup platforms
        design_domains = ['figma.com', 'sketch.com', 'adobe.com', 'dribbble.com', 'behance.net']
        if any(domain.endswith(dd) for dd in design_domains):
            return "Design/Mockup"
        
        # Learning platforms
        learning_domains = ['coursera.org', 'udemy.com', 'edx.org', 'codecademy.com', 'freecodecamp.org']
        if any(domain.endswith(ld) for ld in learning_domains):
            return "Educational content"
        
        # Try to get content type from URL response (with timeout)
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            content_type = response.headers.get('content-type', '').lower()
            
            if 'video' in content_type:
                return "Video file"
            elif 'image' in content_type:
                return "Image file"
            elif 'application/pdf' in content_type:
                return "PDF document"
            elif 'text/html' in content_type:
                return "Web page"
            
        except requests.RequestException:
            pass  # Continue with path-based analysis
        
        # File extension analysis
        file_extensions = {
            '.pdf': 'PDF document',
            '.mp4': 'Video file',
            '.avi': 'Video file',
            '.mov': 'Video file',
            '.png': 'Image file',
            '.jpg': 'Image file',
            '.jpeg': 'Image file',
            '.gif': 'Image file',
            '.svg': 'Vector image',
            '.zip': 'Archive file',
            '.tar.gz': 'Archive file',
            '.py': 'Python code',
            '.js': 'JavaScript code',
            '.html': 'HTML file',
            '.css': 'CSS file',
            '.json': 'JSON data',
            '.xml': 'XML data',
            '.md': 'Markdown document'
        }
        
        for ext, description in file_extensions.items():
            if path.endswith(ext):
                return description
        
        return "Web resource"
        
    except Exception as e:
        logger.error(f"Error analyzing URL {url}: {e}")
        return None

def format_resource_list(resources: List[dict], max_items: int = 10) -> str:
    """Format list of resources for display."""
    if not resources:
        return "Нет ресурсов для отображения. / No resources to display."
    
    # Limit the number of items
    limited_resources = resources[:max_items]
    
    formatted_items = []
    for i, resource in enumerate(limited_resources, 1):
        # Format item
        category_emoji = get_category_emoji(resource['category'])
        confidence_text = f" ({resource['confidence']:.1%})" if resource['confidence'] > 0 else ""
        
        item_text = f"{i}. {category_emoji} {resource['category']}{confidence_text}\n"
        item_text += f"   📝 {resource['description'][:50]}{'...' if len(resource['description']) > 50 else ''}\n"
        item_text += f"   🆔 {resource['id']}"
        
        if resource['urls']:
            item_text += f"\n   🔗 {len(resource['urls'])} URL(s)"
        
        formatted_items.append(item_text)
    
    result = "\n\n".join(formatted_items)
    
    if len(resources) > max_items:
        result += f"\n\n... и еще {len(resources) - max_items} ресурсов / and {len(resources) - max_items} more resources"
    
    return result

def get_category_emoji(category: str) -> str:
    """Get emoji for category."""
    emoji_map = {
        'code_examples': '💻',
        'tutorials': '📚',
        'videos': '🎥',
        'mockups': '🎨',
        'documentation': '📖',
        'tools': '🔧',
        'articles': '📰',
        'libraries': '📦',
        'frameworks': '🏗️',
        'other': '📄'
    }
    return emoji_map.get(category, '📄')

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def extract_programming_languages(content: str) -> List[str]:
    """Extract programming languages mentioned in content."""
    languages = {
        'python': ['python', 'py', 'django', 'flask', 'pandas', 'numpy'],
        'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
        'java': ['java', 'spring', 'maven', 'gradle'],
        'cpp': ['c++', 'cpp', 'cxx'],
        'c': ['c programming', ' c '],
        'csharp': ['c#', 'csharp', '.net', 'dotnet'],
        'php': ['php', 'laravel', 'symfony'],
        'ruby': ['ruby', 'rails'],
        'go': ['golang', ' go '],
        'rust': ['rust'],
        'swift': ['swift', 'ios'],
        'kotlin': ['kotlin', 'android'],
        'typescript': ['typescript', 'ts'],
        'html': ['html', 'html5'],
        'css': ['css', 'css3', 'sass', 'scss'],
        'sql': ['sql', 'mysql', 'postgresql', 'sqlite'],
        'shell': ['bash', 'shell', 'zsh'],
        'r': [' r ', 'rstudio'],
        'matlab': ['matlab'],
        'scala': ['scala'],
        'perl': ['perl'],
        'lua': ['lua']
    }
    
    content_lower = content.lower()
    detected_languages = []
    
    for language, keywords in languages.items():
        if any(keyword in content_lower for keyword in keywords):
            detected_languages.append(language)
    
    return detected_languages

def is_code_content(content: str) -> bool:
    """Check if content appears to be code."""
    code_indicators = [
        r'def\s+\w+\s*\(',  # Python functions
        r'function\s+\w+\s*\(',  # JavaScript functions
        r'class\s+\w+\s*[{:]',  # Class definitions
        r'import\s+[\w.]+',  # Import statements
        r'#include\s*<\w+>',  # C/C++ includes
        r'```[\w]*\n',  # Code blocks
        r'public\s+class\s+\w+',  # Java classes
        r'<\w+[^>]*>.*</\w+>',  # HTML tags
        r'{\s*["\w]+\s*:\s*["\w]+.*}',  # JSON-like objects
    ]
    
    return any(re.search(pattern, content, re.IGNORECASE) for pattern in code_indicators)
