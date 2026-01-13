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
