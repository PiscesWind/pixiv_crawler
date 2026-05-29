import pixiv_crawler

if __name__ == "__main__":
    print(f"Pixiv Crawler version: {pixiv_crawler.__version__}")
    pixiv_crawler = pixiv_crawler.PixivDownloader("refresh_token")
    pixiv_crawler.download_author_works("https://www.pixiv.net/users/作者ID")
    # pixiv_crawler.download_author_works("https://www.pixiv.net/users/作者ID", mode="B2")
