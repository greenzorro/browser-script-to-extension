# browser-script-to-extension

[🇬🇧 EN](https://github.com/greenzorro/browser-script-to-extension/blob/main/README.md) | [🇨🇳 中文](https://github.com/greenzorro/browser-script-to-extension/blob/main/README_ZH_CN.md)

自动将 Tampermonkey/GreaseMonkey 脚本转换为 Chrome Extension Manifest V3 格式的浏览器扩展。

## 核心价值

- 降低使用门槛：用户直接从 Chrome Web Store 安装，无需了解 Tampermonkey
- 利用浏览器应用商店生态：发现机制、信任体系、自动更新
- 拓展推广渠道：跨平台分发、可追踪数据、借助全球化网络

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 准备脚本目录

```
[你的脚本目录]/
├── 你的脚本.js              # 包含 ==UserScript== 元数据的 JS 文件
├── store_assets/
│   ├── icon.png             # 图标源文件（必需）
│   └── screenshots/         # 截图目录（至少 1 张，最多 5 张）
└── extension/               # 输出目录（自动生成）
```

### 构建扩展

```bash
python build.py /path/to/your/script-directory
```

## 使用方式

### 命令行参数

```bash
# 构建单个脚本
python build.py /path/to/your/script-directory

# 清理后重新构建
python build.py /path/to/your/script-directory --clean

# 显示详细日志
python build.py /path/to/your/script-directory --verbose
```

### 自动检测脚本

工具会自动扫描目录下所有 `.js` 文件，找到包含 `// ==UserScript==` 块的文件作为输入脚本。

## 用户脚本要求

### UserScript 元数据

你的脚本至少需要包含以下元数据：

```javascript
// ==UserScript==
// @name         你的扩展名称
// @version      1.0.0
// @description  扩展描述（Chrome Web Store 上架必需）
// @match        https://example.com/*
// ==/UserScript==

// 你的脚本代码
```

### 推荐元数据

- `@namespace`：命名空间（推荐，防止扩展 ID 冲突）
- `@author`：作者名称（推荐）
- `@license`：许可证（推荐）
- `@grant`：GM API 权限声明（默认 `none`，使用 GM API 时需要）
- `@require`：外部 JS 库依赖（可选）
- `@run-at`：运行时机（可选，默认 `document-end`）

### 支持的 GM API

| GM API | 转换方式 |
|--------|---------|
| `GM_addStyle` | 创建 `<style>` 元素注入 |
| `GM.setValue/getValue/deleteValue/listValues` | `chrome.storage.local` API |
| `GM.xmlHttpRequest` | `fetch()` API 包装 |
| `GM.notification` | `chrome.notifications.create()` |
| `GM.setClipboard` | 临时 `<textarea>` + `execCommand('copy')` |
| `GM.openInTab` | `chrome.tabs.create()` |
| `GM.download` | `chrome.downloads.download()` |

### 商店材料要求

`store_assets/` 目录必须包含：

- `icon.png`：图标源文件（必需，建议 512x512 或更高）
- `screenshots/`：截图目录（必需，至少 1 张，最多 5 张）

工具会自动从 `icon.png` 生成 16x16、48x48、128x128 三个尺寸的图标。

## 输出结果

构建成功后，`extension/` 目录包含：

```
extension/
├── manifest.json      # Chrome 扩展配置文件
├── content.js         # 转换后的脚本（包含 GM API polyfill）
├── icons/             # 自动生成的多尺寸图标
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
 └── lib/               # 外部依赖库（@require）
```

## 加载到 Chrome

1. 打开 Chrome，访问 `chrome://extensions/`
2. 启用「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择生成的 `extension/` 目录

## Chrome Web Store 上架

### 前置条件

1. 扩展名称不超过 75 字符
2. 描述非空
3. 至少 1 张截图，最多 5 张
4. 版本号格式推荐使用 x.y.z

### 注意事项

- Chrome Web Store 可能会审查 `<all_urls>` 权限，建议使用具体的 `@match` 模式
- 外部依赖（`@require`）必须符合 Chrome Web Store 政策
- 首次上架需要支付 $5 注册费（一次性）

## 常见问题

### 找不到 UserScript 文件

- 检查目录路径是否正确
- 确认 `.js` 文件包含 `// ==UserScript==` 块
- 确认文件编码为 UTF-8

### 图标生成失败

- 检查是否安装 Pillow：`pip install Pillow`
- 确认 `store_assets/icon.png` 文件存在

### 依赖下载失败

- 检查网络连接
- 确认 `@require` URL 可访问

---

Created by [Victor_42](https://victor42.work/)
