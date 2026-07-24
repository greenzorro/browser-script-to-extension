# browser-script-to-extension

[🇬🇧 EN](https://github.com/greenzorro/browser-script-to-extension/blob/main/README.md) | [🇨🇳 中文](https://github.com/greenzorro/browser-script-to-extension/blob/main/README_ZH_CN.md)

自动将 Tampermonkey/GreaseMonkey 脚本转换为 Chrome Extension（Manifest V3）。

## 核心价值

- **降低使用门槛：** 用户直接从 Chrome Web Store 安装，无需 Tampermonkey
- **商店生态：** 发现机制、信任体系、自动更新
- **更广分发：** 跨平台分发与可追踪数据

请让 Agent 在本机构建/打包（见英文 README 文末 `# For Agent`）。你准备好 **用户脚本 + 商店素材**，ZIP 出来后由你完成 **Web Store 上架与审核**。

## 用户脚本要求（写给作者）

你的 `.js` **必须**包含：

```javascript
// ==UserScript==
// @name         Extension Name
// @version      1.0.0
// @description  Description (Required for Web Store)
// @match        https://example.com/*
// ==/UserScript==
```

推荐：`@namespace`、`@author`、`@license`、`@grant`（默认 `none`）、`@require`、`@run-at`、`@inject-into` / `@world`。

### 能力模型

本工具是 **Web Store 打包流水线**，并提供尽力而为的 GM polyfill——不是完整 Tampermonkey 运行时。

| 路径 | 适用 | 说明 |
|------|------|------|
| **推荐** | `@grant none` + DOM / `localStorage` | 最接近扩展 content script |
| GM polyfill | `@grant GM.*` | 尽力兼容，见下表 |
| 页面 JS 对象 | CodeMirror、`window.App` 等 | `@inject-into page` 或 `@world MAIN` |

| 元数据 | Chrome `content_scripts.world` | 何时使用 |
|--------|--------------------------------|----------|
| （默认）/ `@inject-into content` / `@world ISOLATED` | `ISOLATED` | `chrome.*` / GM polyfill |
| `@inject-into page` / `@world MAIN` | `MAIN` | 页面 JS 对象 |

`MAIN` 不能使用 `chrome.*`。不要把 `MAIN` 与需要 storage / tabs / XHR 的 GM grant 混用。

`GM_setValue` / `GM_getValue` / `GM.deleteValue` / `GM.listValues` 返回 **Promise**（非同步）：

```js
const x = await GM_getValue('k', 0);
```

若要同步状态，使用 `@grant none` + `localStorage`。

### 支持的 GM API

同时接受 `GM_xxx` 与 `GM.xxx` 两种 `@grant` 写法。

| GM API | Polyfill 策略 |
|--------|----------------|
| `GM_addStyle` / `GM.addStyle` | 注入 `<style>` |
| `GM.setValue` / `getValue` … | **异步** `chrome.storage.local` |
| `GM.xmlHttpRequest` | Background `fetch()`（配合 `host_permissions` / `@connect`） |
| `GM.notification` | `chrome.notifications` |
| `GM.setClipboard` | `navigator.clipboard` + fallback |
| `GM.openInTab` | `chrome.tabs.create` |
| `GM.download` | `chrome.downloads.download` |

未支持（或仅警告）：`unsafeWindow`、`@resource` / `GM_getResource*`、同步 `GM_getValue`、二进制 XHR `responseType`、跨上下文 XHR abort。

### 你需要准备的商店素材

在脚本项目的 `store_assets/` 中：

- **`icon.png`**（源图；工具会生成 16/48/128）
- **1–5 张截图**（`.png` / `.jpg`）

### 上架注意（人 / 商店）

- 名称 ≤ 75 字符；描述必填 ≤ 132 字符；版本建议 SemVer `x.y.z`
- 尽量用具体 `@match`，少用 `<all_urls>`，审核更快
- 远程 `@require` 须符合商店政策
- Chrome Web Store 一次性约 $5 开发者注册费
- Agent 打出 ZIP 后，**由你**在开发者控制台提交介绍文案、隐私问卷与截图

## 手动命令行

依赖装好后，你也可以自己跑同样的构建：

```bash
python build.py /path/to/project_root
python build.py /path/to/project_root --clean
python build.py /path/to/project_root --verbose
python build.py /path/to/project_root --package
python build.py /path/to/project_root --refresh-dependencies
```

`--package` 需要 `store_assets/upload_config.json` 才会打 ZIP 并打开上传页。

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)
