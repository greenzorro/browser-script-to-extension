#!/usr/bin/env python3
"""
Tampermonkey脚本到浏览器插件转换工具
主入口文件
"""

import sys
import argparse
import logging
from pathlib import Path

# 添加src到Python路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from src.parser import UserScriptParser, UserScriptMetadata
from src.manifest import ManifestV3Generator
from src.converter import CodeConverter
from src.fetcher import DependencyFetcher
from utils.image import generate_icon_sizes, validate_store_assets


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

    # 检查2: 权限不能是<all_urls>，除非确实需要
    if "<all_urls>" in metadata.match_patterns:
        logger.warning(
            "Chrome Web Store may reject extensions with '<all_urls>' permissions. "
            "Use specific match patterns instead if possible."
        )

    # 检查3: 名称长度限制（75字符）
    if len(metadata.name) > 75:
        raise RuntimeError(
            f"Extension name exceeds 75 characters (current: {len(metadata.name)}). "
            "Chrome Web Store requires name <= 75 characters."
        )

    # 检查4: 版本号格式
    import re

    if not re.match(r"^\d+(\.\d+){0,3}$", metadata.version.lstrip("vV")):
        logger.warning(
            f"Version '{metadata.version}' may not follow Chrome Web Store format. "
            "Recommended format: x.y.z (e.g., 1.0.0)"
        )


def setup_logging(verbose: bool = False):
    """设置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def find_script_file(script_dir: Path) -> Path:
    """扫描目录下所有.js文件，找到包含UserScript特征的那个"""
    candidates = []

    for js_file in script_dir.glob("*.js"):
        try:
            content = js_file.read_text(encoding="utf-8")
            if "// ==UserScript==" in content and "// ==/UserScript==" in content:
                candidates.append(js_file)
        except Exception:
            pass

    if len(candidates) == 0:
        raise FileNotFoundError(f"No UserScript found in directory: {script_dir}")
    elif len(candidates) > 1:
        names = ", ".join([c.name for c in candidates])
        raise ValueError(
            f"Multiple UserScripts found in directory: {script_dir}. "
            f"Please specify which one to use. Found: {names}"
        )

    return candidates[0]


def build_script(script_dir: Path, clean: bool = False, verbose: bool = False) -> bool:
    """
    构建单个脚本为浏览器扩展

    Args:
        script_dir: 脚本目录路径
        clean: 是否清理输出目录后重新构建
        verbose: 是否显示详细日志

    Returns:
        bool: 是否构建成功
    """
    logger = logging.getLogger(__name__)

    try:
        # 查找脚本文件
        script_path = find_script_file(script_dir)
        logger.info(f"Found script: {script_path}")

        # 解析元数据
        parser = UserScriptParser(script_path)
        metadata = parser.parse()
        logger.info(f"Parsed: {metadata.name} v{metadata.version}")

        # 验证Chrome Web Store上架要求
        validate_store_readiness(metadata, script_dir)

        # 创建输出目录
        output_dir = script_dir / "extension"
        if clean and output_dir.exists():
            # 清理输出目录
            for item in output_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    for sub in item.rglob("*"):
                        if sub.is_file():
                            sub.unlink()
                    for sub in sorted(output_dir.rglob("*"), reverse=True):
                        if sub.is_dir():
                            sub.rmdir()
            logger.info("Cleaned output directory")

        output_dir.mkdir(parents=True, exist_ok=True)

        # 验证Chrome Web Store上架材料
        assets_info = validate_store_assets(script_dir)
        logger.info(
            f"Validated store assets: {assets_info['screenshot_count']} screenshot(s)"
        )

        # 生成manifest.json
        lib_dir = output_dir / "lib"
        lib_files = []
        if metadata.require_urls:
            fetcher = DependencyFetcher(lib_dir)
            lib_files = fetcher.fetch_all(metadata.require_urls)

        manifest_gen = ManifestV3Generator(metadata, lib_files, has_icons=True)
        manifest = manifest_gen.generate()
        manifest_path = output_dir / "manifest.json"
        manifest_gen.save(manifest_path)
        logger.info(f"Generated: {manifest_path}")

        # 转换并保存脚本
        code_body = parser.extract_code_body()
        converter = CodeConverter(metadata)
        converted_code = converter.convert(code_body)
        content_path = output_dir / "content.js"
        converter.save(converted_code, content_path)
        logger.info(f"Generated: {content_path}")

        # 生成图标
        icon_source = script_dir / "store_assets" / "icon.png"
        icons_dir = output_dir / "icons"
        if not generate_icon_sizes(icon_source, icons_dir):
            raise RuntimeError("Icon generation failed. Check if icon.png is valid.")
        logger.info("Generated icons: 16x16, 48x48, 128x128")

        logger.info(f"✓ Extension built: {output_dir}")
        return True

    except Exception as e:
        logger.error(f"✗ Build failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Tampermonkey脚本到浏览器插件转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python build.py /path/to/your/script-directory       # 构建单个脚本
  python build.py /path/to/your/script-directory --clean  # 清理后重建
  python build.py /path/to/your/script-directory -v       # 显示详细日志
        """,
    )

    parser.add_argument("script_dir", type=Path, help="脚本目录路径（必需）")
    parser.add_argument("--clean", action="store_true", help="清理输出目录后重新构建")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细日志")

    args = parser.parse_args()

    # 设置日志
    setup_logging(args.verbose)

    # 执行构建
    success = build_script(args.script_dir, args.clean, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
