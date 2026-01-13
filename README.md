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
- **Screenshot files**: 1 to 5 images in `.png` or `.jpg` format (placed directly in `store_assets/` directory).

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

**Icon Error**
- Ensure `Pillow` is installed (`pip install Pillow`).
- Verify `store_assets/icon.png` exists.

**Download Error**
- Check internet connection.
- Verify `@require` URLs are accessible.

---

Created by [Victor_42](https://victor42.work/)