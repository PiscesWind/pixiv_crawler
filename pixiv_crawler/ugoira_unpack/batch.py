import os
import subprocess
from pathlib import Path
from .core import extract_zip, get_size_mb

def convert_all_formats(zip_path: str, output_dir: str = None, webp_quality: int = 100):
    """
    一次性转换 MP4、GIF、WebP 三种格式，只解压一次
    即使某种格式失败，其他格式仍会继续转换
    """
    zip_path = Path(zip_path)
    
    # 确定输出目录
    if output_dir is None:
        output_dir = zip_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用 ZIP 文件名作为基础名称
    base_name = zip_path.stem
    mp4_path = output_dir / f"{base_name}.mp4"
    gif_path = output_dir / f"{base_name}.gif"
    webp_path = output_dir / f"{base_name}.webp"
    
    print(f"📦 开始处理: {zip_path.name}")
    print(f"📁 输出目录: {output_dir}")
    print(f"🔄 解压中...")
    
    # 只解压一次
    tmpdir, concat_file= extract_zip(str(zip_path))
    
    results = {'mp4': None, 'gif': None, 'webp': None}
    errors = []
    
    try:
        print(f"✅ 解压完成，准备转换...")
        print(f"🎬 开始转换...\n")
        
        # 转换 MP4
        try:
            print(f"  📹 转换 MP4...")
            cmd_mp4 = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-y", str(mp4_path),
            ]
            subprocess.run(cmd_mp4, cwd=tmpdir.name, check=True, capture_output=True, text=True)
            print(f"    ✅ MP4: {mp4_path} ({get_size_mb(str(mp4_path))} MB)")
            results['mp4'] = str(mp4_path)
        except subprocess.CalledProcessError as e:
            error_msg = f"MP4 转换失败: {e.stderr if e.stderr else str(e)}"
            print(f"    ❌ {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"MP4 转换出错: {str(e)}"
            print(f"    ❌ {error_msg}")
            errors.append(error_msg)
        
        # 转换 GIF
        try:
            print(f"  🖼️  转换 GIF...")
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
                capture_output=True,
                text=True
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
                    "-y", str(gif_path),
                ],
                cwd=tmpdir.name,
                check=True,
                capture_output=True,
                text=True
            )
            print(f"    ✅ GIF: {gif_path} ({get_size_mb(str(gif_path))} MB)")
            results['gif'] = str(gif_path)
        except subprocess.CalledProcessError as e:
            error_msg = f"GIF 转换失败: {e.stderr if e.stderr else str(e)}"
            print(f"    ❌ {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"GIF 转换出错: {str(e)}"
            print(f"    ❌ {error_msg}")
            errors.append(error_msg)
        
        # 转换 WebP
        try:
            print(f"  🎨 转换 WebP (质量={webp_quality})...")
            cmd_webp = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c:v", "libwebp_anim",
                "-quality", str(webp_quality),
                "-loop", "0",
                "-vsync", "vfr",
                "-y", str(webp_path),
            ]
            subprocess.run(cmd_webp, cwd=tmpdir.name, check=True, capture_output=True, text=True)
            print(f"    ✅ WebP: {webp_path} ({get_size_mb(str(webp_path))} MB)")
            results['webp'] = str(webp_path)
        except subprocess.CalledProcessError as e:
            error_msg = f"WebP 转换失败: {e.stderr if e.stderr else str(e)}"
            print(f"    ❌ {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"WebP 转换出错: {str(e)}"
            print(f"    ❌ {error_msg}")
            errors.append(error_msg)
        
        # 输出总结
        print(f"\n{'='*50}")
        successful = [k for k, v in results.items() if v is not None]
        if successful:
            print(f"✅ 成功转换: {', '.join(successful)}")
        if errors:
            print(f"❌ 失败: {len(errors)} 项")
            for error in errors:
                print(f"   - {error}")
        print(f"{'='*50}")
        
    finally:
        tmpdir.cleanup()
    
    return results, errors