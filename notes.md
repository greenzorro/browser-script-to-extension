# browser-script-to-extension 项目备忘录

## 1. 目的

记录实现细节与架构决策，便于维护。功能变更时同步更新本文档。

## 2. 项目概述

将 Tampermonkey / GreaseMonkey userscript 转为 Chrome Extension Manifest V3。

**定位：** Chrome Web Store **打包流水线**（元数据 → manifest、素材校验、依赖内联、ZIP 发布），附带尽力而为的 GM API polyfill。不是完整 TM 运行时仿真。

**核心价值：**
- 降低使用门槛：用户从 Web Store 安装，无需 Tampermonkey
- 利用商店生态：发现、信任、自动更新
- 拓展分发渠道

**推荐脚本形态：** `@grant none` + DOM / `localStorage`（与扩展 content script 模型最接近）。

## 3. 技术栈

- **Python 3.12+**
- **dataclasses** / **re** / **json**
- **requests**：`@require` 下载
- **Pillow**：图标尺寸

## 4. 目录结构

```
browser-script-to-extension/
├── build.py                  # 主入口
├── notes.md                  # 本备忘录
├── README.md / README_ZH_CN.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── parser.py             # UserScript 元数据解析
│   ├── gm_api.py             # grant 归一化与权限映射
│   ├── manifest.py           # manifest.json 生成
│   ├── converter.py          # GM polyfill + background 桥
│   ├── fetcher.py            # @require 下载
│   ├── validator.py          # 上架校验
│   └── packager.py           # ZIP / 打开上传页
└── utils/
    ├── __init__.py
    └── image.py              # 图标多尺寸
```

**用户脚本目录：**
```
[path/to/script-directory]
├── [任意名].js                 # ==UserScript== 元数据
├── store_assets/
│   ├── icon.png               # 必需
│   ├── screenshot*.png|jpg    # 至少 1 张，最多 5 张
│   └── upload_config.json     # 可选，--package 用
└── extension/                 # 构建输出
    ├── manifest.json
    ├── content.js
    ├── background.js          # 按需
    ├── icons/
    └── lib/                   # @require
```

## 5. 核心模块

### 5.1 元数据解析器 (`src/parser.py`)

- 元数据块：`// ==UserScript==\n(.*?)// ==/UserScript==`
- 元数据行：`// @(\S+)\s+(.+)`
- 多值：`@match` / `@include`、`@grant`、`@require`、`@connect`、`@exclude`、`@resource`
- 默认：`version=1.0.0`，`description=""`，`license=MIT`，`run_at=document-end`，`execution_world=ISOLATED`

**执行世界：**
| 元数据 | 结果 |
|--------|------|
| 默认 / `@world ISOLATED` / `@inject-into content` | `ISOLATED` |
| `@world MAIN` / `@inject-into page` | `MAIN` |
| `@inject-into auto` | `ISOLATED`（保守） |

`MAIN` 可访问页面 JS 对象（如 `element.CodeMirror`）；不可用 `chrome.*` / 依赖扩展 API 的 GM polyfill。

### 5.2 Manifest V3 (`src/manifest.py`)

| GM API | Chrome |
|--------|--------|
| `GM_addStyle` | 无额外权限 |
| storage 系 | `permissions: ["storage"]` |
| `GM_xmlHttpRequest` | `host_permissions`（含 `<all_urls>`）+ background |
| `GM_notification` | `notifications` + background |
| `GM_setClipboard` | `clipboardWrite` |
| `GM_openInTab` | `tabs` + background |
| `GM_download` | `downloads` + host + background |

- 空 `permissions` / `host_permissions` 省略
- 无 `@match`/`@include` 时拒绝构建（不默认 `<all_urls>`）
- `execution_world=MAIN` 时写入 `content_scripts[].world`
- `@exclude` → `exclude_matches`

### 5.3 GM API 映射 (`src/gm_api.py`)

- `GM_xxx` / `GM.xxx` / 少数 `GMXxx` 归一为 canonical 下划线名
- 权限与 host 从 `_API_SPECS` 收集
- `@connect` → host_permissions 模式

**走 background 的 API：** `GM_xmlHttpRequest`、`GM_openInTab`、`GM_notification`、`GM_download`。

MV3 下 content script 的网络请求仍受页面 CORS 约束；特权跨域只在 extension page / service worker 中可用，故 XHR 与 tabs/notifications/downloads 一样经消息桥转发。

### 5.4 代码转换器 (`src/converter.py`)

- storage：`chrome.storage.local`，**Promise 异步**（对齐 GM4 `GM.*`）
- XHR / openInTab / notification / download：content → `runtime.sendMessage` → `background.js`
- 双向别名 `GM_xxx` ↔ `GM.xxx`
- XHR 支持 `timeout`；one-shot 消息下 `abort` 为空操作；无二进制 `responseType`

### 5.5 依赖下载 (`src/fetcher.py`)

1. 从 URL 取文件名，冲突时 hash 后缀
2. 已存在则复用
3. `requests` 下载到 `extension/lib/`
4. 失败 fail-fast
5. 日志提示商店政策与无 SRI

### 5.6 校验 (`src/validator.py`)

- description 非空且 ≤132；name ≤75
- 至少一个 match；宽泛 match 警告
- 版本格式建议 x.y.z
- `@connect` 无法转换时警告
- `@resource` 未打包时警告
- `MAIN` + GM grant 时警告
- `store_assets`：icon.png + ≥1 截图

### 5.7 图像 (`utils/image.py`)

源 `icon.png` → 16 / 48 / 128（LANCZOS）。

### 5.8 打包 (`src/packager.py`)

ZIP、`upload_config.json`、WSL 下只打印 URL、素材拷到 `~/Downloads/<name>_assets/`。

## 6. 主入口 (`build.py`)

```bash
python build.py <script_dir>
python build.py <script_dir> --clean
python build.py <script_dir> --verbose
python build.py <script_dir> --package
```

**脚本发现：** 扫描目录下 `.js`，含完整 UserScript 头尾即候选。
- 0 个：`FileNotFoundError`（附带各文件跳过原因：无元数据 / 读失败）
- 1 个：采用
- 多个：`ValueError` 列出文件名

## 7. 关键技术决策

### 7.1 按内容找脚本，不约定文件名

任意 `.js` 名；以元数据块为准。

### 7.2 Polyfill 内嵌在 converter

单文件逻辑、无额外 polyfill 资源包。

### 7.3 省略空权限数组

符合 Chrome 实践、减小 manifest。

### 7.4 `store_assets/` 命名

直接表达商店素材用途。

### 7.5 不默认 `<all_urls>` match

过审与最小权限；宽泛 match 仅警告。

### 7.6 特权网络与标签类 API 统一走 background

与 MV3 安全模型一致；content 侧只做消息转发。

### 7.7 Storage 采用异步契约

`chrome.storage` 天然异步；对外统一 Promise，文档要求 `await` / `.then`。需要同步状态时用 `@grant none` + `localStorage`。

### 7.8 可选 MAIN world

页面 JS 对象与扩展隔离世界不可见；`@inject-into page` / `@world MAIN` 写入 `content_scripts.world`。与 GM/`chrome.*` 互斥，由校验警告。

## 8. 能力边界（产品契约）

| 支持 | 说明 |
|------|------|
| 主路径 | `@grant none` + DOM / localStorage |
| GM polyfill | 见 README 表；尽力兼容 |
| 页面 JS | `@inject-into page` / `@world MAIN` |
| `@require` | 下载进包 |
| 上架流水线 | 校验、图标、ZIP、upload 页 |

| 不支持或有限 | 说明 |
|--------------|------|
| 同步 `GM_getValue` 等 | 仅异步 |
| `unsafeWindow` | 无 polyfill；用 MAIN world 替代部分场景 |
| `@resource` / `GM_getResource*` | 仅警告 |
| XHR abort / 二进制 responseType | 有限 |
| include 冷门 glob | 直接写入 match，调用方需自洽 |

## 9. 测试状态

| 项目 | 状态 |
|------|------|
| 转换流程 | 已验证 |
| 本地加载 | 已验证 |
| Manifest V3 | 符合官方结构 |

## 10. 依赖

```
requests>=2.31.0
Pillow>=10.0.0
```

## 11. 故障排查

**找不到 UserScript**
- 路径、UTF-8、`// ==UserScript==` 块；看错误中的 Inspected 明细

**图标失败**
- `pip install Pillow`；存在 `store_assets/icon.png`

**依赖下载失败**
- 网络与 `@require` URL

**详细日志**
```bash
python build.py /path/to/script --verbose
```
