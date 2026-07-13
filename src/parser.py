"""
UserScript元数据解析器
解析Tampermonkey/GreaseMonkey脚本的==UserScript==元数据块
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path

from .gm_api import normalize_grants


@dataclass
class UserScriptMetadata:
    """UserScript元数据"""

    name: str
    namespace: str
    version: str
    description: str
    author: str
    license: str
    match_patterns: List[str]
    grant_permissions: List[str]
    require_urls: List[str]
    resource_urls: List[str]
    connect_urls: List[str]
    run_at: str
    icon_url: Optional[str]
    update_url: Optional[str]
    download_url: Optional[str]
    support_url: Optional[str]
    homepage_url: Optional[str]
    raw_metadata: Dict[str, List[str]]

    def uses_gm_api(self) -> bool:
        """是否使用了GM API"""
        return any(
            grant != "none" and grant.startswith("GM")
            for grant in self.grant_permissions
        )

    def get_required_apis(self) -> List[str]:
        """获取需要的GM API列表（canonical 下划线形式）"""
        from .gm_api import required_gm_apis

        return required_gm_apis(self.grant_permissions)


class UserScriptParser:
    """UserScript解析器"""

    METADATA_BLOCK_PATTERN = re.compile(
        r"// ==UserScript==\n(.*?)// ==/UserScript==", re.DOTALL
    )

    METADATA_LINE_PATTERN = re.compile(r"// @(\S+)\s+(.+)")

    def __init__(self, script_path: Path):
        self.script_path = script_path
        self.metadata: Optional[UserScriptMetadata] = None

    def parse(self) -> UserScriptMetadata:
        """解析脚本文件，提取元数据"""
        content = self.script_path.read_text(encoding="utf-8")
        metadata_block = self._extract_metadata_block(content)
        raw_metadata = self._parse_metadata_lines(metadata_block)

        match_patterns = self._collect_match_patterns(raw_metadata)
        grants = normalize_grants(self._get_all_values(raw_metadata, "grant", ["none"]))
        if not grants:
            grants = ["none"]

        self.metadata = UserScriptMetadata(
            name=self._get_first_value(raw_metadata, "name", "Unnamed Script"),
            namespace=self._get_first_value(raw_metadata, "namespace", ""),
            version=self._get_first_value(raw_metadata, "version", "1.0.0"),
            description=self._get_first_value(raw_metadata, "description", ""),
            author=self._get_first_value(raw_metadata, "author", ""),
            license=self._get_first_value(raw_metadata, "license", "MIT"),
            match_patterns=match_patterns,
            grant_permissions=grants,
            require_urls=self._get_all_values(raw_metadata, "require", []),
            resource_urls=self._get_all_values(raw_metadata, "resource", []),
            connect_urls=self._get_all_values(raw_metadata, "connect", []),
            run_at=self._parse_run_at(raw_metadata),
            icon_url=self._get_first_value(raw_metadata, "icon"),
            update_url=self._get_first_value(raw_metadata, "updateURL"),
            download_url=self._get_first_value(raw_metadata, "downloadURL"),
            support_url=self._get_first_value(raw_metadata, "supportURL"),
            homepage_url=self._get_first_value(raw_metadata, "homepage")
            or self._get_first_value(raw_metadata, "homepageURL"),
            raw_metadata=raw_metadata,
        )
        return self.metadata

    def extract_code_body(self) -> str:
        """提取脚本主体代码（去除元数据块）"""
        content = self.script_path.read_text(encoding="utf-8")
        code = self.METADATA_BLOCK_PATTERN.sub("", content)
        return code.strip()

    def _extract_metadata_block(self, content: str) -> str:
        match = self.METADATA_BLOCK_PATTERN.search(content)
        if not match:
            raise ValueError(
                f"No UserScript metadata block found in {self.script_path}"
            )
        return match.group(1)

    def _parse_metadata_lines(self, block: str) -> Dict[str, List[str]]:
        metadata: Dict[str, List[str]] = {}
        for line in block.split("\n"):
            line = line.strip()
            match = self.METADATA_LINE_PATTERN.match(line)
            if match:
                key, value = match.groups()
                metadata.setdefault(key, []).append(value.strip())
        return metadata

    def _collect_match_patterns(self, raw_metadata: Dict) -> List[str]:
        """合并 @match 与 @include，并记录 @exclude（exclude 在 manifest 侧处理）"""
        patterns: List[str] = []
        for key in ("match", "include"):
            for value in self._get_all_values(raw_metadata, key, []):
                if value and value not in patterns:
                    patterns.append(value)
        return patterns

    def get_exclude_patterns(self) -> List[str]:
        """从 raw metadata 读取 @exclude"""
        if not self.metadata:
            return []
        return list(self.metadata.raw_metadata.get("exclude", []))

    def _get_first_value(self, metadata: Dict, key: str, default=None):
        values = metadata.get(key, [])
        return values[0] if values else default

    def _get_all_values(self, metadata: Dict, key: str, default=None):
        if default is not None:
            return list(metadata.get(key, default))
        return list(metadata.get(key, []))

    def _parse_run_at(self, metadata: Dict) -> str:
        for key in ["run-at", "runAt"]:
            if key in metadata:
                return metadata[key][0]
        return "document-end"
