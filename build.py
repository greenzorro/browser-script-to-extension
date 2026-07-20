#!/usr/bin/env python3
"""
Tampermonkey脚本到浏览器插件转换工具
主入口文件
"""

import sys
import argparse
import logging
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from src.parser import UserScriptParser
from src.manifest import ManifestV3Generator
from src.converter import CodeConverter
from src.fetcher import DependencyFetcher
from src.validator import validate_store_readiness, validate_store_assets
from src.packager import load_upload_config, package_extension, open_upload_pages
from src.gm_api import needs_background
from utils.image import generate_icon_sizes


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def find_script_file(script_dir: Path) -> Path:
    """扫描目录下所有.js文件，找到包含UserScript特征的那个"""
    logger = logging.getLogger(__name__)
    candidates = []
    skipped = []

    for js_file in script_dir.glob("*.js"):
        try:
            content = js_file.read_text(encoding="utf-8")
            if "// ==UserScript==" in content and "// ==/UserScript==" in content:
                candidates.append(js_file)
            else:
                skipped.append(f"{js_file.name}: no UserScript metadata block")
        except Exception as e:
            skipped.append(f"{js_file.name}: {type(e).__name__}: {e}")
            logger.warning(f"Skipped unreadable JS file {js_file.name}: {e}")

    if len(candidates) == 0:
        detail = ""
        if skipped:
            detail = " Inspected: " + "; ".join(skipped)
        raise FileNotFoundError(
            f"No UserScript found in directory: {script_dir}.{detail}"
        )
    if len(candidates) > 1:
        names = ", ".join([c.name for c in candidates])
        raise ValueError(
            f"Multiple UserScripts found in directory: {script_dir}. "
            f"Please specify which one to use. Found: {names}"
        )

    return candidates[0]


def build_script(
    script_dir: Path,
    clean: bool = False,
    verbose: bool = False,
    package: bool = False,
    refresh_dependencies: bool = False,
) -> bool:
    logger = logging.getLogger(__name__)

    try:
        script_path = find_script_file(script_dir)
        logger.info(f"Found script: {script_path}")

        parser = UserScriptParser(script_path)
        metadata = parser.parse()
        exclude_patterns = parser.get_exclude_patterns()
        logger.info(f"Parsed: {metadata.name} v{metadata.version}")
        logger.info(f"Grants (normalized): {metadata.grant_permissions}")
        logger.info(f"Match patterns: {metadata.match_patterns}")
        logger.info(f"Execution world: {metadata.execution_world}")

        validate_store_readiness(metadata, script_dir)

        output_dir = script_dir / "extension"
        if clean and output_dir.exists():
            shutil.rmtree(output_dir)
            logger.info("Cleaned output directory")

        output_dir.mkdir(parents=True, exist_ok=True)

        assets_info = validate_store_assets(script_dir)
        logger.info(
            f"Validated store assets: {assets_info['screenshot_count']} screenshot(s)"
        )

        lib_dir = output_dir / "lib"
        lib_files = []
        if metadata.require_urls:
            fetcher = DependencyFetcher(lib_dir)
            lib_files = fetcher.fetch_all(
                metadata.require_urls, refresh=refresh_dependencies
            )

        use_background = needs_background(metadata.grant_permissions)
        manifest_gen = ManifestV3Generator(
            metadata,
            lib_files,
            has_icons=True,
            exclude_patterns=exclude_patterns,
            with_background=use_background,
        )
        manifest_gen.generate()
        manifest_path = output_dir / "manifest.json"
        manifest_gen.save(manifest_path)
        logger.info(f"Generated: {manifest_path}")

        code_body = parser.extract_code_body()
        converter = CodeConverter(metadata)
        converted_code = converter.convert(code_body)
        content_path = output_dir / "content.js"
        converter.save(converted_code, content_path)
        logger.info(f"Generated: {content_path}")

        if use_background:
            bg_path = output_dir / "background.js"
            converter.save_background(bg_path)
            logger.info(f"Generated: {bg_path} (GM API bridge)")

        icon_source = script_dir / "store_assets" / "icon.png"
        icons_dir = output_dir / "icons"
        if not generate_icon_sizes(icon_source, icons_dir):
            raise RuntimeError("Icon generation failed. Check if icon.png is valid.")
        logger.info("Generated icons: 16x16, 48x48, 128x128")

        logger.info(f"Extension built: {output_dir}")

        if package:
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
                config = None

            zip_path = package_extension(
                output_dir, script_path.name, config, script_dir
            )

            if zip_path and config:
                open_upload_pages(config)

        return True

    except Exception as e:
        logger.error(f"Build failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Tampermonkey脚本到浏览器插件转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python build.py /path/to/your/script-directory
  python build.py /path/to/your/script-directory --clean
  python build.py /path/to/your/script-directory -v
  python build.py /path/to/your/script-directory --package
  python build.py /path/to/your/script-directory --refresh-dependencies
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
    parser.add_argument(
        "--refresh-dependencies",
        action="store_true",
        help="忽略已验证的@require缓存并重新下载依赖",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    success = build_script(
        args.script_dir,
        args.clean,
        args.verbose,
        args.package,
        args.refresh_dependencies,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
