import zipfile
import json
import tempfile
import os

def find_json(tmpdir: str) -> str:
    """在临时目录中查找 JSON 文件"""
    for root, dirs, files in os.walk(tmpdir):
        for file in files:
            if file in ["animation.json", "meta.json", "info.json", "timing.json"]:
                return os.path.join(root, file)
    raise FileNotFoundError("ZIP 中没有找到 JSON 文件")

def parse_frames(json_path: str) -> list:
    """解析 JSON 文件，返回帧列表"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif "frames" in data:
        return data["frames"]
    else:
        return []

def create_concat_file(tmpdir: str, json_dir: str, frames: list) -> str:
    """创建 FFmpeg concat 文件，返回文件路径"""
    concat_file = os.path.join(tmpdir, "concat.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for idx, frame in enumerate(frames):
            if isinstance(frame, dict):
                frame_file = frame.get("file", frame.get("name", f"{idx:06d}.jpg"))
                delay_ms = frame.get("delay", frame.get("duration", 100))
            else:
                frame_file = f"{idx:06d}.jpg"
                delay_ms = frame if isinstance(frame, int) else 100

            delay_sec = delay_ms / 1000.0
            full_frame_path = os.path.relpath(
                os.path.join(json_dir, frame_file), tmpdir
            )
            f.write(f"file '{full_frame_path}'\n")
            f.write(f"duration {delay_sec}\n")
    return concat_file

def get_size_mb(filepath: str) -> str:
    """获取文件大小（MB）"""
    return f"{os.path.getsize(filepath) / (1024 * 1024):.2f}"

def extract_zip(zip_path: str) -> str:
    """
    解压 ZIP 并准备转换所需的数据
    返回: (tmpdir, concat_file) 
          调用者负责清理 tmpdir
    """
    tmpdir = tempfile.TemporaryDirectory()
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmpdir.name)
    
    json_path = find_json(tmpdir.name)
    json_dir = os.path.dirname(json_path)
    frames = parse_frames(json_path)
    concat_file = create_concat_file(tmpdir.name, json_dir, frames)
    
    return tmpdir, concat_file