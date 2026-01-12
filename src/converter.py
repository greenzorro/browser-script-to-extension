"""
代码转换器
处理UserScript代码，注入GM API polyfill
"""

from pathlib import Path
from typing import List
from .parser import UserScriptMetadata


class CodeConverter:
    """脚本代码转换器"""

    def __init__(self, metadata: UserScriptMetadata):
        self.metadata = metadata

    def convert(self, code_body: str) -> str:
        """转换脚本代码，添加必要的polyfill"""
        parts = []

        # 1. 添加GM API polyfill（如果需要）
        if self.metadata.uses_gm_api():
            polyfill = self._generate_polyfill()
            if polyfill:
                parts.append(polyfill)

        # 2. 添加原始代码
        parts.append(code_body)

        return '\n\n'.join(parts)

    def _generate_polyfill(self) -> str:
        """生成GM API polyfill代码"""
        needed_apis = self.metadata.get_required_apis()

        if not needed_apis:
            return ''

        # 构建polyfill代码
        polyfill_parts = [
            '// ===== GM API Polyfill for Browser Extensions =====',
            '(function() {',
            '    "use strict";',
            ''
        ]

        # 为每个需要的API生成polyfill
        for api in needed_apis:
            api_polyfill = self._get_api_polyfill(api)
            if api_polyfill:
                polyfill_parts.append(api_polyfill)

        polyfill_parts.append('})();')

        return '\n'.join(polyfill_parts)

    def _get_api_polyfill(self, api: str) -> str:
        """获取特定API的polyfill代码"""
        polyfills = {
            'GM_addStyle': '''    // GM_addStyle polyfill
    if (typeof GM_addStyle === 'undefined') {
        window.GM_addStyle = function(css) {
            const style = document.createElement('style');
            style.textContent = css;
            document.head.appendChild(style);
            return style;
        };
    }''',

            'GM.setValue': '''    // GM.setValue polyfill
    if (typeof GM === 'undefined' || !GM.setValue) {
        window.GM = window.GM || {};
        GM.setValue = async function(key, value) {
            return new Promise((resolve) => {
                chrome.storage.local.set({[key]: value}, () => resolve());
            });
        };
    }''',

            'GM.getValue': '''    // GM.getValue polyfill
    if (typeof GM === 'undefined' || !GM.getValue) {
        window.GM = window.GM || {};
        GM.getValue = async function(key, defaultValue) {
            return new Promise((resolve) => {
                chrome.storage.local.get([key], (result) => {
                    resolve(key in result ? result[key] : defaultValue);
                });
            });
        };
    }''',

            'GM.deleteValue': '''    // GM.deleteValue polyfill
    if (typeof GM === 'undefined' || !GM.deleteValue) {
        window.GM = window.GM || {};
        GM.deleteValue = async function(key) {
            return new Promise((resolve) => {
                chrome.storage.local.remove([key], () => resolve());
            });
        };
    }''',

            'GM.listValues': '''    // GM.listValues polyfill
    if (typeof GM === 'undefined' || !GM.listValues) {
        window.GM = window.GM || {};
        GM.listValues = async function() {
            return new Promise((resolve) => {
                chrome.storage.local.get(null, (items) => {
                    resolve(Object.keys(items));
                });
            });
        };
    }''',

            'GM.xmlHttpRequest': '''    // GM.xmlHttpRequest polyfill
    if (typeof GM === 'undefined' || !GM.xmlHttpRequest) {
        window.GM = window.GM || {};
        GM.xmlHttpRequest = function(details) {
            fetch(details.url, {
                method: details.method || 'GET',
                headers: details.headers || {},
                body: details.data
            }).then(response => response.text()).then(text => {
                if (details.onload) {
                    details.onload({
                        status: 200,
                        statusText: 'OK',
                        responseText: text,
                        response: text
                    });
                }
            }).catch(error => {
                if (details.onerror) {
                    details.onerror(error);
                }
            });
        };
    }''',

            'GM.notification': '''    // GM.notification polyfill
    if (typeof GM === 'undefined' || !GM.notification) {
        window.GM = window.GM || {};
        GM.notification = function(options) {
            chrome.notifications.create({
                type: 'basic',
                iconUrl: options.image || '',
                title: options.title || '',
                message: options.text || ''
            });
        };
    }''',

            'GM.setClipboard': '''    // GM.setClipboard polyfill
    if (typeof GM === 'undefined' || !GM.setClipboard) {
        window.GM = window.GM || {};
        GM.setClipboard = function(text) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        };
    }''',

            'GM.openInTab': '''    // GM.openInTab polyfill
    if (typeof GM === 'undefined' || !GM.openInTab) {
        window.GM = window.GM || {};
        GM.openInTab = function(url, options) {
            const background = options && options.background;
            chrome.tabs.create({ url: url, active: !background });
        };
    }''',

            'GM.download': '''    // GM.download polyfill
    if (typeof GM === 'undefined' || !GM.download) {
        window.GM = window.GM || {};
        GM.download = function(details) {
            chrome.downloads.download({
                url: details.url,
                filename: details.name,
                saveAs: details.saveAs || false
            }, details.onload || (() => {}));
        };
    }''',
        }

        return polyfills.get(api, '')

    def save(self, code: str, output_path: Path):
        """保存转换后的代码"""
        output_path.write_text(code, encoding='utf-8')
