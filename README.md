# browser-script-to-extension

[🇬🇧 EN](https://github.com/greenzorro/browser-script-to-extension/blob/main/README.md) | [🇨🇳 中文](https://github.com/greenzorro/browser-script-to-extension/blob/main/README_ZH_CN.md)

Automatically convert Tampermonkey/GreaseMonkey scripts into Chrome Extensions (Manifest V3).

## Why use this?

- **Zero Friction for Users:** Install directly from the Chrome Web Store—no Tampermonkey required.
- **Ecosystem Benefits:** Native discovery, established trust, and automatic updates.
- **Broader Reach:** Cross-platform distribution with trackable analytics.

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Directory Setup

Structure your project folder as follows:

```
[project_root]/
├── script.js                # Your script with ==UserScript== metadata
├── store_assets/
│   ├── icon.png             # Source icon (512x512+ recommended)
│   ├── screenshot1.png      # Screenshot files (1-5 required)
│   └── screenshot2.png      # Optional
└── extension/               # Output directory (auto-generated)
```

### 3. Build

```bash
python build.py /path/to/project_root
```

## Usage

### CLI Commands

```bash
# Build a script
python build.py /path/to/project_root

# Clean rebuild
python build.py /path/to/project_root --clean

# Verbose logging
python build.py /path/to/project_root --verbose

# Build and package (creates ZIP and opens upload pages)
python build.py /path/to/project_root --package

# Force a fresh download of all @require dependencies
python build.py /path/to/project_root --refresh-dependencies
```

### Auto-Detection

The tool scans the target directory for any `.js` file containing a `// ==UserScript==` block and uses it automatically.

## Script Requirements

### Minimal Metadata

Your script **must** include:

```javascript
// ==UserScript==
// @name         Extension Name
// @version      1.0.0
// @description  Description (Required for Web Store)
// @match        https://example.com/*
// ==/UserScript==

// Your code here...
```

### Recommended Metadata

- `@namespace`: Prevents ID conflicts.
- `@author`: Your name.
- `@license`: e.g., MIT.
- `@grant`: Declare used GM APIs (defaults to `none`).
- `@require`: External libraries.
- `@run-at`: Execution timing (default: `document-end`).
- `@inject-into` / `@world`: Execution world (see below).

### Capability Model

This tool is a **Web Store packaging pipeline** with best-effort GM polyfills—not a full Tampermonkey runtime.

| Path | Best for | Notes |
|------|----------|-------|
| **Recommended** | `@grant none` + DOM / `localStorage` | Closest to extension content scripts |
| GM polyfills | `@grant GM.*` | Best-effort; see table below |
| Page JS objects | CodeMirror, `window.App`, etc. | `@inject-into page` or `@world MAIN` |

**Execution world**

| Metadata | Chrome `content_scripts.world` | Use when |
|----------|--------------------------------|----------|
| (default) / `@inject-into content` / `@world ISOLATED` | `ISOLATED` | `chrome.*` / GM polyfills |
| `@inject-into page` / `@world MAIN` | `MAIN` | Page JS objects (e.g. `element.CodeMirror`) |

`MAIN` cannot use `chrome.*`. Do not combine `MAIN` with GM grants that need storage / tabs / XHR.

**Storage**

`GM_setValue` / `GM_getValue` / `GM.deleteValue` / `GM.listValues` return **Promises** (GM4-style / `chrome.storage.local`):

```js
// not supported (sync)
const x = GM_getValue('k', 0);

// supported
const x = await GM_getValue('k', 0);
// or: GM_getValue('k', 0).then(...)
```

For synchronous state, use `@grant none` and `localStorage`.

### Supported GM APIs

Both `GM_xxx` and `GM.xxx` `@grant` styles are accepted and normalized.

| GM API | Polyfill Strategy |
|--------|-------------------|
| `GM_addStyle` / `GM.addStyle` | Injects `<style>` tag |
| `GM.setValue` / `getValue` ... | **Async** `chrome.storage.local` (Promise) |
| `GM.xmlHttpRequest` | Via background service worker → `fetch()` (CORS bypass with `host_permissions` / `@connect`) |
| `GM.notification` | Via background → `chrome.notifications` |
| `GM.setClipboard` | `navigator.clipboard` with fallback |
| `GM.openInTab` | Via background → `chrome.tabs.create` |
| `GM.download` | Via background → `chrome.downloads.download` |

A `background.js` message bridge is generated when XHR / tabs / notifications / downloads are required.

Not supported (or only warned): `unsafeWindow`, `@resource` / `GM_getResource*`, sync `GM_getValue`, binary XHR `responseType`, XHR abort across contexts.

### Asset Requirements

Ensure `store_assets/` contains:
- **`icon.png`**: Source icon. The tool generates 16, 48, and 128px versions automatically.
- **Screenshot files**: 1 to 5 images in `.png` or `.jpg` format (placed directly in `store_assets/` directory).

## Output Structure

Upon success, the `extension/` folder is ready for deployment:

```
extension/
├── manifest.json      # Generated configuration
├── content.js         # Transpiled script with polyfills
├── dependencies.lock.json # @require URL, filename, and cache hash
├── icons/             # Resized icons
└── lib/               # Downloaded @require dependencies
```

### Dependency Cache

After the first successful download, each `@require` URL, output filename, and
SHA-256 hash is recorded in `dependencies.lock.json`. Later builds reuse a file
only when the URL is unchanged and its current hash still matches the lock.
This keeps normal builds reproducible and allows them to work offline.

Use `--refresh-dependencies` when you intentionally want to fetch the current
remote content. A changed URL, a missing lock, or a hash mismatch also triggers
a download. Failed downloads abort the build without replacing the previous
dependency or lock file. The recorded hash validates the local cache; it is not
publisher-provided SRI authenticity proof.

`--clean` removes the whole `extension/` directory, including the dependency
files and lock, so a clean rebuild requires network access.

## Testing in Chrome

1. Go to `chrome://extensions/`.
2. Enable **Developer mode** (top right).
3. Click **Load unpacked**.
4. Select the `extension/` folder.

## Publishing to Web Store

### Requirements
- **Name:** Max 75 characters.
- **Description:** Cannot be empty, max 132 characters.
- **Screenshots:** 1-5 required.
- **Version:** SemVer format (x.y.z) recommended.

### Important Notes
- Avoid `<all_urls>` permission if possible; specific patterns pass review faster.
- Remote code (`@require`) must align with Store policies.
- A one-time $5 developer registration fee applies.

## Packaging

### Quick Package

The tool can automatically package your extension and open store upload pages:

```bash
python build.py /path/to/project_root --package
```

### Upload Configuration

Create `store_assets/upload_config.json` in your project:

```json
{
  "zip_filename": "My Extension",
  "output_path": "~/Downloads",
  "upload_urls": [
    "https://chrome.google.com/webstore/devconsole/xxx/edit/package",
    "https://partner.microsoft.com/.../packages"
  ]
}
```

**Field Reference:**

| Field | Required | Description |
|-------|----------|-------------|
| `zip_filename` | Optional | ZIP filename (without .zip), defaults to script filename |
| `output_path` | Optional | Output path (see path format below) |
| `upload_urls` | Required | Array of upload page URLs |

**Path Format:**
- **Cross-platform recommended**: `~/Downloads` (expands to user home directory)
- **Relative path**: `../releases`
- **Absolute path**: Always use forward slashes `/`, works on Windows too (e.g., `C:/Users/xxx/Downloads`)
- ❌ Don't use backslashes `\` (requires escaping in JSON, not cross-platform)

**Default Behavior:**

- Without config: Uses script filename for ZIP, outputs to project root, skips opening pages
- WSL environment: Prints URLs instead of opening browser

## Troubleshooting

**Script Not Found**
- Verify the path.
- Ensure the `.js` file has a valid `// ==UserScript==` header.
- Check for UTF-8 encoding.
- The error message lists why each `.js` file was skipped.

**Icon Error**
- Ensure `Pillow` is installed (`pip install Pillow`).
- Verify `store_assets/icon.png` exists.

**Download Error**
- A verified dependency cache can be reused without a network connection.
- For a first download or `--refresh-dependencies`, check the connection and
  verify that every `@require` URL is accessible.

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)

# For Agent

Convert a Tampermonkey userscript folder into a Manifest V3 Chrome extension on this machine, then hand off store upload / daily use to the human.

## Prerequisites

- Python 3 with pip
- Network access the first time you resolve `@require` URLs (or a warm dependency cache)
- A target project folder that already contains a `.js` file with a `// ==UserScript==` header

## Steps

1. Clone or locate this repo. From the repo root:
   ```bash
   pip install -r requirements.txt
   ```
2. Confirm the target folder layout:
   ```text
   [project_root]/
   ├── <script>.js          # must include ==UserScript==
   └── store_assets/
       ├── icon.png         # required for packaging / store
       └── screenshot*.png  # 1–5 for --package / Web Store
   ```
3. Build:
   ```bash
   python build.py /path/to/project_root
   ```
   Useful flags: `--clean`, `--verbose`, `--package`, `--refresh-dependencies`.
4. Verify: `project_root/extension/` exists with `manifest.json` and content scripts. For a local smoke test, tell the human to open `chrome://extensions`, enable Developer mode, and **Load unpacked** → `extension/`.
5. If the human asked to publish: `python build.py /path/to/project_root --package` produces a ZIP and may open upload pages. Stop there—Chrome Web Store login, listing text, and submission are human tasks.

## Hand off to the human

- Loading the unpacked extension / Tampermonkey install confirmation in the browser
- Web Store account, privacy questionnaire, and publish review
- Ongoing use of the resulting extension

## Red lines

- Do not invent missing `@name` / `@description` / `@match` metadata; fix or ask
- Do not commit downloaded `@require` caches as secrets; do not embed API keys
- Maintainer architecture and capability boundaries live in `notes.md`—read it when the build fails for product-contract reasons, do not paste it into commits

For Chinese readers, see [README_ZH_CN.md](README_ZH_CN.md) (human-facing only).
