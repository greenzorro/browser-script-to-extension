"""
外部依赖下载器
处理@require指定的外部库下载
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class DependencyFetcher:
    """外部依赖下载器"""

    def __init__(self, lib_dir: Path, timeout: int = 30):
        self.lib_dir = lib_dir
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; browser-script-to-extension/1.0; "
                    "+https://github.com/greenzorro/browser-script-to-extension)"
                )
            }
        )

    def fetch_all(self, urls: List[str]) -> List[str]:
        """下载所有外部依赖；任一失败则抛出异常（fail-fast）"""
        if not urls:
            return []

        logger.warning(
            "Chrome Web Store policy: All code must be included in the extension package. "
            f"Downloading {len(urls)} remote dependenc{'y' if len(urls) == 1 else 'ies'}. "
            "Ensure these libraries comply with Chrome Web Store policies. "
            "No integrity (SRI) verification is performed."
        )

        self.lib_dir.mkdir(parents=True, exist_ok=True)
        downloaded: List[str] = []
        used_names: set = set()

        for url in urls:
            filename = self.fetch(url, used_names)
            if not filename:
                raise RuntimeError(
                    f"Failed to download @require dependency: {url}. "
                    "Build aborted (fail-fast)."
                )
            used_names.add(filename)
            downloaded.append(filename)
            logger.info(f"Downloaded: {url} -> {filename}")

        return downloaded

    def _unique_filename(self, url: str, used_names: set) -> str:
        parsed = urlparse(url)
        base = parsed.path.split("/")[-1] or "dependency.js"
        base = re.sub(r"[^\w.\-]", "_", base)
        if not base.endswith(".js") and "." not in base:
            base += ".js"

        if base not in used_names:
            return base

        # 同名冲突：用 URL hash 前缀区分
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
        stem = base[:-3] if base.endswith(".js") else base
        candidate = f"{stem}_{digest}.js"
        return candidate

    def fetch(self, url: str, used_names: Optional[set] = None) -> Optional[str]:
        """下载单个依赖，返回文件名"""
        used_names = used_names or set()
        filename = self._unique_filename(url, used_names)
        output_path = self.lib_dir / filename

        # 仅当同 URL 对应文件已存在且名未被占用策略命中时复用
        # 为避免错误复用同名不同源，冲突名总是重新下载到唯一文件
        if output_path.exists() and filename not in used_names:
            # 存在但可能是旧构建残留；仍允许复用同名文件（同一构建内 used_names 会阻止冲突）
            logger.info(f"File already exists, reusing: {output_path.name}")
            return filename

        logger.info(f"Downloading {url}...")
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            output_path.write_bytes(response.content)
            return filename
        except requests.RequestException as e:
            logger.error(f"Download failed for {url}: {e}")
            return None

    def clear(self):
        if self.lib_dir.exists():
            for file in self.lib_dir.iterdir():
                if file.is_file():
                    file.unlink()
            logger.info(f"Cleared lib directory: {self.lib_dir}")
