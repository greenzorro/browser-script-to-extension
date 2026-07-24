# browser-script-to-extension

[🇬🇧 EN](https://github.com/greenzorro/browser-script-to-extension/blob/main/README.md) | [🇨🇳 中文](https://github.com/greenzorro/browser-script-to-extension/blob/main/README_ZH_CN.md)

Automatically convert Tampermonkey/GreaseMonkey scripts into Chrome Extensions (Manifest V3).

## Why use this?

- **Zero Friction for Users:** Install directly from the Chrome Web Store—no Tampermonkey required.
- **Ecosystem Benefits:** Native discovery, established trust, and automatic updates.
- **Broader Reach:** Cross-platform distribution with trackable analytics.

Ask an agent to build and package on your machine (see `# For Agent`). You prepare the **userscript + store assets**, then handle **Web Store listing / review** after the ZIP exists.

## Script requirements (for authors)

Your `.js` **must** include:

```javascript
// ==UserScript==
// @name         Extension Name
// @version      1.0.0
// @description  Description (Required for Web Store)
// @match        https://example.com/*
// ==/UserScript==
```

Recommended: `@namespace`, `@author`, `@license`, `@grant` (default `none`), `@require`, `@run-at`, `@inject-into` / `@world`.

### Capability model

This tool is a **Web Store packaging pipeline** with best-effort GM polyfills—not a full Tampermonkey runtime.

| Path | Best for | Notes |
|------|----------|-------|
| **Recommended** | `@grant none` + DOM / `localStorage` | Closest to extension content scripts |
| GM polyfills | `@grant GM.*` | Best-effort; see table below |
| Page JS objects | CodeMirror, `window.App`, etc. | `@inject-into page` or `@world MAIN` |

| Metadata | Chrome `content_scripts.world` | Use when |
|----------|--------------------------------|----------|
| (default) / `@inject-into content` / `@world ISOLATED` | `ISOLATED` | `chrome.*` / GM polyfills |
| `@inject-into page` / `@world MAIN` | `MAIN` | Page JS objects |

`MAIN` cannot use `chrome.*`. Do not combine `MAIN` with GM grants that need storage / tabs / XHR.

`GM_setValue` / `GM_getValue` / `GM.deleteValue` / `GM.listValues` return **Promises** (not sync):

```js
const x = await GM_getValue('k', 0);
```

For sync state, use `@grant none` and `localStorage`.

### Supported GM APIs

Both `GM_xxx` and `GM.xxx` `@grant` styles are accepted.

| GM API | Polyfill Strategy |
|--------|-------------------|
| `GM_addStyle` / `GM.addStyle` | Injects `<style>` |
| `GM.setValue` / `getValue` … | **Async** `chrome.storage.local` |
| `GM.xmlHttpRequest` | Background `fetch()` (+ `host_permissions` / `@connect`) |
| `GM.notification` | `chrome.notifications` |
| `GM.setClipboard` | `navigator.clipboard` + fallback |
| `GM.openInTab` | `chrome.tabs.create` |
| `GM.download` | `chrome.downloads.download` |

Not supported (or only warned): `unsafeWindow`, `@resource` / `GM_getResource*`, sync `GM_getValue`, binary XHR `responseType`, XHR abort across contexts.

### Store assets you should prepare

In the script project’s `store_assets/`:

- **`icon.png`** (source; tool generates 16/48/128)
- **1–5 screenshots** (`.png` / `.jpg`)

### Publishing notes (human / store)

- Name ≤ 75 chars; description required ≤ 132 chars; SemVer `x.y.z` recommended
- Prefer specific `@match` over `<all_urls>` for review speed
- Remote `@require` must comply with Store policies
- One-time ~$5 Chrome Web Store developer fee
- After the agent produces a ZIP, **you** submit listing text, privacy form, and screenshots in the developer console

## Manual CLI

You can run the same build yourself after dependencies are installed:

```bash
python build.py /path/to/project_root
python build.py /path/to/project_root --clean
python build.py /path/to/project_root --verbose
python build.py /path/to/project_root --package
python build.py /path/to/project_root --refresh-dependencies
```

`--package` needs `store_assets/upload_config.json` when you want ZIP + upload pages opened.

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)

---

# For Agent

Convert a Tampermonkey userscript folder into a Manifest V3 Chrome extension, and operate the CLI for rebuilds/packaging when asked.

## Prerequisites

- Python 3 with pip
- Network access the first time you resolve `@require` URLs (or a warm dependency cache)
- A target project folder that already contains a `.js` file with a `// ==UserScript==` header

## Install / first-time setup

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

## Usage

Primary entrypoint: `python build.py <script_dir>`.

| Flag | Purpose |
|------|---------|
| *(none)* | Build into `script_dir/extension/` |
| `--clean` | Delete `extension/` then rebuild |
| `-v` / `--verbose` | Verbose logs |
| `--package` | ZIP + open upload URLs from `store_assets/upload_config.json` |
| `--refresh-dependencies` | Re-download `@require` deps (ignore verified cache) |

Typical flows:

1. **Build once:** `python build.py /path/to/project_root` → verify `extension/manifest.json` exists.
2. **Local load test:** tell the human to `chrome://extensions` → Developer mode → Load unpacked → `extension/`.
3. **Iterate after script edits:** rebuild (add `--clean` if polyfills/deps look stale).
4. **Publish packaging:** `python build.py /path/to/project_root --package`, then stop—store listing is human.

Auto-detection: any `.js` under `script_dir` with `// ==UserScript==` is used; do not invent metadata.

## Hand off to the human

- Approving Load unpacked / Tampermonkey prompts
- Web Store account, privacy questionnaire, screenshots copy, publish review
- Ongoing use of the resulting extension

## Red lines

- Do not invent missing `@name` / `@description` / `@match`; fix or ask
- Do not commit dependency caches as secrets; do not embed API keys
- Product contracts / architecture: `notes.md`
