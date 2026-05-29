"""
Ugoira 转换工具包
将 Pixiv 的 Ugoira 格式（ZIP 压缩的动画）转换为 MP4、GIF、WebP 格式
"""

__all__ = ['ugoira_to_mp4', 'ugoira_to_gif', 'ugoira_to_webp', 'convert_all_formats']
__version__ = '1.0.0'


from .to_mp4 import ugoira_to_mp4
from .to_gif import ugoira_to_gif
from .to_webp import ugoira_to_webp
from .batch import convert_all_formats
