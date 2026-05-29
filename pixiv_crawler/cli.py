"""命令行接口"""

import argparse
import sys
import os
from pathlib import Path

from .exceptions import PixivDownloader
from .config import Config
from .exceptions import PixivDownloaderError


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Pixiv Downloader - 下载 Pixiv 用户作品",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=""
    )