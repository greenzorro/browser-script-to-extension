"""
外部依赖下载器
处理@require指定的外部库下载
"""

import hashlib
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class DependencyFetcher:
    """外部依赖下载器"""

    LOCK_FILENAME = "dependencies.lock.json"

    def __init__(self, lib_dir: Path, timeout: int = 30):
        self.lib_dir = lib_dir
        self.lock_path = lib_dir.parent / self.LOCK_FILENAME
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

    def fetch_all(self, urls: List[str], refresh: bool = False) -> List[str]:
        """解析所有外部依赖；优先复用已验证缓存，任一失败则 fail-fast。"""
        if not urls:
            return []

        logger.warning(
            "Chrome Web Store policy: All code must be included in the extension package. "
            f"Resolving {len(urls)} remote dependenc{'y' if len(urls) == 1 else 'ies'}. "
            "Ensure these libraries comply with Chrome Web Store policies. "
            "No integrity (SRI) verification is performed."
        )

        self.lib_dir.mkdir(parents=True, exist_ok=True)
        previous_entries = self._load_lock()
        current_entries: Dict[str, Dict[str, str]] = {}
        resolved: List[str] = []
        used_names: set = set()

        for url in urls:
            previous_entry = previous_entries.get(url, {})
            filename = self._locked_filename(previous_entry, used_names)
            if filename is None:
                filename = self._unique_filename(url, used_names)

            output_path = self.lib_dir / filename
            expected_hash = previous_entry.get("sha256")
            cache_is_valid = (
                not refresh
                and self._cache_matches(output_path, expected_hash)
            )

            if cache_is_valid:
                logger.info(f"Reusing verified dependency: {url} -> {filename}")
            else:
                filename = self.fetch(url, filename=filename)
                if filename:
                    logger.info(f"Downloaded: {url} -> {filename}")

            if not filename:
                raise RuntimeError(
                    f"Failed to download @require dependency: {url}. "
                    "Build aborted (fail-fast)."
                )

            used_names.add(filename)
            resolved.append(filename)
            current_entries[url] = {
                "filename": filename,
                "sha256": self._sha256(self.lib_dir / filename),
            }

        self._save_lock(current_entries)
        return resolved

    def _load_lock(self) -> Dict[str, Dict[str, str]]:
        if not self.lock_path.exists():
            return {}

        try:
            data = json.loads(self.lock_path.read_text(encoding="utf-8"))
            dependencies = data.get("dependencies")
            if data.get("version") != 1 or not isinstance(dependencies, dict):
                raise ValueError("unsupported lock format")
            if not all(
                isinstance(url, str) and isinstance(entry, dict)
                for url, entry in dependencies.items()
            ):
                raise ValueError("invalid dependency entry")
            return dependencies
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            logger.warning(
                f"Ignoring invalid dependency lock file {self.lock_path.name}: {error}"
            )
            return {}

    def _save_lock(self, entries: Dict[str, Dict[str, str]]) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {"version": 1, "dependencies": entries},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.lock_path.parent,
                prefix=f".{self.lock_path.name}.",
                suffix=".write",
                delete=False,
            ) as temp_file:
                temp_file.write(payload)
                temp_path = Path(temp_file.name)
            temp_path.replace(self.lock_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _cache_matches(self, path: Path, expected_hash: object) -> bool:
        if not isinstance(expected_hash, str) or not path.is_file():
            return False
        try:
            return self._sha256(path) == expected_hash
        except OSError as error:
            logger.warning(f"Unable to verify cached dependency {path.name}: {error}")
            return False

    @staticmethod
    def _locked_filename(entry: Dict[str, str], used_names: set) -> Optional[str]:
        filename = entry.get("filename")
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or filename in used_names
        ):
            return None
        return filename

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

    def fetch(
        self,
        url: str,
        used_names: Optional[set] = None,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """下载单个依赖，返回文件名"""
        used_names = used_names or set()
        filename = filename or self._unique_filename(url, used_names)
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
        if self.lock_path.exists():
            self.lock_path.unlink()
            logger.info(f"Cleared dependency lock: {self.lock_path}")
