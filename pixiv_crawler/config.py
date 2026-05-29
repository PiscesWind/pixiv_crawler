"""配置管理模块"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime


@dataclass
class DownloadConfig:
    """下载配置"""
    download_interval: float = 3.0  # 下载间隔（秒）
    page_interval: float = 0.3  # 翻页间隔（秒）
    max_retries: int = 3  # 最大重试次数
    timeout: int = 30  # 请求超时时间
    auto_refresh_token: bool = False  # 是否自动刷新token
    token_refresh_before_expiry: int = 3600  # token过期前多久刷新（秒）


@dataclass
class PathConfig:
    """路径配置"""
    base_download_dir: Path = field(default_factory=lambda: Path("pixiv_downloads"))
    temp_dir: Optional[Path] = None
    token_cache_file: Optional[Path] = None
    
    def __post_init__(self):
        self.base_download_dir.mkdir(exist_ok=True)
        if self.temp_dir:
            self.temp_dir.mkdir(exist_ok=True)
        if self.token_cache_file:
            self.token_cache_file.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class Config:
    """全局配置"""
    download: DownloadConfig = field(default_factory=DownloadConfig)
    path: PathConfig = field(default_factory=PathConfig)
    language: str = "zh-CN"
    refresh_token: Optional[str] = None
    webp_quality: int = 100  # WebP质量（0-100）
    
    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        refresh_token = os.environ.get("PIXIV_REFRESH_TOKEN")
        return cls(refresh_token=refresh_token)
    
    def update_download_interval(self, interval: float):
        """更新下载间隔"""
        self.download.download_interval = interval
    
    def update_base_directory(self, directory: str | Path):
        """更新基础下载目录"""
        self.path.base_download_dir = Path(directory)
        self.path.base_download_dir.mkdir(exist_ok=True)
    
    def set_token_cache(self, cache_file: str | Path):
        """设置token缓存文件"""
        self.path.token_cache_file = Path(cache_file)