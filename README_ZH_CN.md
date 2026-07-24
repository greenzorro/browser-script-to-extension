# browser-script-to-extension

[🇬🇧 EN](https://github.com/greenzorro/browser-script-to-extension/blob/main/README.md) | [🇨🇳 中文](https://github.com/greenzorro/browser-script-to-extension/blob/main/README_ZH_CN.md)

自动将 Tampermonkey/GreaseMonkey 脚本转换为 Chrome Extension（Manifest V3）。

## 核心价值

- 降低使用门槛：用户直接从 Chrome Web Store 安装，无需 Tampermonkey
- 利用应用商店生态：发现、信任、自动更新
- 拓展分发：跨平台、可追踪

请让 Agent 按英文 README 的 `# For Agent` 在本机构建/打包。你准备好 **用户脚本 + 商店素材**，ZIP 出来后由你完成 **商店上架与审核材料**。

## 用户脚本要求（写给作者）

`.js` 至少包含：

```javascript
// ==UserScript==
// @name         你的扩展名称
// @version      1.0.0
// @description  扩展描述（上架必需）
// @match        https://example.com/*
// ==/UserScript==
```

推荐：`@namespace`、`@author`、`@license`、`@grant`（默认 `none`）、`@require`、`@run-at`、`@inject-into` / `@world`。

### 能力模型

本工具是 **商店打包流水线** + 尽力而为的 GM polyfill，不是完整 Tampermonkey 运行时。

| 路径 | 适用 | 说明 |
|------|------|------|
| **推荐** | `@grant none` + DOM / `localStorage` | 最接近扩展 content script |
| GM polyfill | `@grant GM.*` | 尽力兼容，见下表 |
| 页面 JS 对象 | CodeMirror、`window.App` 等 | `@inject-into page` / `@world MAIN` |

| 元数据 | Chrome world | 何时 |
|--------|--------------|------|
| 默认 / content / ISOLATED | `ISOLATED` | `chrome.*` / GM |
| page / MAIN | `MAIN` | 页面对象 |

`MAIN` 不能用 `chrome.*`，也不要和需要 storage/tabs/XHR 的 GM grant 混用。

`GM_getValue` 等返回 **Promise**，不要当同步 API 用；要同步状态请用 `@grant none` + `localStorage`。

### 支持的 GM API

| GM API | 策略 |
|--------|------|
| `GM_addStyle` | 注入 `<style>` |
| `GM.setValue` / `getValue` … | 异步 `chrome.storage.local` |
| `GM.xmlHttpRequest` | background `fetch()` |
| `GM.notification` / `openInTab` / `download` / `setClipboard` | 经 background 或剪贴板 API |

未支持或仅警告：`unsafeWindow`、`@resource`、同步 `GM_getValue`、二进制 XHR 等。

### 你需要准备的商店素材

在脚本项目的 `store_assets/`：

- `icon.png`（工具会生成多尺寸）
- 1–5 张截图（`.png` / `.jpg`）

### 上架注意（人）

- 名称 ≤ 75 字；描述必填 ≤ 132 字；版本建议 `x.y.z`
- 尽量用具体 `@match`，少用 `<all_urls>`
- `@require` 需符合商店政策；首次上架有一次性开发者注册费
- Agent 打出 ZIP 后，**由你**在开发者控制台填介绍、隐私问卷并提交审核

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)
