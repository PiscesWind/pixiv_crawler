import subprocess
from .core import extract_zip, get_size_mb

def ugoira_to_webp(zip_path: str, output_path: str, quality: int = 100):
    """转换为 WebP（保持原始尺寸，支持奇数）"""
    tmpdir, concat_file = extract_zip(zip_path)
    
    try:
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c:v", "libwebp_anim",
            "-quality", str(quality),
            "-loop", "0",
            "-vsync", "vfr",
            "-y", output_path,
        ]
        subprocess.run(cmd, cwd=tmpdir.name, check=True)
        print(f"✅ WebP: {output_path} ({get_size_mb(output_path)} MB)")
    finally:
        tmpdir.cleanup()