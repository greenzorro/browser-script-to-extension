"""
代码转换器
处理UserScript代码，注入GM API polyfill；
需要 background 的 API 通过 runtime 消息桥转发。
"""

from pathlib import Path
from typing import List

from .parser import UserScriptMetadata
from .gm_api import needs_background


class CodeConverter:
    """脚本代码转换器"""

    def __init__(self, metadata: UserScriptMetadata):
        self.metadata = metadata

    def convert(self, code_body: str) -> str:
        parts: List[str] = []

        if self.metadata.uses_gm_api():
            polyfill = self._generate_polyfill()
            if polyfill:
                parts.append(polyfill)

        parts.append(code_body)
        return "\n\n".join(parts)

    def _generate_polyfill(self) -> str:
        needed_apis = self.metadata.get_required_apis()
        if not needed_apis:
            return ""

        polyfill_parts = [
            "// ===== GM API Polyfill for Browser Extensions =====",
            "(function() {",
            '    "use strict";',
            "",
            "    // 统一命名空间：同时暴露 GM.* 与 GM_*",
            "    window.GM = window.GM || {};",
            "",
        ]

        for api in needed_apis:
            api_polyfill = self._get_api_polyfill(api)
            if api_polyfill:
                polyfill_parts.append(api_polyfill)
                polyfill_parts.append("")

        # 别名：GM_xxx <-> GM.xxx
        polyfill_parts.append(self._alias_block(needed_apis))
        polyfill_parts.append("})();")
        return "\n".join(polyfill_parts)

    def _alias_block(self, apis: List[str]) -> str:
        lines = ["    // Bidirectional aliases GM_xxx <-> GM.xxx"]
        for api in apis:
            if not api.startswith("GM_"):
                continue
            short = api[3:]  # setValue
            lines.append(
                f"    if (typeof window.{api} === 'function') {{ "
                f"window.GM.{short} = window.GM.{short} || window.{api}; }}"
            )
            lines.append(
                f"    if (typeof window.GM.{short} === 'function') {{ "
                f"window.{api} = window.{api} || window.GM.{short}; }}"
            )
        return "\n".join(lines)

    def _get_api_polyfill(self, api: str) -> str:
        polyfills = {
            "GM_addStyle": """    // GM_addStyle
    if (typeof GM_addStyle === 'undefined') {
        window.GM_addStyle = function(css) {
            const style = document.createElement('style');
            style.textContent = css;
            (document.head || document.documentElement).appendChild(style);
            return style;
        };
    }""",
            "GM_setValue": """    // GM_setValue / GM.setValue
    if (typeof GM_setValue === 'undefined') {
        window.GM_setValue = function(key, value) {
            return new Promise((resolve, reject) => {
                try {
                    chrome.storage.local.set({[key]: value}, () => {
                        if (chrome.runtime.lastError) {
                            reject(chrome.runtime.lastError);
                        } else {
                            resolve();
                        }
                    });
                } catch (e) { reject(e); }
            });
        };
    }""",
            "GM_getValue": """    // GM_getValue / GM.getValue
    if (typeof GM_getValue === 'undefined') {
        window.GM_getValue = function(key, defaultValue) {
            return new Promise((resolve, reject) => {
                try {
                    chrome.storage.local.get([key], (result) => {
                        if (chrome.runtime.lastError) {
                            reject(chrome.runtime.lastError);
                        } else {
                            resolve(Object.prototype.hasOwnProperty.call(result, key)
                                ? result[key] : defaultValue);
                        }
                    });
                } catch (e) { reject(e); }
            });
        };
    }""",
            "GM_deleteValue": """    // GM_deleteValue / GM.deleteValue
    if (typeof GM_deleteValue === 'undefined') {
        window.GM_deleteValue = function(key) {
            return new Promise((resolve, reject) => {
                try {
                    chrome.storage.local.remove([key], () => {
                        if (chrome.runtime.lastError) {
                            reject(chrome.runtime.lastError);
                        } else {
                            resolve();
                        }
                    });
                } catch (e) { reject(e); }
            });
        };
    }""",
            "GM_listValues": """    // GM_listValues / GM.listValues
    if (typeof GM_listValues === 'undefined') {
        window.GM_listValues = function() {
            return new Promise((resolve, reject) => {
                try {
                    chrome.storage.local.get(null, (items) => {
                        if (chrome.runtime.lastError) {
                            reject(chrome.runtime.lastError);
                        } else {
                            resolve(Object.keys(items || {}));
                        }
                    });
                } catch (e) { reject(e); }
            });
        };
    }""",
            "GM_xmlHttpRequest": """    // GM_xmlHttpRequest / GM.xmlHttpRequest
    if (typeof GM_xmlHttpRequest === 'undefined') {
        window.GM_xmlHttpRequest = function(details) {
            const method = (details.method || 'GET').toUpperCase();
            const controller = typeof AbortController !== 'undefined'
                ? new AbortController() : null;
            const init = {
                method: method,
                headers: details.headers || {},
                body: details.data,
                credentials: details.anonymous ? 'omit' : 'include',
            };
            if (controller) init.signal = controller.signal;

            const promise = fetch(details.url, init)
                .then(async (response) => {
                    const responseText = await response.text();
                    const headersObj = {};
                    response.headers.forEach((v, k) => { headersObj[k] = v; });
                    const result = {
                        status: response.status,
                        statusText: response.statusText,
                        responseText: responseText,
                        response: responseText,
                        responseHeaders: Object.entries(headersObj)
                            .map(([k, v]) => k + ': ' + v).join('\\r\\n'),
                        finalUrl: response.url,
                        readyState: 4,
                    };
                    if (details.onload) details.onload(result);
                    return result;
                })
                .catch((error) => {
                    if (details.onerror) details.onerror(error);
                    throw error;
                });

            return {
                abort: function() { if (controller) controller.abort(); },
                then: promise.then.bind(promise),
                catch: promise.catch.bind(promise),
            };
        };
    }""",
            "GM_notification": """    // GM_notification / GM.notification -> background
    if (typeof GM_notification === 'undefined') {
        window.GM_notification = function(options, ondone, onclick) {
            let opts = options;
            if (typeof options === 'string') {
                opts = { text: options, title: ondone, image: onclick };
            }
            return chrome.runtime.sendMessage({
                type: 'GM_notification',
                options: {
                    title: (opts && opts.title) || '',
                    text: (opts && (opts.text || opts.body)) || '',
                    image: (opts && (opts.image || opts.icon)) || '',
                }
            });
        };
    }""",
            "GM_setClipboard": """    // GM_setClipboard / GM.setClipboard
    if (typeof GM_setClipboard === 'undefined') {
        window.GM_setClipboard = async function(text) {
            const value = String(text == null ? '' : text);
            if (navigator.clipboard && navigator.clipboard.writeText) {
                try {
                    await navigator.clipboard.writeText(value);
                    return;
                } catch (e) { /* fallback */ }
            }
            const textarea = document.createElement('textarea');
            textarea.value = value;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        };
    }""",
            "GM_openInTab": """    // GM_openInTab / GM.openInTab -> background
    if (typeof GM_openInTab === 'undefined') {
        window.GM_openInTab = function(url, options) {
            // boolean second arg = open_in_background (Tampermonkey/GreaseMonkey)
            let background = false;
            if (typeof options === 'boolean') {
                background = options;
            } else if (options && typeof options === 'object') {
                background = !!(options.background || options.loadInBackground
                    || options.open_in_background);
                if (options.active === true) background = false;
                if (options.active === false) background = true;
            }
            return chrome.runtime.sendMessage({
                type: 'GM_openInTab',
                url: url,
                active: !background,
            });
        };
    }""",
            "GM_download": """    // GM_download / GM.download -> background
    if (typeof GM_download === 'undefined') {
        window.GM_download = function(details, name) {
            let opts = details;
            if (typeof details === 'string') {
                opts = { url: details, name: name };
            }
            return chrome.runtime.sendMessage({
                type: 'GM_download',
                details: {
                    url: opts.url,
                    name: opts.name || opts.filename,
                    saveAs: !!opts.saveAs,
                }
            }).then(function(result) {
                if (opts.onload) opts.onload(result);
                return result;
            }).catch(function(err) {
                if (opts.onerror) opts.onerror(err);
                throw err;
            });
        };
    }""",
        }
        return polyfills.get(api, "")

    def generate_background_script(self) -> str:
        """生成 background service worker 源码"""
        return """// Auto-generated background service worker for GM API bridge
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    return false;
  }

  if (message.type === 'GM_openInTab') {
    chrome.tabs.create(
      { url: message.url, active: message.active !== false },
      (tab) => {
        if (chrome.runtime.lastError) {
          sendResponse({ ok: false, error: chrome.runtime.lastError.message });
        } else {
          sendResponse({ ok: true, tabId: tab && tab.id });
        }
      }
    );
    return true;
  }

  if (message.type === 'GM_notification') {
    const opts = message.options || {};
    const createOptions = {
      type: 'basic',
      title: opts.title || 'Notification',
      message: opts.text || '',
    };
    if (opts.image) {
      createOptions.iconUrl = opts.image;
    }
    chrome.notifications.create(createOptions, (id) => {
      if (chrome.runtime.lastError) {
        sendResponse({ ok: false, error: chrome.runtime.lastError.message });
      } else {
        sendResponse({ ok: true, id: id });
      }
    });
    return true;
  }

  if (message.type === 'GM_download') {
    const d = message.details || {};
    const downloadOpts = { url: d.url, saveAs: !!d.saveAs };
    if (d.name) downloadOpts.filename = d.name;
    chrome.downloads.download(downloadOpts, (downloadId) => {
      if (chrome.runtime.lastError) {
        sendResponse({ ok: false, error: chrome.runtime.lastError.message });
      } else {
        sendResponse({ ok: true, downloadId: downloadId });
      }
    });
    return true;
  }

  return false;
});
"""

    def needs_background(self) -> bool:
        return needs_background(self.metadata.grant_permissions)

    def save(self, code: str, output_path: Path):
        output_path.write_text(code, encoding="utf-8")

    def save_background(self, output_path: Path):
        output_path.write_text(self.generate_background_script(), encoding="utf-8")
