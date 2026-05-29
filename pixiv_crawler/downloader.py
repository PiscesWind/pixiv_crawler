import os
import re
import time
import zipfile
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable, Set
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

from pixivpy3 import AppPixivAPI, ByPassSniApi

from .ugoira_unpack import convert_all_formats

from .config import Config
from .exceptions import (
    AuthenticationError,
    InvalidURLException,
    APIError,
    TokenExpiredError,
    DownloadError,
)
from .utils import (
    sanitize_filename,
    format_date,
    extract_user_id_from_url,
    save_token_cache,
    load_token_cache,
)


class PixivDownloader:
    """Pixiv 下载器主类"""

    def __init__(
        self,
        refresh_token: str = None,
        config: Config = None,
        use_bypass_sni: bool = False,
    ):
        """
        初始化下载器

        Args:
            refresh_token: Pixiv refresh_token，如果不提供则从环境变量读取
            config: 配置对象，如果不提供则使用默认配置
            use_bypass_sni: 是否使用绕过SNI的API（用于网络限制环境）
        """
        self.config = config or Config.from_env()

        if not refresh_token and self.config.refresh_token:
            refresh_token = self.config.refresh_token

        if not refresh_token:
            refresh_token = os.environ.get("PIXIV_REFRESH_TOKEN")
            if not refresh_token:
                raise AuthenticationError(
                    "请提供 refresh_token 或设置环境变量 PIXIV_REFRESH_TOKEN"
                )

        self.refresh_token = refresh_token
        self.use_bypass_sni = use_bypass_sni
        self.access_token = None
        self.token_expire_time = None

        # 初始化API
        self._init_api()

        # 认证
        self._authenticate()

        # 创建主下载目录
        self.base_download_dir = self.config.path.base_download_dir
        self.base_download_dir.mkdir(exist_ok=True)

    def _init_api(self):
        """初始化API对象"""
        if self.use_bypass_sni:
            self.api = ByPassSniApi()
            self.api.require_appapi_ph = False
        else:
            self.api = AppPixivAPI()
        self.api.set_accept_language(self.config.language)

    def _authenticate(self):
        """认证并获取access_token"""
        # 尝试从缓存加载token
        if self.config.path.token_cache_file:
            cache_data = load_token_cache(self.config.path.token_cache_file)
            if cache_data and cache_data["refresh_token"] == self.refresh_token:
                # 检查token是否过期
                if datetime.now() < cache_data["expire_time"]:
                    print("从缓存加载access_token成功")
                    self.access_token = cache_data["access_token"]
                    self.token_expire_time = cache_data["expire_time"]
                    self.api.set_authentication(self.access_token)
                    return

        # 重新认证
        print("正在进行 Pixiv API 认证...")
        try:
            auth_result = self.api.auth(refresh_token=self.refresh_token)
            self.access_token = auth_result["access_token"]
            # 通常access_token有效期为3600秒
            self.token_expire_time = datetime.now() + timedelta(seconds=3600)

            # 保存到缓存
            if self.config.path.token_cache_file:
                save_token_cache(
                    self.config.path.token_cache_file,
                    self.refresh_token,
                    self.access_token,
                    self.token_expire_time,
                )

            print("认证成功！")
        except Exception as e:
            raise AuthenticationError(f"认证失败：{e}")

    def _check_and_refresh_token(self):
        """检查并刷新token"""
        if not self.config.download.auto_refresh_token:
            return

        # 检查token是否即将过期
        if self.token_expire_time:
            time_until_expiry = (
                self.token_expire_time - datetime.now()
            ).total_seconds()
            if time_until_expiry < self.config.download.token_refresh_before_expiry:
                print("Access token即将过期，正在刷新...")
                self._refresh_token()

    def _refresh_token(self):
        """刷新access_token"""
        try:
            auth_result = self.api.auth(refresh_token=self.refresh_token)
            self.access_token = auth_result["access_token"]
            self.token_expire_time = datetime.now() + timedelta(seconds=3600)

            # 更新缓存
            if self.config.path.token_cache_file:
                save_token_cache(
                    self.config.path.token_cache_file,
                    self.refresh_token,
                    self.access_token,
                    self.token_expire_time,
                )

            print("Token刷新成功")
        except Exception as e:
            raise TokenExpiredError(f"Token刷新失败：{e}")

    def _api_call_with_retry(self, api_func, *args, **kwargs):
        """带重试机制的API调用"""
        max_retries = self.config.download.max_retries

        for attempt in range(max_retries):
            try:
                result = api_func(*args, **kwargs)

                # 检查API返回的错误
                if result and isinstance(result, dict) and "error" in result:
                    error_msg = result["error"].get("message", "")
                    # 如果是token相关错误，尝试刷新token
                    if "token" in error_msg.lower() or "auth" in error_msg.lower():
                        if attempt < max_retries - 1:
                            print(f"API返回认证错误，尝试刷新token...")
                            self._refresh_token()
                            continue

                return result

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"API调用失败（尝试 {attempt + 1}/{max_retries}）：{e}")
                    print("正在尝试刷新token...")
                    self._refresh_token()
                    time.sleep(2**attempt)  # 指数退避
                else:
                    raise APIError(f"API调用失败：{e}")

        return None

    def _download_with_retry(self, url: str, path: str, fname: str):
        """带重试机制的下载"""
        max_retries = self.config.download.max_retries

        for attempt in range(max_retries):
            try:
                self._check_and_refresh_token()
                self.api.download(url, path=path, fname=fname)
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"下载失败（尝试 {attempt + 1}/{max_retries}）：{e}")
                    print("正在尝试刷新token...")
                    self._refresh_token()
                    time.sleep(2**attempt)
                else:
                    raise DownloadError(f"下载失败：{e}")
        return False

    def _convert_ugoira_to_gif_mp4_webp(
        self, zip_path: Path, work_folder: Path
    ) -> bool:
        """将 ZIP 文件转换为 GIF、MP4 和 WebP"""
        try:
            zip_path_abs = zip_path.absolute()
            work_folder_abs = work_folder.absolute()
            work_folder_abs.mkdir(parents=True, exist_ok=True)

            converted = convert_all_formats(
                zip_path_abs, work_folder_abs, webp_quality=self.config.webp_quality
            )
            print(f"    动图转换完成：{converted}")

            return True

        except Exception as e:
            print(f"    动图转换失败：{e}")
            return False

    def _get_author_info(self, user_id: str) -> Tuple[str, str]:
        """获取作者信息"""
        try:
            user_detail = self._api_call_with_retry(self.api.user_detail, user_id)
            user_name = user_detail["user"]["name"]
            return sanitize_filename(user_name), user_id
        except Exception as e:
            print(f"获取作者信息失败：{e}")
            return f"user_{user_id}", user_id

    def download_single_illust(self, illust_id: str, author_folder: Path) -> bool:
        """下载单个作品"""
        print(f"\n开始处理作品: {illust_id}")

        try:
            illust_detail = self._api_call_with_retry(self.api.illust_detail, illust_id)
            if "error" in illust_detail:
                print(
                    f"  获取作品详情失败：{illust_detail['error'].get('message', 'Unknown error')}"
                )
                return False

            illust_info = illust_detail["illust"]

            title = sanitize_filename(illust_info["title"])
            if not title:
                title = f"Untitled_{illust_id}"

            create_date_str = format_date(illust_info["create_date"])

            work_folder_name = f"{create_date_str} {title} ({illust_id})"
            work_folder = author_folder / work_folder_name
            work_folder.mkdir(parents=True, exist_ok=True)

            hd_folder = work_folder / "HDP"
            hd_folder.mkdir(exist_ok=True)

            print(f"  标题：{title}")
            print(f"  日期：{create_date_str}")
            print(
                f"  类型：{'多图' if illust_info.get('page_count', 1) > 1 else '单图'}"
            )

            illust_type = illust_info.get("type")

            if illust_type == "ugoira":
                return self._download_ugoira(illust_id, work_folder, hd_folder)
            else:
                return self._download_regular_images(
                    illust_info, work_folder, hd_folder
                )

        except Exception as e:
            print(f"  处理作品 {illust_id} 时发生错误：{e}")
            return False

    def _download_ugoira(
        self, illust_id: str, work_folder: Path, hd_folder: Path
    ) -> bool:
        """下载动图作品"""
        print(f"  检测到动图作品，将下载并转换为 GIF/MP4/WEBP...")

        ugoira_metadata = self._api_call_with_retry(self.api.ugoira_metadata, illust_id)
        if "error" in ugoira_metadata:
            print(
                f"  获取动图信息失败：{ugoira_metadata.get('error', {}).get('message', 'Unknown')}"
            )
            return False

        zip_url = ugoira_metadata["ugoira_metadata"]["zip_urls"]["medium"]
        zip_filename = f"{illust_id}_ugoira.zip"
        zip_path = hd_folder / zip_filename

        frame_delays = []
        if (
            "ugoira_metadata" in ugoira_metadata
            and "frames" in ugoira_metadata["ugoira_metadata"]
        ):
            for frame in ugoira_metadata["ugoira_metadata"]["frames"]:
                frame_delays.append(frame.get("delay", 100))
            print(f"    获取到 {len(frame_delays)} 帧的延迟信息")

        if not zip_path.exists():
            print(f"  正在下载动图包：{zip_filename}")
            try:
                self._download_with_retry(zip_url, str(hd_folder), zip_filename)
                print(f"  下载完成：{zip_filename}")
                time.sleep(self.config.download.download_interval)
            except Exception as e:
                print(f"  下载动图包失败：{e}")
                return False
        else:
            print(f"  动图包已存在，跳过下载：{zip_filename}")

        self._ensure_animation_json(zip_path, frame_delays, hd_folder, illust_id)

        print(f"  正在将动图转换为 GIF 和 MP4 和 WebP ...")
        self._convert_ugoira_to_gif_mp4_webp(zip_path, work_folder)

        return True

    def _ensure_animation_json(
        self, zip_path: Path, frame_delays: List[int], hd_folder: Path, illust_id: str
    ):
        """确保ZIP包包含animation.json文件"""
        has_animation = False
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                if "animation.json" in zf.namelist():
                    has_animation = True
                    print(f"    ZIP 包中包含 animation.json")
        except Exception as e:
            print(f"    检查 ZIP 包时出错：{e}")

        if not has_animation:
            print(f"    ZIP 包中没有 animation.json，正在创建...")
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    with zipfile.ZipFile(zip_path, "r") as zf:
                        zf.extractall(temp_path)

                    image_files = []
                    image_files.extend(sorted(temp_path.glob("*.png")))
                    image_files.extend(sorted(temp_path.glob("*.jpg")))
                    image_files.extend(sorted(temp_path.glob("*.jpeg")))

                    if image_files:
                        if not frame_delays:
                            frame_delays = [100] * len(image_files)

                        if len(frame_delays) < len(image_files):
                            last_delay = frame_delays[-1] if frame_delays else 100
                            frame_delays.extend(
                                [last_delay] * (len(image_files) - len(frame_delays))
                            )
                        elif len(frame_delays) > len(image_files):
                            frame_delays = frame_delays[: len(image_files)]

                        animation_data = {
                            "frames": [
                                {"file": f.name, "delay": frame_delays[i]}
                                for i, f in enumerate(image_files)
                            ]
                        }

                        animation_path = temp_path / "animation.json"
                        with open(animation_path, "w", encoding="utf-8") as f:
                            json.dump(animation_data, f, ensure_ascii=False, indent=2)

                        new_zip_path = (
                            hd_folder / f"{illust_id}_ugoira_with_animation.zip"
                        )
                        with zipfile.ZipFile(new_zip_path, "w") as zf:
                            for file_path in temp_path.iterdir():
                                zf.write(file_path, file_path.name)

                        zip_path.unlink()
                        new_zip_path.rename(zip_path)
                        print(
                            f"    已创建并添加 animation.json 到 ZIP 包（{len(image_files)} 帧）"
                        )
            except Exception as e:
                print(f"    创建 animation.json 失败：{e}")

    def _download_regular_images(
        self, illust_info: dict, work_folder: Path, hd_folder: Path
    ) -> bool:
        """下载普通图片"""
        image_urls = []
        page_count = illust_info.get("page_count", 1)
        meta_pages = illust_info.get("meta_pages", [])

        if page_count == 1 or not meta_pages:
            original_url = illust_info["meta_single_page"]["original_image_url"]
            preview_url = original_url.replace("img-original", "img-master")
            preview_url = re.sub(r"(_p0)(\.\w+)$", r"\1_master1200\2", preview_url)

            orig_filename = os.path.basename(original_url.split("?")[0])
            preview_filename = os.path.basename(preview_url.split("?")[0])

            image_urls.append((preview_url, preview_filename, False))
            image_urls.append((original_url, orig_filename, True))
        else:
            for page in meta_pages:
                original_url = page["image_urls"]["original"]
                preview_url = page["image_urls"].get("large", "")
                if not preview_url or "master1200" not in preview_url:
                    preview_url = original_url.replace("img-original", "img-master")
                    preview_url = re.sub(
                        r"(_p\d+)(\.\w+)$", r"\1_master1200\2", preview_url
                    )

                orig_filename = os.path.basename(original_url.split("?")[0])
                preview_filename = os.path.basename(preview_url.split("?")[0])

                image_urls.append((preview_url, preview_filename, False))
                image_urls.append((original_url, orig_filename, True))

        if not image_urls:
            print(f"  未找到可下载的资源")
            return False

        for url, filename, is_hd in image_urls:
            save_folder = hd_folder if is_hd else work_folder
            save_path = save_folder / filename

            if save_path.exists():
                print(f"  文件已存在，跳过：{filename}")
                continue

            print(f"  正在下载：{filename} ({'高清' if is_hd else '预览'})")
            try:
                self._download_with_retry(url, str(save_folder), filename)
                print(f"  下载完成：{filename}")
                time.sleep(self.config.download.download_interval)
            except Exception as e:
                print(f"  下载失败：{e}")

        return True

    def get_author_artworks(self, author_url: str, mode: str = "B1") -> List[str]:
        """
        获取作者的作品ID列表

        Args:
            author_url: 作者主页URL
            mode: B1=爬取作者所有作品，B2=爬取作者的作品中用户喜欢的作品
        """
        # 提取作者ID（B1模式下的目标作者，或B2模式下登录用户的ID）
        author_id = extract_user_id_from_url(author_url)
        if not author_id:
            raise InvalidURLException(f"无法从URL '{author_url}' 中提取作者ID")

        print(f"目标作者ID: {author_id}")

        if mode == "B1":
            # B1: 下载作者所有的作品
            return self._get_user_illusts(author_id)
        elif mode == "B2":
            # B2: 下载当前登录用户喜欢的指定用户的作品
            return self._get_user_bookmarks_of_target(author_id)
        else:
            print(f"错误：未知模式 {mode}，使用默认模式 B1")
            return self._get_user_illusts(author_id)

    def _get_user_illusts(self, user_id: str) -> List[str]:
        """B1模式：获取用户发布的所有作品"""
        print("模式 B1: 获取用户发布的所有作品")
        all_illust_ids = []
        next_qs = None
        page_num = 1

        while True:
            print(f"正在获取第 {page_num} 页...")
            try:
                if next_qs:
                    if "user_id" in next_qs:
                        del next_qs["user_id"]
                    json_result = self._api_call_with_retry(
                        self.api.user_illusts, user_id, req_auth=True, **next_qs
                    )
                else:
                    json_result = self._api_call_with_retry(
                        self.api.user_illusts, user_id, req_auth=True
                    )

                if "error" in json_result:
                    print(
                        f"API 返回错误：{json_result['error'].get('message', 'Unknown')}"
                    )
                    break

                illusts = json_result.get("illusts", [])
                if not illusts:
                    break

                for illust in illusts:
                    all_illust_ids.append(str(illust["id"]))

                print(
                    f"第 {page_num} 页获取到 {len(illusts)} 个作品，累计 {len(all_illust_ids)} 个"
                )

                next_url = json_result.get("next_url")
                if not next_url:
                    break

                parsed = urlparse(next_url)
                next_qs = parse_qs(parsed.query)
                next_qs = {k: v[0] if len(v) == 1 else v for k, v in next_qs.items()}
                next_qs.pop("user_id", None)

                page_num += 1
                time.sleep(self.config.download.page_interval)

            except Exception as e:
                print(f"获取作品列表时发生错误：{e}")
                break

        return all_illust_ids

    def _get_user_bookmarks_of_target(self, author_id: str) -> List[str]:
        """
        B2模式：获取当前登录用户喜欢的指定用户的作品
        Args:
            author_id: 要下载其作品的作者ID
        """
        print(
            f"模式 B2: 获取用户 {self.api.user_name}({self.api.user_id}) 喜欢的作者 {author_id} 的作品"
        )

        all_illust_ids = []
        next_qs = None
        page_num = 1
        seen_illusts = set()  # 用于去重

        while True:
            print(f"正在获取第 {page_num} 页收藏列表...")
            try:
                if next_qs:
                    if "user_id" in next_qs:
                        del next_qs["user_id"]
                    json_result = self._api_call_with_retry(
                        self.api.user_bookmarks_illusts,
                        self.api.user_id,
                        req_auth=True,
                        **next_qs,
                    )
                else:
                    json_result = self._api_call_with_retry(
                        self.api.user_bookmarks_illusts, self.api.user_id, req_auth=True
                    )

                if "error" in json_result:
                    print(
                        f"API 返回错误：{json_result['error'].get('message', 'Unknown')}"
                    )
                    break

                illusts = json_result.get("illusts", [])
                if not illusts:
                    print("没有更多收藏作品")
                    break

                # 过滤出指定用户的作品
                page_match_count = 0
                for illust in illusts:
                    illust_id = str(illust["id"])
                    illust_user_id = str(illust["user"]["id"])

                    if illust_user_id == author_id and illust_id not in seen_illusts:
                        all_illust_ids.append(illust_id)
                        seen_illusts.add(illust_id)
                        page_match_count += 1

                print(
                    f"第 {page_num} 页获取到 {len(illusts)} 个收藏，其中匹配目标用户的有 {page_match_count} 个，累计 {len(all_illust_ids)} 个"
                )

                next_url = json_result.get("next_url")
                if not next_url:
                    break

                parsed = urlparse(next_url)
                next_qs = parse_qs(parsed.query)
                next_qs = {k: v[0] if len(v) == 1 else v for k, v in next_qs.items()}
                next_qs.pop("user_id", None)

                page_num += 1
                time.sleep(self.config.download.page_interval)

            except Exception as e:
                print(f"获取收藏列表时发生错误：{e}")
                break

        print(f"\n共找到 {len(all_illust_ids)} 个用户 {author_id} 的作品被当前用户收藏")
        return all_illust_ids

    def download_author_works(
        self,
        author_url: str,
        mode: str = "B1",
        max_works: int = None,
        callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, int]:
        """
        下载指定用户的作品

        Args:
            author_url: 作者主页URL
            mode: B1=下载作者自己的作品，B2=下载作者的作品中用户喜欢的作品
            max_works: 最大下载数量，None表示全部下载
            callback: 进度回调函数

        Returns:
            Dict: 包含成功和失败数量的字典
        """

        author_id = extract_user_id_from_url(author_url)
        if not author_id:
            raise InvalidURLException(f"无法从URL提取作者ID")

        author_name, _ = self._get_author_info(author_id)
        author_folder_name = f"{author_name}（{author_id}）"
        author_folder = self.base_download_dir / author_folder_name
        author_folder.mkdir(exist_ok=True)
        print(f"\n作者文件夹：{author_folder_name}")

        if mode == "B1":
            print(f"模式 B1: 获取作者 {author_name}({author_id}) 的作品")

        if mode == "B2":
            print(
                f"模式 B2: 获取作者 {author_name}({author_id}) 作品中{self.api.user_name}({self.api.user_id}) 喜欢的作品"
            )

        illust_ids = self.get_author_artworks(author_url, mode)

        if not illust_ids:
            print("未获取到任何作品")
            return {"success": 0, "failed": 0}

        print(f"\n共获取到 {len(illust_ids)} 个作品，开始下载...")

        if max_works and max_works > 0:
            illust_ids = illust_ids[:max_works]
            print(f"限制下载数量为 {max_works} 个")

        success_count = 0
        for idx, illust_id in enumerate(illust_ids, 1):
            print(f"\n进度: [{idx}/{len(illust_ids)}]")

            if callback:
                callback(idx, len(illust_ids), illust_id)

            if self.download_single_illust(illust_id, author_folder):
                success_count += 1

            # 每下载10个作品检查一次token（如果设置了自动刷新）
            if idx % 10 == 0:
                self._check_and_refresh_token()

        failed_count = len(illust_ids) - success_count
        print(
            f"\n下载完成！成功：{success_count}/{len(illust_ids)}，失败：{failed_count}"
        )

        return {"success": success_count, "failed": failed_count}

    def get_user_info(self, user_id: str) -> Dict:
        """获取用户信息"""
        try:
            user_detail = self._api_call_with_retry(self.api.user_detail, user_id)
            return {
                "id": user_id,
                "name": user_detail["user"]["name"],
                "account": user_detail["user"]["account"],
                "comment": user_detail["user"].get("comment", ""),
                "profile_img": user_detail["user"]["profile_image_urls"].get(
                    "medium", ""
                ),
            }
        except Exception as e:
            raise APIError(f"获取用户信息失败：{e}")

    def set_download_interval(self, interval: float):
        """设置下载间隔 （单位：秒）"""
        self.config.download.download_interval = interval

    def set_base_directory(self, directory: str):
        """设置下载目录"""
        self.config.path.base_download_dir = Path(directory)
        self.config.path.base_download_dir.mkdir(exist_ok=True)
