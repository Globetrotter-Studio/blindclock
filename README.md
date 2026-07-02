# BlindClock Website

GitHub Pages site for the BlindClock iOS app, served on the custom domain **`blindclock.app`**
(see `CNAME`). Three pages × 12 languages, **pre-rendered** into per-language folders by
`_build_pages.py` — each language is a real, indexable URL (good for SEO). There IS a build step now.

The build also generates the whole **SEO/GEO layer** (strategy + follow-ups in
`../docs/product/seo-geo.md`): canonical + hreflang (incl. `es`/`pt` generic aliases),
localized Open Graph/Twitter tags, JSON-LD (SoftwareApplication on index, FAQPage on
support — extracted from the baked translations), `sitemap.xml` with honest `<lastmod>`
(git dates), `robots.txt` (deliberately open to AI crawlers — do NOT add Disallow rules),
and `llms.txt`. Static extras at the root: `404.html`, `favicon.ico`, `assets/og.png`
(1200×630 share card), and the IndexNow key file `60e56452e51f4aacb43c99f544b5f1f5.txt`.

## Pages & App Store Connect URLs (English / canonical)

| Page | File | Live URL | Used as |
|---|---|---|---|
| Marketing landing | `index.html` | `https://blindclock.app/` | 行銷 URL (Marketing URL) |
| Support | `support.html` | `https://blindclock.app/support.html` | 支援 URL (Support URL) |
| Privacy Policy | `privacy.html` | `https://blindclock.app/privacy.html` | 隱私權政策 URL (Privacy Policy URL) |

Localized variants live under a slug folder, e.g. `https://blindclock.app/jp/privacy.html` (日本語),
`https://blindclock.app/zh/` (繁中). `blindclock.app/jp` (no slash) 301-redirects to `/jp/`.

> ⚠️ DNS: `blindclock.app` is registered on Cloudflare. Apex → 4 GitHub A records
> (185.199.108–111.153), `www` → CNAME `globetrotter-studio.github.io`, proxy = **DNS only**.
> Set the custom domain in the repo's Settings → Pages so the `CNAME` file lands correctly.
> The `CNAME` file in this repo pins `blindclock.app`.

## Language switching — path-based, pre-rendered (12 languages)

Localized in **English, 繁體中文, 日本語, 한국어, Deutsch, Français, Italiano, Polski, Português (BR), Español (LA), Türkçe, Tiếng Việt**. URL slugs: `(en)=root`, `zh`, `jp`, `ko`, `de`, `fr`, `it`, `pl`, `pt`, `es`, `tr`, `vi`.

How it works (each language is its own static page — NOT a client-side swap):

- **English is the source of truth in the HTML** (`index/privacy/support.html` at root). Each translatable element carries `data-i18n="<key>"`; body translations live in `assets/i18n.js` as `window.BC_STRINGS[lang][key]`.
- Per-page `<title>` / `<meta description>` for every language live in **`_meta_i18n.json`**.
- **`_build_pages.py`** bakes each translation into static files: it writes the English pages at root and every other language into `<slug>/…`, sets `<html lang>`, swaps `<title>`/description, rewrites `assets/…` → `../assets/…`, and injects `<link rel="canonical">` + 12 `hreflang` alternates. It also regenerates `sitemap.xml` + `robots.txt`. **Run it after any copy change** — the language subfolders are generated, never hand-edited.
- `assets/lang.js` is now navigation-only: it builds the `<select id="lang-select">` and, on change, sends the browser to the same page under the chosen slug (no runtime text swapping). Keep its `LANGS` list in sync with `_build_pages.py`.
- To change the domain: edit `SITE` in `_build_pages.py` (and `CNAME`), then rebuild.

> Legacy helpers kept from v1.9: `_web_source.json` (key → en + zh-Hant source) and
> `_build_i18n.py` (regenerates `assets/i18n.js` from the translation workflow output).

## 🔁 Release checklist — update this site with EVERY app release

When a new version (e.g. 1.11) ships, update:

1. **`index.html`**
   - Version pill in the hero (`Version 1.9 …` → new version). Update the English default in the HTML **and** the `i8` value in `_web_source.json` / each language in `assets/i18n.js`.
   - The “What’s new in X.Y” section (`i27`, `i28a/b`, `i29a/b`, `i30a/b`): replace with the new release notes in every language.
   - Feature grid: add/adjust cards if features were added, removed, or re-tiered (free vs Pro).
2. **`support.html`**
   - Version number in the `.meta` line (`s4`).
   - FAQ entries: add questions for new features; fix any answers invalidated by changes.
   - Minimum OS line / supported-languages line (`s25`) if they changed.
3. **`privacy.html`** — only if data practices changed (new SDK, new data collected, new permission).
   If changed, also bump the “Effective date” (`pv2`) in every language.
4. **Translations:** after editing any English string, update its translation for all 11 other languages (edit `_web_source.json` + `python3 _build_i18n.py`, or edit `assets/i18n.js` directly).
5. Fill in the real App Store URL in `index.html` (`store-badge` link) once the app page is live.
6. **Rebuild:** `python3 _build_pages.py` — regenerates all 36 pages + `sitemap.xml` +
   `robots.txt` + `llms.txt`, with JSON-LD/OG refreshed and the app version parsed from
   the hero pill (`i8`). (If titles/descriptions changed, edit `_meta_i18n.json` first —
   it also feeds `og:title`/`og:description` and the SoftwareApplication description.)
7. Commit and push to `main` (include the regenerated `<slug>/` folders + `sitemap.xml`) — GitHub Pages deploys automatically.
8. **IndexNow ping (after the deploy is live):** tells Bing (→ Copilot + ChatGPT search)
   about the changed pages in hours instead of weeks. Only ping URLs that actually changed:

   ```sh
   curl -s -X POST https://api.indexnow.org/indexnow \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d '{"host":"blindclock.app","key":"60e56452e51f4aacb43c99f544b5f1f5",
          "keyLocation":"https://blindclock.app/60e56452e51f4aacb43c99f544b5f1f5.txt",
          "urlList":["https://blindclock.app/","https://blindclock.app/support.html"]}'
   ```

   (Add the `<slug>/` variants of whichever pages changed; 200/202 = accepted.)

## Local preview

```sh
python3 _build_pages.py          # regenerate the per-language pages first
python3 -m http.server 8000
# English: http://localhost:8000/   ·   日本語: http://localhost:8000/jp/
```
