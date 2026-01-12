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
│   └── screenshots/         # Folder with 1-5 screenshots
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

### Supported GM APIs

| GM API | Polyfill Strategy |
|--------|-------------------|
| `GM_addStyle` | Injects `<style>` tag |
| `GM.setValue` / `getValue` ... | Maps to `chrome.storage.local` |
| `GM.xmlHttpRequest` | Wrapper around `fetch()` |
| `GM.notification` | Maps to `chrome.notifications.create` |
| `GM.setClipboard` | Temporary textarea + `execCommand` |
| `GM.openInTab` | Maps to `chrome.tabs.create` |
| `GM.download` | Maps to `chrome.downloads.download` |

### Asset Requirements

Ensure `store_assets/` contains:
- **`icon.png`**: Source icon. The tool generates 16, 48, and 128px versions automatically.
- **`screenshots/`**: A folder containing 1 to 5 screenshots.

## Output Structure

Upon success, the `extension/` folder is ready for deployment:

```
extension/
├── manifest.json      # Generated configuration
├── content.js         # Transpiled script with polyfills
├── icons/             # Resized icons
└── lib/               # Downloaded @require dependencies
```

## Testing in Chrome

1. Go to `chrome://extensions/`.
2. Enable **Developer mode** (top right).
3. Click **Load unpacked**.
4. Select the `extension/` folder.

## Publishing to Web Store

### Requirements
- **Name:** Max 75 characters.
- **Description:** Cannot be empty.
- **Screenshots:** 1-5 required.
- **Version:** SemVer format (x.y.z) recommended.

### Important Notes
- Avoid `<all_urls>` permission if possible; specific patterns pass review faster.
- Remote code (`@require`) must align with Store policies.
- A one-time $5 developer registration fee applies.

## Troubleshooting

**Script Not Found**
- Verify the path.
- Ensure the `.js` file has a valid `// ==UserScript==` header.
- Check for UTF-8 encoding.

**Icon Error**
- Ensure `Pillow` is installed (`pip install Pillow`).
- Verify `store_assets/icon.png` exists.

**Download Error**
- Check internet connection.
- Verify `@require` URLs are accessible.

---

Created by [Victor_42](https://victor42.work/)