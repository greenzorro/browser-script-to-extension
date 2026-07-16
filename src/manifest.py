"""
Manifest V3生成器
将UserScript元数据转换为Chrome Extension Manifest V3格式
"""

import json
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

from .parser import UserScriptMetadata
from .gm_api import (
    collect_permissions,
    collect_host_permissions_from_grants,
    connect_to_host_permission,
    needs_background,
)


class ManifestV3Generator:
    """Manifest V3配置生成器"""

    def __init__(
        self,
        metadata: UserScriptMetadata,
        lib_files: List[str] = None,
        has_icons: bool = False,
        exclude_patterns: Optional[List[str]] = None,
        with_background: Optional[bool] = None,
    ):
        self.metadata = metadata
        self.lib_files = lib_files or []
        self.has_icons = has_icons
        self.exclude_patterns = exclude_patterns or []
        if with_background is None:
            self.with_background = needs_background(metadata.grant_permissions)
        else:
            self.with_background = with_background
        self.manifest: Dict[str, Any] = {}

    def generate(self) -> Dict[str, Any]:
        """生成Manifest V3配置"""
        content_script: Dict[str, Any] = {
            "matches": self._get_match_patterns(),
            "js": self._get_js_files(),
            "run_at": self._get_run_at(),
        }
        world = self._get_execution_world()
        if world != "ISOLATED":
            content_script["world"] = world
        if self.exclude_patterns:
            content_script["exclude_matches"] = self.exclude_patterns

        self.manifest = {
            "manifest_version": 3,
            "name": self.metadata.name,
            "version": self._normalize_version(),
            "description": self.metadata.description,
            "content_scripts": [content_script],
        }

        permissions = self._get_permissions()
        if permissions:
            self.manifest["permissions"] = permissions

        host_permissions = self._get_host_permissions()
        if host_permissions:
            self.manifest["host_permissions"] = host_permissions

        icons = self._get_icons()
        if icons:
            self.manifest["icons"] = icons

        if self.metadata.homepage_url:
            self.manifest["homepage_url"] = self.metadata.homepage_url

        if self.metadata.author:
            self.manifest["author"] = self.metadata.author

        if self.with_background:
            self.manifest["background"] = {
                "service_worker": "background.js",
            }

        return self.manifest

    def _normalize_version(self) -> str:
        version = self.metadata.version.lstrip("vV")
        # 去掉预发布后缀中 Chrome 不接受的部分：仅保留数字段
        core = version.split("-")[0].split("+")[0]
        parts = [p for p in core.split(".") if p.isdigit()]
        if not parts:
            return "1.0.0"
        while len(parts) < 3:
            parts.append("0")
        return ".".join(parts[:4])

    def _get_icons(self) -> Optional[Dict[str, str]]:
        if not self.has_icons:
            return None
        return {
            "16": "icons/icon16.png",
            "48": "icons/icon48.png",
            "128": "icons/icon128.png",
        }

    def _get_permissions(self) -> List[str]:
        return collect_permissions(self.metadata.grant_permissions)

    def _get_host_permissions(self) -> List[str]:
        hosts: Set[str] = set(
            collect_host_permissions_from_grants(self.metadata.grant_permissions)
        )
        for connect in self.metadata.connect_urls:
            converted = connect_to_host_permission(connect)
            if converted:
                hosts.add(converted)
        return sorted(hosts)

    def _get_match_patterns(self) -> List[str]:
        if not self.metadata.match_patterns:
            raise ValueError(
                "No @match or @include patterns found. "
                "Chrome extensions require explicit host match patterns "
                "(refusing to default to <all_urls>)."
            )
        return list(self.metadata.match_patterns)

    def _get_run_at(self) -> str:
        run_at_map = {
            "document-start": "document_start",
            "document-end": "document_end",
            "document-idle": "document_idle",
        }
        return run_at_map.get(self.metadata.run_at, "document_end")

    def _get_execution_world(self) -> str:
        world = (self.metadata.execution_world or "ISOLATED").upper()
        return world if world in ("MAIN", "ISOLATED") else "ISOLATED"

    def _get_js_files(self) -> List[str]:
        js_files = []
        if self.lib_files:
            js_files.extend([f"lib/{lib}" for lib in self.lib_files])
        js_files.append("content.js")
        return js_files

    def save(self, output_path: Path):
        output_path.write_text(
            json.dumps(self.manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
