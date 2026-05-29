import subprocess
from .core import extract_zip, get_size_mb

def ugoira_to_mp4(zip_path: str, output_path: str):
    """转换为 MP4（必须偶数尺寸）"""
    tmpdir, concat_file = extract_zip(zip_path)
    
    try:
        # MP4：强制转为偶数尺寸
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-y", output_path,
        ]
        subprocess.run(cmd, cwd=tmpdir.name, check=True)
        print(f"✅ MP4: {output_path} ({get_size_mb(output_path)} MB)")
    finally:
        tmpdir.cleanup()  # 清理临时目录