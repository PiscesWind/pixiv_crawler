import subprocess
import os
from .core import extract_zip, get_size_mb

def ugoira_to_gif(zip_path: str, output_path: str):
    """转换为 GIF（保持原始尺寸，支持奇数）"""
    tmpdir, concat_file = extract_zip(zip_path)
    
    try:
        palette_file = os.path.join(tmpdir.name, "palette.png")
        
        # 生成调色板
        subprocess.run(
            [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-vf", "fps=15,palettegen",
                "-y", palette_file,
            ],
            cwd=tmpdir.name,
            check=True,
        )
        
        # 生成 GIF
        subprocess.run(
            [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-i", palette_file,
                "-lavfi", "fps=15,paletteuse",
                "-y", output_path,
            ],
            cwd=tmpdir.name,
            check=True,
        )
        print(f"✅ GIF: {output_path} ({get_size_mb(output_path)} MB)")
    finally:
        tmpdir.cleanup()