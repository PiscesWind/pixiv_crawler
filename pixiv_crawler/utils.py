"""辅助工具函数"""

import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    if not name:
        return "untitled"
    clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return clean[:255] if len(clean) > 255 else clean


def format_date(date_str: str, format_str: str = "%y-%m-%d") -> str:
    """格式化日期字符串"""
    try:
        if date_str.endswith("+00:00"):
            date_str = date_str.replace("+00:00", "")
        create_date = datetime.fromisoformat(date_str)
        return create_date.strftime(format_str)
    except (ValueError, TypeError):
        return "unknown_date"


def extract_user_id_from_url(url: str) -> Optional[str]:
    """从URL中提取用户ID"""
    patterns = [
        r"users/(\d+)",
        r"users\\(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_illust_id_from_url(url: str) -> Optional[str]:
    """从URL中提取作品ID"""
    patterns = [
        r"/artworks/(\d+)",
        r"pixiv\.net/artworks/(\d+)",
        r"www\.pixiv\.net/artworks/(\d+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_file_extension(url: str) -> str:
    """从URL获取文件扩展名"""
    url_path = url.split("?")[0]
    ext = Path(url_path).suffix.lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.zip']:
        return ext
    return '.jpg'


def ensure_directory(path: Path) -> Path:
    """确保目录存在"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def truncate_string(s: str, max_length: int = 100) -> str:
    """截断字符串"""
    if len(s) <= max_length:
        return s
    return s[:max_length-3] + "..."


def save_token_cache(cache_file: Path, refresh_token: str, access_token: str, expire_time: datetime):
    """保存token到缓存文件"""
    cache_data = {
        "refresh_token": refresh_token,
        "access_token": access_token,
        "expire_time": expire_time.isoformat()
    }
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)


def load_token_cache(cache_file: Path) -> Optional[Dict[str, Any]]:
    """从缓存文件加载token"""
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['expire_time'] = datetime.fromisoformat(data['expire_time'])
        return data
    except Exception:
        return None