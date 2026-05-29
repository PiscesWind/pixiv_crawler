"""
Pixiv Downloader - 一个用于下载 Pixiv 作品的 Python 包
"""

__version__ = "1.0.0"
__author__ = "PiscesWind"
__all__ = [
    "PixivDownloader",
    "PixivDownloaderError",
    "AuthenticationError", 
    "DownloadError",
    "UserNotFoundError"
]

from .downloader import PixivDownloader
from .exceptions import (
    PixivDownloaderError,
    AuthenticationError,
    DownloadError,
    UserNotFoundError
)
