"""
打包发布模块
将extension目录打包成ZIP，并打开上传页面
"""

import json
import logging
import os
import platform
import shutil
import webbrowser
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def load_upload_config(script_dir: Path) -> Optional[Dict]:
    """
    加载上传配置文件

    Args:
        script_dir: 脚本目录路径

    Returns:
        配置字典，如果文件不存在或解析失败返回 None
    """
    config_path = script_dir / "store_assets" / "upload_config.json"

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to parse upload_config.json: {e}")
        return None


def detect_wsl() -> bool:
    """
    检测是否运行在WSL环境

    Returns:
        bool: True表示WSL环境，False表示其他环境
    """
    try:
        with open("/proc/version", "r") as f:
            version_info = f.read().lower()
        return "microsoft" in version_info or "wsl" in version_info
    except (FileNotFoundError, IOError):
        # 无法读取/proc/version，使用platform检测
        return "microsoft" in platform.uname().release.lower()


def copy_store_assets_to_downloads(
    script_dir: Path,
    zip_filename: str,
    output_path: Path,
) -> None:
    """
    复制 store_assets 中的图片到下载目录

    Args:
        script_dir: 脚本目录路径
        zip_filename: ZIP 文件名（含 .zip 扩展名）
        output_path: 当前输出路径
    """
    logger = logging.getLogger(__name__)

    # 确定下载目录
    downloads_dir = Path.home() / "Downloads"

    # 如果输出目录不是下载目录，才需要复制
    if output_path == downloads_dir or output_path.resolve() == downloads_dir.resolve():
        logger.debug("Output is already in Downloads, skipping copy")
        return

    store_assets_dir = script_dir / "store_assets"
    if not store_assets_dir.exists():
        return

    # 创建目标子目录：zip_name + _assets
    assets_dir_name = zip_filename.replace(".zip", "") + "_assets"
    assets_output_dir = downloads_dir / assets_dir_name
    assets_output_dir.mkdir(parents=True, exist_ok=True)

    # 复制所有图片文件
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    copied_count = 0

    for img_file in store_assets_dir.iterdir():
        if img_file.suffix.lower() not in image_extensions:
            continue

        # 特殊处理 icon.png -> icon128.png (128x128)
        if img_file.name == "icon.png":
            if not PIL_AVAILABLE:
                logger.warning("PIL not available, skipping icon.png resize")
                continue

            target_path = assets_output_dir / "icon128.png"
            try:
                with Image.open(img_file) as img:
                    img_resized = img.resize((128, 128), Image.Resampling.LANCZOS)
                    img_resized.save(target_path, "PNG")
                logger.info(f"Copied and resized: {target_path}")
                copied_count += 1
            except Exception as e:
                logger.error(f"Failed to process icon.png: {e}")
        else:
            # 直接复制其他图片
            target_path = assets_output_dir / img_file.name
            shutil.copy2(img_file, target_path)
            logger.info(f"Copied: {target_path}")
            copied_count += 1

    if copied_count > 0:
        logger.info(f"Copied {copied_count} asset file(s) to {assets_output_dir}")


def package_extension(
    extension_dir: Path,
    script_filename: str,
    config: Optional[Dict],
    script_dir: Path,
) -> Optional[Path]:
    """
    打包extension目录为ZIP文件

    Args:
        extension_dir: extension目录路径
        script_filename: 脚本文件名（不含扩展名），用于默认ZIP命名
        config: 上传配置（可能为None）
        script_dir: 脚本目录路径（用于解析相对路径）

    Returns:
        生成的ZIP文件路径，失败时返回None
    """
    logger = logging.getLogger(__name__)

    # 确定ZIP文件名（移除.js扩展名）
    base_name = script_filename.replace(".js", "").replace(".user.js", "")
    if config and "zip_filename" in config:
        zip_name = config["zip_filename"]
    else:
        # 使用脚本文件名
        zip_name = base_name

    zip_filename = f"{zip_name}.zip"

    # 确定输出路径
    if config and "output_path" in config:
        output_path_str = config["output_path"]
        output_path = Path(output_path_str)

        # 处理~扩展
        if str(output_path).startswith("~"):
            output_path = output_path.expanduser()

        # 处理相对路径（相对于script_dir）
        if not output_path.is_absolute():
            output_path = (script_dir / output_path).resolve()
    else:
        # 默认：项目根目录（与extension同级）
        output_path = script_dir

    # 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)

    zip_file_path = output_path / zip_filename

    # 删除已存在的ZIP文件
    if zip_file_path.exists():
        zip_file_path.unlink()
        logger.debug(f"Removed existing ZIP file: {zip_file_path}")

    # 创建ZIP文件
    try:
        with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(extension_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(extension_dir)
                    zipf.write(file_path, arcname)

        logger.info(f"Packaged: {zip_file_path}")
        logger.info(f"  Size: {zip_file_path.stat().st_size:,} bytes")

        # 复制 ZIP 到下载目录（如果输出路径不是下载目录）
        downloads_dir = Path.home() / "Downloads"
        if output_path != downloads_dir and output_path.resolve() != downloads_dir.resolve():
            downloads_zip_path = downloads_dir / zip_filename
            shutil.copy2(zip_file_path, downloads_zip_path)
            logger.info(f"Copied ZIP to Downloads: {downloads_zip_path}")

        # 复制 store_assets 图片到下载目录
        copy_store_assets_to_downloads(script_dir, zip_filename, output_path)

        return zip_file_path

    except Exception as e:
        logger.error(f"Failed to create ZIP: {e}")
        return None


def open_upload_pages(config: Dict) -> None:
    """
    打开上传页面（在浏览器中）

    Args:
        config: 上传配置字典
    """
    logger = logging.getLogger(__name__)

    # 检测WSL环境
    is_wsl = detect_wsl()

    if is_wsl:
        logger.info("WSL environment detected. Browser auto-open not available.")
        logger.info("Please manually visit the URLs below:")
    else:
        logger.info("Opening upload pages in browser...")

    upload_urls = config.get("upload_urls", [])

    if not upload_urls:
        logger.warning("No upload URLs configured in upload_config.json")
        return

    for i, entry in enumerate(upload_urls, 1):
        url = entry if isinstance(entry, str) else entry.get("url", "")

        if not url:
            continue

        logger.info(f"{i}. {url}")

        if not is_wsl:
            try:
                webbrowser.open(url)
            except Exception as e:
                logger.warning(f"   Failed to open browser: {e}")
