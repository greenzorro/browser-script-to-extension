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
│   ├── screenshot1.png      # 截图文件（必需，至少1张，最多5张）
│   └── screenshot2.png      # 可选
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

# 构建并打包（生成ZIP并打开上传页面）
python build.py /path/to/your/script-directory --package
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
- `@inject-into` / `@world`：执行世界（见下方）

### 能力模型

本工具是 **Chrome Web Store 打包流水线**，并提供尽力而为的 GM polyfill，不是完整 Tampermonkey 运行时。

| 路径 | 适用 | 说明 |
|------|------|------|
| **推荐主路径** | `@grant none` + DOM / `localStorage` | 与扩展 content script 最接近 |
| GM polyfill | `@grant GM.*` | 尽力兼容，见下表 |
| 页面 JS 对象 | CodeMirror、`window.App` 等 | `@inject-into page` 或 `@world MAIN` |

**执行世界**

| 元数据 | Chrome `content_scripts.world` | 何时使用 |
|--------|--------------------------------|----------|
| 默认 / `@inject-into content` / `@world ISOLATED` | `ISOLATED` | `chrome.*` / GM polyfill |
| `@inject-into page` / `@world MAIN` | `MAIN` | 页面 JS 对象（如 `element.CodeMirror`） |

`MAIN` 中不可用 `chrome.*`。不要与依赖 storage / tabs / XHR 的 GM grant 混用。

**Storage 语义**

`GM_setValue` / `GM_getValue` / `GM.deleteValue` / `GM.listValues` 返回 **Promise**（GM4 / `chrome.storage.local` 风格）：

```js
// 不支持（同步）
const x = GM_getValue('k', 0);

// 支持
const x = await GM_getValue('k', 0);
// 或: GM_getValue('k', 0).then(...)
```

需要同步状态时使用 `@grant none` + `localStorage`。

### 支持的 GM API

同时支持 `GM_xxx` 与 `GM.xxx` 两种 `@grant` 写法（会自动归一化）。

| GM API | 转换方式 |
|--------|---------|
| `GM_addStyle` / `GM.addStyle` | 创建 `<style>` 元素注入 |
| `GM.setValue/getValue/deleteValue/listValues` | **异步** `chrome.storage.local`（Promise） |
| `GM.xmlHttpRequest` | 经 background service worker → `fetch()`（配合 `host_permissions` / `@connect` 实现跨域） |
| `GM.notification` | 经 background → `chrome.notifications` |
| `GM.setClipboard` | `navigator.clipboard`（失败则 fallback） |
| `GM.openInTab` | 经 background → `chrome.tabs.create` |
| `GM.download` | 经 background → `chrome.downloads.download` |

需要 XHR / `tabs` / `notifications` / `downloads` 时会自动生成 `background.js` 消息桥。

未支持（或仅 warning）：`unsafeWindow`、`@resource` / `GM_getResource*`、同步 `GM_getValue`、二进制 XHR `responseType`、跨上下文 XHR abort。

### 商店材料要求

`store_assets/` 目录必须包含：

- `icon.png`：图标源文件（必需，建议 512x512 或更高）
- 截图文件：至少 1 张，最多 5 张（支持 `.png` 或 `.jpg` 格式，直接放在 `store_assets/` 目录下）

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
2. 描述非空，且不超过 132 字符
3. 至少 1 张截图，最多 5 张
4. 版本号格式推荐使用 x.y.z

### 注意事项

- Chrome Web Store 可能会审查 `<all_urls>` 权限，建议使用具体的 `@match` 模式
- 外部依赖（`@require`）必须符合 Chrome Web Store 政策
- 首次上架需要支付 $5 注册费（一次性）

## 打包发布

### 快速打包

工具可以自动将 `extension/` 目录打包成 ZIP 文件，并打开浏览器跳转到上传页面：

```bash
python build.py /path/to/your/script-directory --package
```

### 配置上传页面

在 `store_assets/` 目录创建 `upload_config.json`：

```json
{
  "zip_filename": "我的扩展",
  "output_path": "~/Downloads",
  "upload_urls": [
    "https://chrome.google.com/webstore/devconsole/xxx/edit/package",
    "https://partner.microsoft.com/.../packages"
  ]
}
```

**配置说明：**

| 字段 | 必需 | 说明 |
|------|------|------|
| `zip_filename` | 可选 | ZIP 文件名（不含 .zip），默认与脚本文件同名 |
| `output_path` | 可选 | 输出路径（见下方路径格式说明） |
| `upload_urls` | 必需 | 上传页面 URL 数组 |

**路径格式说明：**
- **跨平台推荐**：`~/Downloads`（自动扩展为用户主目录）
- **相对路径**：`../releases`
- **绝对路径**：统一使用正斜杠 `/`，Windows 也支持（如 `C:/Users/xxx/Downloads`）
- ❌ 不要使用反斜杠 `\`（JSON 中需要转义，且不跨平台）

**默认行为：**

- 无配置文件时：使用脚本文件名作为 ZIP 名，输出到项目根目录，不打开上传页面
- WSL 环境：打印 URL，不自动打开浏览器

## 常见问题

### 找不到 UserScript 文件

- 检查目录路径是否正确
- 确认 `.js` 文件包含 `// ==UserScript==` 块
- 确认文件编码为 UTF-8
- 错误信息会列出每个 `.js` 被跳过的原因

### 图标生成失败

- 检查是否安装 Pillow：`pip install Pillow`
- 确认 `store_assets/icon.png` 文件存在

### 依赖下载失败

- 检查网络连接
- 确认 `@require` URL 可访问

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)
