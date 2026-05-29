# Pixiv Crawler

一个基于 Python 的 Pixiv 作品下载器，支持下载插画、多图作品及动图（Ugoira），并可将动图自动转换为 GIF / MP4 / WebP 格式。

## 快速开始

```python
import pixiv_crawler

crawler = pixiv_crawler.PixivDownloader("你的refresh_token")

# B1 模式：下载作者的所有作品
crawler.download_author_works("https://www.pixiv.net/users/作者ID")

# B2 模式：下载当前登录用户收藏中指定作者的作品
crawler.download_author_works("https://www.pixiv.net/users/作者ID", mode="B2")

# 下载单个作品（参数为作品ID）
crawler.download_single_illust("作品ID", author_folder)
```

### 模式说明

| 模式 | 功能 |
|------|------|
| **B1** | 下载指定作者发布的所有作品 |
| **B2** | 下载当前登录用户收藏中，属于指定作者的作品 |

## 依赖

- **Python 库**：[pixivpy3](https://github.com/upbit/pixivpy) — Pixiv API 封装
- **系统工具**：[FFmpeg](https://ffmpeg.org/) — 用于动图（Ugoira）转换为 MP4 / GIF / WebP

### FFmpeg 安装

1. 下载 FFmpeg：[https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. 解压后将 `bin` 目录添加到系统环境变量 PATH 中
3. 在命令行输入 `ffmpeg -version` 验证安装

> ⚠️ **注意**：如果没有安装 FFmpeg，动图（Ugoira）只会下载为原始 ZIP 格式，**不会影响其他图片的下载**。

## 获取 Refresh Token

Refresh Token 可通过 [pixiv-token](https://github.com/piglig/pixiv-token) 项目获取。

### 推荐用法

```bash
# 有窗口模式（方便通过浏览器的人机验证）
python pixiv_token_fetcher.py -u "你的邮箱" -p "你的密码" --no-headless
```

建议修改脚本中的限制时长，方便通过浏览器的人机验证：

```python
# 在 pixiv_token_fetcher.py 中查找并修改以下参数
TYPING_DELAY = 0.5  # 输入延迟（秒），可适当增大
PAGE_WAIT = 3       # 页面等待时间（秒），可适当增大
```
