"""
Manifest V3生成器
将UserScript元数据转换为Chrome Extension Manifest V3格式
"""

import json
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from .parser import UserScriptMetadata


class ManifestV3Generator:
    """Manifest V3配置生成器"""

    # GM API到Chrome权限的映射
    GM_API_PERMISSIONS: Dict[str, List[str]] = {
        "GM_xmlHttpRequest": ["<all_urls>"],
        "GM_addStyle": [],
        "GM_setValue": ["storage"],
        "GM_getValue": ["storage"],
        "GM_deleteValue": ["storage"],
        "GM_listValues": ["storage"],
        "GM_notification": ["notifications"],
        "GM_setClipboard": ["clipboardWrite"],
        "GM_openInTab": ["tabs"],
        "GM_download": ["downloads", "<all_urls>"],
    }

    def __init__(
        self,
        metadata: UserScriptMetadata,
        lib_files: List[str] = None,
        has_icons: bool = False,
    ):
        self.metadata = metadata
        self.lib_files = lib_files or []
        self.has_icons = has_icons
        self.manifest: Dict[str, Any] = {}

    def generate(self) -> Dict[str, Any]:
        """生成Manifest V3配置"""
        self.manifest = {
            "manifest_version": 3,
            "name": self.metadata.name,
            "version": self._normalize_version(),
            "description": self.metadata.description,
            "content_scripts": [
                {
                    "matches": self._get_match_patterns(),
                    "js": self._get_js_files(),
                    "run_at": self._get_run_at(),
                }
            ],
        }

        # 添加权限字段（仅在需要时）
        permissions = self._get_permissions()
        if permissions:
            self.manifest["permissions"] = permissions

        host_permissions = self._get_host_permissions()
        if host_permissions:
            self.manifest["host_permissions"] = host_permissions

        # 添加可选字段
        icons = self._get_icons()
        if icons:
            self.manifest["icons"] = icons

        if self.metadata.homepage_url:
            self.manifest["homepage_url"] = self.metadata.homepage_url

        return self.manifest

    def _normalize_version(self) -> str:
        """规范化版本号（Manifest V3要求）"""
        version = self.metadata.version
        # 移除v前缀
        version = version.lstrip("vV")
        # 简单验证格式
        parts = version.split(".")
        if len(parts) < 3:
            version += ".0" * (3 - len(parts))
        return version

    def _get_icons(self) -> Optional[Dict[str, str]]:
        """获取图标配置"""
        # 只有当实际生成了图标文件时才返回配置
        if not self.has_icons:
            return None

        return {
            "16": "icons/icon16.png",
            "48": "icons/icon48.png",
            "128": "icons/icon128.png",
        }

    def _get_permissions(self) -> List[str]:
        """获取权限列表"""
        permissions: Set[str] = set()

        # 从GM API推断权限
        for grant in self.metadata.grant_permissions:
            if grant != "none" and grant in self.GM_API_PERMISSIONS:
                for perm in self.GM_API_PERMISSIONS[grant]:
                    if perm and not perm.startswith("<all_urls>"):
                        permissions.add(perm)

        return sorted(list(permissions))

    def _get_host_permissions(self) -> List[str]:
        """获取主机权限"""
        hosts: Set[str] = set()

        # 从GM API推断主机权限
        for grant in self.metadata.grant_permissions:
            if grant != "none" and grant in self.GM_API_PERMISSIONS:
                for perm in self.GM_API_PERMISSIONS[grant]:
                    if perm and perm.startswith("<all_urls>"):
                        hosts.add("<all_urls>")

        # 从connect URLs添加
        hosts.update(self.metadata.connect_urls)

        return sorted(list(hosts))

    def _get_match_patterns(self) -> List[str]:
        """获取match patterns"""
        return (
            self.metadata.match_patterns
            if self.metadata.match_patterns
            else ["<all_urls>"]
        )

    def _get_run_at(self) -> str:
        """获取脚本运行时机"""
        run_at_map = {
            "document-start": "document_start",
            "document-end": "document_end",
            "document-idle": "document_idle",
        }
        return run_at_map.get(self.metadata.run_at, "document_end")

    def _get_js_files(self) -> List[str]:
        """获取JS文件列表（包括依赖库）"""
        js_files = []
        # 添加外部库依赖
        if self.lib_files:
            js_files.extend([f"lib/{lib}" for lib in self.lib_files])
        # 添加主脚本
        js_files.append("content.js")
        return js_files

    def save(self, output_path: Path):
        """保存manifest.json"""
        output_path.write_text(
            json.dumps(self.manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
