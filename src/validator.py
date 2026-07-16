"""
验证模块
验证Chrome Web Store上架要求
"""

import logging
import re
from pathlib import Path

from src.parser import UserScriptMetadata
from src.gm_api import connect_to_host_permission


def validate_store_readiness(metadata: UserScriptMetadata, script_dir: Path) -> None:
    """
    验证扩展是否满足Chrome Web Store上架要求

    Raises:
        RuntimeError: 如果不满足上架要求
    """
    logger = logging.getLogger(__name__)

    if not metadata.description or not metadata.description.strip():
        raise RuntimeError(
            "Description is required for Chrome Web Store. "
            "Add @description in your userscript."
        )

    if len(metadata.description) > 132:
        raise RuntimeError(
            f"Description exceeds 132 characters (current: {len(metadata.description)}). "
            "Chrome Web Store requires description <= 132 characters. "
            "Please shorten your @description in the userscript."
        )

    if not metadata.match_patterns:
        raise RuntimeError(
            "At least one @match or @include pattern is required. "
            "Refusing to default to <all_urls> for Chrome Web Store safety."
        )

    if "<all_urls>" in metadata.match_patterns or any(
        p in ("*://*/*", "http://*/*", "https://*/*") for p in metadata.match_patterns
    ):
        logger.warning(
            "Broad match patterns (<all_urls> / *://*/*) may cause Chrome Web Store "
            "review friction. Prefer specific host patterns when possible."
        )

    if len(metadata.name) > 75:
        raise RuntimeError(
            f"Extension name exceeds 75 characters (current: {len(metadata.name)}). "
            "Chrome Web Store requires name <= 75 characters."
        )

    version_core = metadata.version.lstrip("vV").split("-")[0].split("+")[0]
    if not re.match(r"^\d+(\.\d+){0,3}$", version_core):
        logger.warning(
            f"Version '{metadata.version}' may not follow Chrome Web Store format. "
            "Recommended format: x.y.z (e.g., 1.0.0)"
        )

    # @connect 可转换性检查
    for connect in metadata.connect_urls:
        if connect_to_host_permission(connect) is None:
            logger.warning(
                f"@connect value '{connect}' could not be converted to a valid "
                "Chrome host_permissions pattern and will be skipped."
            )

    if metadata.resource_urls:
        logger.warning(
            f"@resource is declared ({len(metadata.resource_urls)} entries) but not packaged. "
            "GM_getResourceText / GM_getResourceURL are unsupported."
        )

    world = (metadata.execution_world or "ISOLATED").upper()
    if world == "MAIN" and metadata.uses_gm_api():
        logger.warning(
            "MAIN world cannot use chrome.*; GM polyfills that need storage/runtime "
            "will not work. Use ISOLATED with GM grants, or @grant none in MAIN."
        )


def validate_store_assets(script_dir: Path) -> dict:
    """
    验证Chrome Web Store上架所需的材料

    store_assets 目录必须包含：
    - icon.png: 图标源文件（必需）
    - 至少1张截图文件：*.png 或 *.jpg（必需，最多5张，不含 icon.png）
    """
    logger = logging.getLogger(__name__)

    config_dir = script_dir / "store_assets"
    icon_path = config_dir / "icon.png"

    if not config_dir.exists():
        raise RuntimeError(
            "store_assets directory is required for Chrome Web Store submission. "
            "Create it with: 1) icon.png (required) 2) at least 1 screenshot "
            "*.png or *.jpg (required, not counting icon.png)"
        )

    if not icon_path.exists():
        raise RuntimeError(
            "icon.png not found in store_assets/. "
            "This is required for Chrome Web Store submission."
        )

    screenshot_files = []
    for pattern in ("*.png", "*.jpg", "*.jpeg"):
        for path in config_dir.glob(pattern):
            if path.name.lower() == "icon.png":
                continue
            screenshot_files.append(path)

    # 去重（大小写不同扩展名等）
    unique = {p.resolve(): p for p in screenshot_files}
    screenshot_files = list(unique.values())

    if len(screenshot_files) == 0:
        raise RuntimeError(
            "No screenshots found in store_assets/ (icon.png does not count). "
            "At least 1 screenshot (*.png / *.jpg) is required for Chrome Web Store submission."
        )

    if len(screenshot_files) > 5:
        logger.warning(
            f"Chrome Web Store allows maximum 5 screenshots, found {len(screenshot_files)}"
        )

    return {"has_icon": True, "screenshot_count": len(screenshot_files)}
