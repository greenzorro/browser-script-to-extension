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
from src.validator import validate_store_readiness, validate_store_assets
from src.packager import load_upload_config, package_extension, open_upload_pages
from utils.image import generate_icon_sizes


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


def build_script(
    script_dir: Path, clean: bool = False, verbose: bool = False, package: bool = False
) -> bool:
    """
    构建单个脚本为浏览器扩展

    Args:
        script_dir: 脚本目录路径
        clean: 是否清理输出目录后重新构建
        verbose: 是否显示详细日志
        package: 是否打包并打开上传页面

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

        # 打包逻辑
        if package:
            # 加载上传配置
            config = load_upload_config(script_dir)

            if config is None:
                logger.warning(
                    "No upload_config.json found in store_assets/. "
                    "Will package with default settings and skip upload page opening. "
                    "Create store_assets/upload_config.json to enable auto-opening."
                )
            elif "upload_urls" not in config:
                logger.warning(
                    "upload_config.json exists but missing 'upload_urls' field. "
                    "Will package and skip upload page opening."
                )
                config = None  # 标记为无效配置

            # 打包extension目录
            zip_path = package_extension(
                output_dir, script_path.name, config, script_dir
            )

            if zip_path and config:
                # 打开上传页面
                open_upload_pages(config)

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
  python build.py /path/to/your/script-directory --package # 打包并打开上传页面
        """,
    )

    parser.add_argument("script_dir", type=Path, help="脚本目录路径（必需）")
    parser.add_argument("--clean", action="store_true", help="清理输出目录后重新构建")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细日志")
    parser.add_argument(
        "--package",
        action="store_true",
        help="打包extension为ZIP并打开上传页面（需要在store_assets/upload_config.json中配置）",
    )

    args = parser.parse_args()

    # 设置日志
    setup_logging(args.verbose)

    # 执行构建
    success = build_script(args.script_dir, args.clean, args.verbose, args.package)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
