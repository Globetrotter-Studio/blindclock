# BlindClock Website

GitHub Pages site for the BlindClock iOS app (repo: `Globetrotter-Studio/blindclock-privacy`).
Three static pages, bilingual (EN / 繁體中文) via a client-side toggle — no build step.

## Pages & App Store Connect URLs

| Page | File | Live URL | Used as |
|---|---|---|---|
| Marketing landing | `index.html` | `https://globetrotter-studio.github.io/blindclock-privacy/` | 行銷 URL (Marketing URL) |
| Support | `support.html` | `https://globetrotter-studio.github.io/blindclock-privacy/support.html` | 支援 URL (Support URL) |
| Privacy Policy | `privacy.html` | `https://globetrotter-studio.github.io/blindclock-privacy/privacy.html` | 隱私權政策 URL (Privacy Policy URL) |

> ⚠️ `index.html` used to BE the privacy policy. After deploying this version,
> update the Privacy Policy URL in App Store Connect to point at `privacy.html`.
> Do **not** rename the GitHub repo — it would break every URL above.

## Language switching

- `assets/lang.js` sets `data-lang="en|zh"` on `<html>`; CSS shows/hides `.lang-en` / `.lang-zh` content.
- Priority: `?lang=zh|en` query param → saved choice (localStorage) → browser language → English.
- Every user-visible string appears twice, wrapped in `<span class="lang-en">` / `<span class="lang-zh">`.

## 🔁 Release checklist — update this site with EVERY app release

When a new version (e.g. 1.9) ships, update:

1. **`index.html`**
   - Version pill in the hero (`Version 1.7 …` → new version, both EN and ZH spans).
   - The “What’s new in X.Y” section: replace with the new release notes (EN + ZH).
   - Feature grid: add/adjust cards if features were added, removed, or re-tiered (free vs Pro).
2. **`support.html`**
   - Version number in the `.meta` line.
   - FAQ entries: add questions for new features, fix any answers invalidated by changes.
   - Minimum OS line if the deployment target changed.
3. **`privacy.html`** — only if data practices changed (new SDK, new data collected, new permission).
   If changed, also bump the “Effective date” (both EN and ZH).
4. Fill in the real App Store URL in `index.html` (`store-badge` link) once the app page is live.
5. Commit and push to `main` — GitHub Pages deploys automatically.

## Local preview

```sh
python3 -m http.server 8000
# open http://localhost:8000
```
