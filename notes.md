# browser-script-to-extension 项目备忘录

## 1. 目的

本文档旨在记录 `browser-script-to-extension` 项目的实现细节和架构决策，为本项目的未来开发和维护提供便利。

**重要提示：** 每次新增或修改功能后，请务必更新此备忘录，确保文档的准确性和时效性。

## 2. 项目概述

本项目是一个Python工具，自动将 Tampermonkey userscript 转换为 Chrome Extension Manifest V3 格式的浏览器扩展。

**核心价值：**
- 降低使用门槛：用户直接从 Chrome Web Store 安装，无需了解 Tampermonkey
- 利用浏览器应用商店生态：发现机制、信任体系、自动更新
- 拓展推广渠道：跨平台分发、可追踪数据、借助全球化网络

## 3. 技术栈

- **Python 3.12+**: 主要开发语言
- **dataclasses**: 元数据结构定义
- **re**: UserScript 元数据块解析
- **json**: manifest.json 生成
- **requests**: 外部依赖下载
- **Pillow (PIL)**: 图像处理，图标尺寸转换

## 4. 目录结构

```
browser-script-to-extension/
├── build.py                  # 主入口脚本
├── plan.md                   # 实现计划
├── .gitignore                # Git忽略文件
├── src/                      # 核心模块
│   ├── __init__.py
│   ├── parser.py             # UserScript元数据解析
│   ├── manifest.py           # manifest.json生成器
│   ├── converter.py          # 代码转换器（GM API polyfill）
│   ├── fetcher.py            # 外部依赖下载器
│   ├── validator.py          # Chrome Web Store上架要求验证
│   └── packager.py           # 打包发布功能
└── utils/
    ├── __init__.py
    └── image.py              # 图像处理
```

**用户脚本目录（用户提供）：**
```
[path/to/your/script-directory]
├── [任意文件名].js              # 包含 UserScript 元数据的JS文件（必需）
├── store_assets/                  # 商店上架素材（必需）
│   ├── icon.png                  # 图标源文件（必需），用于生成 16x16、48x48、128x128 图标
│   ├── screenshot1.png           # 截图文件（必需，至少1张，最多5张）
│   ├── screenshot2.png           # 可选
│   └── ...
└── extension/                    # 输出目录（自动生成）
    ├── manifest.json
    ├── content.js
    ├── icons/                    # 16x16, 48x48, 128x128
    └── lib/                      # @require依赖
```

## 5. 核心模块

### 5.1 元数据解析器 (`src/parser.py`)

解析 Tampermonkey/GreaseMonkey 脚本的 `==UserScript==` 元数据块。

**正则表达式提取：**
- 元数据块：`// ==UserScript==\n(.*?)// ==/UserScript==`
- 元数据行：`// @(\S+)\s+(.+)`

**支持的多值属性：**
- `@match`: 多个匹配模式
- `@grant`: 多个权限声明
- `@require`: 多个外部依赖

**默认值处理：**
- `version`: "1.0.0"
- `description`: "" (空字符串，需在 Web Store 上架时补充)
- `license`: "MIT"

### 5.2 Manifest V3 生成器 (`src/manifest.py`)

将 UserScript 元数据转换为 Chrome Extension Manifest V3 格式。

**GM API 到 Chrome 权限的映射：**

| GM API | Chrome API |
|--------|------------|
| `GM_addStyle` | 无需特殊权限 |
| `GM.setValue/getValue/deleteValue/listValues` | `permissions: ["storage"]` |
| `GM_xmlHttpRequest` | `host_permissions: ["<all_urls>"]` |
| `GM_notification` | `permissions: ["notifications"]` |
| `GM.setClipboard` | `permissions: ["clipboardWrite"]` |
| `GM.openInTab` | `permissions: ["tabs"]` |
| `GM_download` | `permissions: ["downloads"]` + `host_permissions: ["<all_urls>"]` |

**Manifest 优化策略：**
- 省略空的 `permissions` 和 `host_permissions` 数组
- 符合 Chrome 官方最佳实践
- 减小 manifest.json 体积

### 5.3 代码转换器 (`src/converter.py`)

处理 UserScript 代码，注入 GM API polyfill。

**GM API Polyfill 清单（11种）：**
- `GM_addStyle`: 创建 `<style>` 元素注入
- `GM.setValue/getValue/deleteValue/listValues`: `chrome.storage.local` API
- `GM.xmlHttpRequest`: `fetch()` API 包装
- `GM_notification`: `chrome.notifications.create()`
- `GM.setClipboard`: 临时 `<textarea>` + `execCommand('copy')`
- `GM.openInTab`: `chrome.tabs.create()`
- `GM.download`: `chrome.downloads.download()`

**转换流程：**
1. 分析 `@grant` 元数据，确定需要哪些 API
2. 为每个需要的 API 生成对应的 polyfill 代码
3. 将 polyfill 包装在 IIFE 中
4. 将原始代码追加在 polyfill 之后

### 5.4 依赖下载器 (`src/fetcher.py`)

下载 `@require` 指定的外部 JavaScript 库到本地。

**处理逻辑：**
1. 解析 URL 获取文件名
2. 检查本地是否已存在
3. 使用 `requests` 下载文件
4. 保存到 `extension/lib/` 目录
5. 在 manifest 中添加到 `content_scripts.js` 列表

**错误处理：**
- 网络超时：默认 30 秒
- User-Agent 模拟浏览器请求
- Chrome Web Store 警告：远程代码需符合商店政策

### 5.5 图像处理工具 (`utils/image.py`)

图标生成和 Chrome Web Store 材料验证。

**图标生成：**
- 输入：单一源图标（推荐 512x512 或更高）
- 输出：三种标准尺寸 `16x16`、`48x48`、`128x128`
- 算法：`PIL.Image.resize()` + `Image.Resampling.LANCZOS`

**商店材料验证：**
检查 `store_assets/` 目录包含：
- `icon.png`: 必需
- 截图文件：至少 1 张 `*.png` 或 `*.jpg`，最多 5 张（直接放在 `store_assets/` 下）

## 6. 主入口 (`build.py`)

### 6.1 命令行接口

```bash
python build.py <script_dir>           # 处理单个脚本
python build.py <script_dir> --clean   # 清理后重新构建
python build.py <script_dir> --verbose # 显示详细日志
python build.py <script_dir> --package # 构建并打包
```

### 6.2 UserScript 自动检测

扫描指定目录下所有 `.js` 文件，检测 `// ==UserScript==` 和 `// ==/UserScript==` 特征。

**查找逻辑：**
- 找到 0 个：抛出 `FileNotFoundError`
- 找到 1 个：使用该文件
- 找到多个：抛出 `ValueError`，列出所有候选文件名

### 6.3 Chrome Web Store 上架要求验证

**检查项目：**
1. 描述非空：`@description` 不能为空
2. 描述长度：`len(description) <= 132` 字符（Chrome 硬性限制）
3. 权限警告：`<all_urls>` in `match_patterns` 时记录警告
4. 名称长度：`len(name) <= 75` 字符
5. 版本号：建议使用 `x.y.z` 格式

### 6.4 打包发布功能

通过 `--package` 参数自动打包 `extension/` 目录并打开上传页面。

**配置文件：** `store_assets/upload_config.json`

```json
{
  "zip_filename": "自定义ZIP名称（可选）",
  "output_path": "~/Downloads",
  "upload_urls": [
    "https://chrome.google.com/webstore/devconsole/xxx/edit/package",
    "https://partner.microsoft.com/.../packages"
  ]
}
```

**路径格式注意：**
- **跨平台推荐**：`~/Downloads`（自动扩展为用户主目录）
- **相对路径**：`../releases`
- **绝对路径**：统一使用正斜杠 `/`，Windows 也支持（如 `C:/Users/xxx/Downloads`）
- ❌ 不要使用反斜杠 `\`（JSON 中需要转义，且不跨平台）

**默认行为：**
- ZIP 文件名：与脚本文件同名
- ZIP 输出路径：项目根目录（与 `extension/` 同级）
- 无配置时：只打包，不打开上传页面

**平台检测：**
- WSL 环境：打印 URL，不打开浏览器
- macOS/Linux/Windows：自动打开浏览器

## 7. 关键技术决策

### 7.1 UserScript 查找策略

扫描目录检测 `==UserScript==` 特征，而非依赖文件名约定。

**理由：**
- 更灵活：支持任意文件名
- 更可靠：基于实际文件内容判断
- 符合使用习惯

### 7.2 GM API Polyfill 设计

将所有 polyfill 代码内嵌在 `converter.py` 中。

**理由：**
- 简化部署：单个文件包含所有逻辑
- 避免外部依赖：polyfill 代码不单独打包
- 易于维护

### 7.3 Manifest 权限管理

省略空的 `permissions` 和 `host_permissions` 数组。

**理由：**
- 符合 Chrome 官方最佳实践
- 减小 manifest.json 体积

### 7.4 商店素材目录命名

使用 `store_assets/` 而非 `to_extension_config/`。

**理由：**
- 更明确：名称直接反映"商店素材"
- 更通用：未来支持其他商店时仍适用
- 更简洁

## 8. 测试状态

| 测试项目 | 状态 |
|----------|------|
| 转换流程 | ✅ 已验证 |
| Chrome 加载 | ✅ 本地安装测试通过，功能正常 |
| Manifest V3 合规 | ✅ 符合 Chrome 官方文档标准 |

## 9. 依赖管理

**依赖库：**
```
requests>=2.31.0   # HTTP请求
Pillow>=10.0.0     # 图像处理
```

## 10. 故障排查

### 10.1 常见问题

**找不到 UserScript 文件**
- 检查目录路径是否正确
- 确认 `.js` 文件包含 `// ==UserScript==` 块
- 确认文件编码为 UTF-8

**图标生成失败**
- 检查是否安装 Pillow：`pip install Pillow`
- 确认 `store_assets/icon.png` 文件存在

**依赖下载失败**
- 检查网络连接
- 确认 `@require` URL 可访问

### 10.2 调试技巧

**启用详细日志：**
```bash
python build.py /path/to/script --verbose
```

