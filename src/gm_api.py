"""
GM API 归一化与权限映射
统一处理 GM_xxx / GM.xxx 两种 grant 写法
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple


# 需要 background service worker 转发的 API（与 GmApiSpec.needs_background 保持一致）
BACKGROUND_APIS = frozenset(
    {
        "GM_xmlHttpRequest",
        "GM_openInTab",
        "GM_notification",
        "GM_download",
    }
)


@dataclass(frozen=True)
class GmApiSpec:
    """单个 GM API 的规范描述"""

    canonical: str  # 统一用下划线形式，如 GM_setValue
    permissions: Tuple[str, ...] = ()
    host_permissions: Tuple[str, ...] = ()
    needs_background: bool = False


# 权威映射表：canonical name -> spec
# 同时登记常见别名（点号写法）
_API_SPECS: Dict[str, GmApiSpec] = {
    "GM_addStyle": GmApiSpec("GM_addStyle"),
    "GM_setValue": GmApiSpec("GM_setValue", permissions=("storage",)),
    "GM_getValue": GmApiSpec("GM_getValue", permissions=("storage",)),
    "GM_deleteValue": GmApiSpec("GM_deleteValue", permissions=("storage",)),
    "GM_listValues": GmApiSpec("GM_listValues", permissions=("storage",)),
    "GM_xmlHttpRequest": GmApiSpec(
        "GM_xmlHttpRequest",
        host_permissions=("<all_urls>",),
        needs_background=True,
    ),
    "GM_notification": GmApiSpec(
        "GM_notification",
        permissions=("notifications",),
        needs_background=True,
    ),
    "GM_setClipboard": GmApiSpec(
        "GM_setClipboard", permissions=("clipboardWrite",)
    ),
    "GM_openInTab": GmApiSpec(
        "GM_openInTab", permissions=("tabs",), needs_background=True
    ),
    "GM_download": GmApiSpec(
        "GM_download",
        permissions=("downloads",),
        host_permissions=("<all_urls>",),
        needs_background=True,
    ),
}


def normalize_grant(grant: str) -> str:
    """
    将 grant 归一为 canonical 下划线形式。
    例: GM.setValue -> GM_setValue, GM_xmlHttpRequest 保持不变
    """
    g = (grant or "").strip()
    if not g or g == "none":
        return g
    # unsafeWindow 等非 GM 权限原样返回
    if g.startswith("GM."):
        return "GM_" + g[3:]
    if g.startswith("GM_"):
        return g
    # 少数脚本写 GMXxx 无下划线
    if g.startswith("GM") and len(g) > 2 and g[2].isupper():
        return "GM_" + g[2:]
    return g


def normalize_grants(grants: Iterable[str]) -> List[str]:
    """归一化 grant 列表，去重并保持顺序"""
    seen: Set[str] = set()
    result: List[str] = []
    for g in grants:
        n = normalize_grant(g)
        if not n or n in seen:
            continue
        seen.add(n)
        result.append(n)
    return result


def is_gm_api_grant(grant: str) -> bool:
    n = normalize_grant(grant)
    return bool(n) and n != "none" and n.startswith("GM")


def get_api_spec(grant: str) -> GmApiSpec | None:
    n = normalize_grant(grant)
    return _API_SPECS.get(n)


def collect_permissions(grants: Iterable[str]) -> List[str]:
    perms: Set[str] = set()
    for g in grants:
        spec = get_api_spec(g)
        if spec:
            perms.update(spec.permissions)
    return sorted(perms)


def collect_host_permissions_from_grants(grants: Iterable[str]) -> List[str]:
    hosts: Set[str] = set()
    for g in grants:
        spec = get_api_spec(g)
        if spec:
            hosts.update(spec.host_permissions)
    return sorted(hosts)


def needs_background(grants: Iterable[str]) -> bool:
    return any(
        (spec := get_api_spec(g)) is not None and spec.needs_background
        for g in grants
    )


def required_gm_apis(grants: Iterable[str]) -> List[str]:
    """返回需要 polyfill 的 canonical API 列表"""
    result: List[str] = []
    seen: Set[str] = set()
    for g in grants:
        n = normalize_grant(g)
        if not is_gm_api_grant(n):
            continue
        if n in seen:
            continue
        # 仅对有实现的 API 生成 polyfill
        if n in _API_SPECS:
            seen.add(n)
            result.append(n)
    return result


def connect_to_host_permission(connect: str) -> str | None:
    """
    将 UserScript @connect 值转为 Chrome host_permissions 模式。
    返回 None 表示无法安全转换（应跳过或报错由调用方决定）。
    """
    c = (connect or "").strip()
    if not c:
        return None
    if c in ("*", "<all_urls>"):
        return "<all_urls>"
    if c.startswith("*://") or c.startswith("http://") or c.startswith("https://"):
        # 已是 URL 模式
        if c.endswith("/*") or c.endswith("/"):
            return c if "*" in c or c.endswith("/*") else c.rstrip("/") + "/*"
        if "/" not in c.split("://", 1)[-1]:
            return c + "/*"
        return c
    # 纯域名 / 通配域名
    if c.startswith("."):
        # .example.com -> *://*.example.com/*
        return f"*://*{c}/*"
    if "/" in c or ":" in c:
        # 非法或过于复杂，拒绝
        return None
    return f"*://{c}/*"
