"""
验证模块
验证Chrome Web Store上架要求
"""

import logging
from pathlib import Path

from src.parser import UserScriptMetadata


def validate_store_readiness(metadata: UserScriptMetadata, script_dir: Path) -> None:
    """
    验证扩展是否满足Chrome Web Store上架要求

    Args:
        metadata: 脚本元数据
        script_dir: 脚本目录

    Raises:
        RuntimeError: 如果不满足上架要求
    """
    logger = logging.getLogger(__name__)

    # 检查1: 描述不能为空
    if not metadata.description or metadata.description == "Unnamed Script":
        raise RuntimeError(
            "Description is required for Chrome Web Store. "
            "Add @description in your userscript or in store listing."
        )

    # 检查2: 描述长度限制（132字符）
    if len(metadata.description) > 132:
        raise RuntimeError(
            f"Description exceeds 132 characters (current: {len(metadata.description)}). "
            "Chrome Web Store requires description <= 132 characters. "
            "Please shorten your @description in the userscript."
        )

    # 检查3: 权限不能是<all_urls>，除非确实需要
    if "<all_urls>" in metadata.match_patterns:
        logger.warning(
            "Chrome Web Store may reject extensions with '<all_urls>' permissions. "
            "Use specific match patterns instead if possible."
        )

    # 检查4: 名称长度限制（75字符）
    if len(metadata.name) > 75:
        raise RuntimeError(
            f"Extension name exceeds 75 characters (current: {len(metadata.name)}). "
            "Chrome Web Store requires name <= 75 characters."
        )

    # 检查5: 版本号格式
    import re

    if not re.match(r"^\d+(\.\d+){0,3}$", metadata.version.lstrip("vV")):
        logger.warning(
            f"Version '{metadata.version}' may not follow Chrome Web Store format. "
            "Recommended format: x.y.z (e.g., 1.0.0)"
        )


def validate_store_assets(script_dir: Path) -> dict:
    """
    验证Chrome Web Store上架所需的材料

    store_assets 目录必须包含：
    - icon.png: 图标源文件（必需）
    - 至少1张截图文件：*.png 或 *.jpg（必需，最多5张）

    Args:
        script_dir: 脚本目录路径

    Returns:
        dict: 包含 'has_icon' 和 'screenshot_count' 的字典

    Raises:
        RuntimeError: 如果缺少必需材料
    """
    logger = logging.getLogger(__name__)

    config_dir = script_dir / "store_assets"
    icon_path = config_dir / "icon.png"

    # store_assets 目录必须存在
    if not config_dir.exists():
        raise RuntimeError(
            f"store_assets directory is required for Chrome Web Store submission. "
            f"Create it with: 1) icon.png (required) 2) at least 1 screenshot *.png or *.jpg (required)"
        )

    # 检查图标
    if not icon_path.exists():
        raise RuntimeError(
            f"icon.png not found in store_assets/. "
            f"This is required for Chrome Web Store submission."
        )

    # 检查截图（直接在 store_assets 目录下）
    screenshot_files = list(config_dir.glob("*.png")) + list(config_dir.glob("*.jpg"))

    if len(screenshot_files) == 0:
        raise RuntimeError(
            f"No screenshots found in store_assets/. "
            f"At least 1 screenshot (*.png or *.jpg) is required for Chrome Web Store submission."
        )

    if len(screenshot_files) > 5:
        logger.warning(
            f"Chrome Web Store allows maximum 5 screenshots, found {len(screenshot_files)}"
        )

    return {"has_icon": True, "screenshot_count": len(screenshot_files)}
