"""
外部依赖下载器
处理@require指定的外部库下载
"""

import hashlib
import logging
import re
import tempfile
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

        logger.info(f"Downloading {url}...")
        temp_path = None
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            self.lib_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=self.lib_dir, prefix=f".{filename}.", suffix=".download", delete=False
            ) as temp_file:
                temp_file.write(response.content)
                temp_path = Path(temp_file.name)
            temp_path.replace(output_path)
            return filename
        except (requests.RequestException, OSError) as e:
            logger.error(f"Download failed for {url}: {e}")
            return None
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def clear(self):
        if self.lib_dir.exists():
            for file in self.lib_dir.iterdir():
                if file.is_file():
                    file.unlink()
            logger.info(f"Cleared lib directory: {self.lib_dir}")
