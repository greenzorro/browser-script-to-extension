"""
图像处理工具
从单一图标源文件生成多尺寸图标
"""

from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available, icon generation will be skipped")


def generate_icon_sizes(
    source_path: Path, output_dir: Path, sizes: List[int] = None
) -> bool:
    """
    从单一图标源文件生成多尺寸图标

    Args:
        source_path: 源图标路径
        output_dir: 输出目录
        sizes: 需要生成的尺寸列表，默认 [16, 48, 128]

    Returns:
        bool: 是否成功生成

    Raises:
        RuntimeError: 如果PIL不可用或生成失败
    """
    if not PIL_AVAILABLE:
        raise RuntimeError(
            "PIL is required for icon generation. Install with: pip install Pillow"
        )

    if sizes is None:
        sizes = [16, 48, 128]

    if not source_path.exists():
        raise RuntimeError(f"Icon source file not found: {source_path}")

    try:
        # 打开源图片
        img = Image.open(source_path)

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成不同尺寸
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            output_path = output_dir / f"icon{size}.png"
            resized.save(output_path, "PNG")
            logger.info(f"Generated: {output_path}")

        return True

    except Exception as e:
        raise RuntimeError(f"Failed to generate icons: {e}")


def validate_store_assets(script_dir: Path) -> dict:
    """
    验证Chrome Web Store上架所需的材料

    store_assets 目录必须包含：
    - icon.png: 图标源文件（必需）
    - screenshots/: 至少1张截图（必需）

    Args:
        script_dir: 脚本目录路径

    Returns:
        dict: 包含 'has_icon' 和 'screenshot_count' 的字典

    Raises:
        RuntimeError: 如果缺少必需材料
    """
    config_dir = script_dir / "store_assets"
    icon_path = config_dir / "icon.png"
    screenshots_dir = config_dir / "screenshots"

    # store_assets 目录必须存在
    if not config_dir.exists():
        raise RuntimeError(
            f"store_assets directory is required for Chrome Web Store submission. "
            f"Create it with: 1) icon.png (required) 2) screenshots/ with at least 1 screenshot (required)"
        )

    # 检查图标
    if not icon_path.exists():
        raise RuntimeError(
            f"icon.png not found in store_assets/. "
            f"This is required for Chrome Web Store submission."
        )

    # 检查截图
    if not screenshots_dir.exists():
        raise RuntimeError(
            f"screenshots/ directory not found in store_assets/. "
            f"At least 1 screenshot is required for Chrome Web Store submission."
        )

    screenshot_files = list(screenshots_dir.glob("*.png")) + list(
        screenshots_dir.glob("*.jpg")
    )
    if len(screenshot_files) == 0:
        raise RuntimeError(
            f"No screenshots found in store_assets/screenshots/. "
            f"At least 1 screenshot is required for Chrome Web Store submission."
        )

    if len(screenshot_files) > 5:
        logger.warning(
            f"Chrome Web Store allows maximum 5 screenshots, found {len(screenshot_files)}"
        )

    return {"has_icon": True, "screenshot_count": len(screenshot_files)}
