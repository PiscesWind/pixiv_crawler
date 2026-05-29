"""自定义异常类"""


class PixivDownloaderError(Exception):
    """Pixiv下载器基础异常"""
    pass


class AuthenticationError(PixivDownloaderError):
    """认证相关异常"""
    pass


class DownloadError(PixivDownloaderError):
    """下载相关异常"""
    pass


class UserNotFoundError(PixivDownloaderError):
    """用户未找到异常"""
    pass


class InvalidURLException(PixivDownloaderError):
    """无效URL异常"""
    pass


class APIError(PixivDownloaderError):
    """API调用异常"""
    pass


class TokenExpiredError(PixivDownloaderError):
    """Token过期异常"""
    pass