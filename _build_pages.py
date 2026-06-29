#!/usr/bin/env python3
"""Pre-render per-language static pages for path-based i18n on GitHub Pages.

English lives at the site root and is the hand-edited source of truth for body
copy (the `data-i18n` elements in index/privacy/support.html). This script bakes
each translation into its own static page so every language gets a real,
indexable URL:

    /                 /privacy.html        /support.html          (English, root)
    /zh/  /zh/privacy.html ...             (繁體中文)
    /jp/  /jp/privacy.html ...             (日本語)   ...and 9 more

Inputs
    index/privacy/support.html  — English templates (body via data-i18n keys)
    assets/i18n.js              — window.BC_STRINGS[lang][key]  (body translations)
    _meta_i18n.json             — per-page <title>/<meta description> per language

Outputs (all generated — DO NOT hand-edit the language subfolders)
    <slug>/index.html, <slug>/privacy.html, <slug>/support.html
    sitemap.xml, robots.txt

Run:  python3 _build_pages.py
"""
import json, os, re
import html as htmllib

WEB = os.path.dirname(os.path.abspath(__file__))
SITE = "https://blindclock.app"          # canonical origin (custom domain)
PAGES = ["index.html", "privacy.html", "support.html"]
PAGEKEY = {"index.html": "index", "privacy.html": "privacy", "support.html": "support"}

# code (matches BC_STRINGS / _meta_i18n.json), URL slug, BCP-47 hreflang, dropdown label.
# en uses slug "" (root). Keep in sync with assets/lang.js.
LANGS = [
    ("en",      "",   "en",      "English"),
    ("zh-Hant", "zh", "zh-Hant", "繁體中文"),
    ("ja",      "jp", "ja",      "日本語"),
    ("ko",      "ko", "ko",      "한국어"),
    ("de",      "de", "de",      "Deutsch"),
    ("fr-FR",   "fr", "fr",      "Français"),
    ("it",      "it", "it",      "Italiano"),
    ("pl",      "pl", "pl",      "Polski"),
    ("pt-BR",   "pt", "pt-BR",   "Português (BR)"),
    ("es-MX",   "es", "es-MX",   "Español (LA)"),
    ("tr",      "tr", "tr",      "Türkçe"),
    ("vi",      "vi", "vi",      "Tiếng Việt"),
]

HEAD_START = "<!--BC_I18N_HEAD_START-->"
HEAD_END = "<!--BC_I18N_HEAD_END-->"

# data-i18n wrappers are only span/p/li/h1/h2 (verified) — none nest a same-named
# child, so a tag-balanced, non-greedy match is safe.
I18N_RE = re.compile(r'(<(h1|h2|li|p|span)\b[^>]*\bdata-i18n="([^"]+)"[^>]*>)(.*?)(</\2>)', re.DOTALL)


def load_bc_strings():
    js = open(os.path.join(WEB, "assets/i18n.js"), encoding="utf-8").read()
    m = re.search(r"window\.BC_STRINGS\s*=\s*(\{.*\})\s*;", js, re.DOTALL)
    if not m:
        raise SystemExit("could not find window.BC_STRINGS in assets/i18n.js")
    return json.loads(m.group(1))


def page_url(page, slug):
    base = SITE + "/" + (slug + "/" if slug else "")
    return base if page == "index.html" else base + page


def translate_body(html, code, bc):
    if code == "en":
        return html
    d = bc.get(code, {})

    def repl(m):
        open_tag, _tag, key, inner, close = m.groups()
        return open_tag + d.get(key, inner) + close   # fall back to English inner

    return I18N_RE.sub(repl, html)


def strip_runtime(html):
    # content is baked in now — drop the runtime translation bundle, keep the
    # (navigation-only) switcher, and bust its cache.
    html = re.sub(r'\n\s*<script src="[^"]*i18n\.js[^"]*"></script>', '', html, count=1)
    html = html.replace('lang.js?v=1.10', 'lang.js?v=2.1')
    return html


def set_html_lang(html, hreflang):
    # require whitespace before lang=" so we don't accidentally match data-lang="
    html = re.sub(r'(<html\b[^>]*?\slang=")[^"]*(")', lambda m: m.group(1) + hreflang + m.group(2), html, count=1)
    html = re.sub(r'(\bdata-lang=")[^"]*(")', lambda m: m.group(1) + hreflang + m.group(2), html, count=1)
    return html


def set_meta(html, meta):
    title = htmllib.escape(meta["title"], quote=False)
    desc = htmllib.escape(meta["desc"], quote=True)
    html = re.sub(r'(<title>).*?(</title>)', lambda m: m.group(1) + title + m.group(2), html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<meta\s+name="description"\s+content=")[^"]*(")', lambda m: m.group(1) + desc + m.group(2), html, count=1)
    return html


def head_block(page, slug):
    lines = ['  <link rel="canonical" href="%s">' % page_url(page, slug)]
    for _c, s, hl, _l in LANGS:
        lines.append('  <link rel="alternate" hreflang="%s" href="%s">' % (hl, page_url(page, s)))
    lines.append('  <link rel="alternate" hreflang="x-default" href="%s">' % page_url(page, ""))
    return "\n".join(lines)


def inject_head(html, block):
    new = HEAD_START + "\n" + block + "\n  " + HEAD_END
    if HEAD_START in html and HEAD_END in html:
        return re.sub(re.escape(HEAD_START) + r".*?" + re.escape(HEAD_END), lambda m: new, html, count=1, flags=re.DOTALL)
    return html.replace("</head>", new + "\n</head>", 1)


def rewrite_assets(html):
    # subfolder pages are one level deep → point at the shared /assets at root
    return html.replace('"assets/', '"../assets/').replace("(assets/", "(../assets/")


def write_sitemap():
    urls = []
    alt_lines = lambda page: "".join(
        '\n    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (hl, page_url(page, s))
        for _c, s, hl, _l in LANGS
    ) + '\n    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>' % page_url(page, "")
    for page in PAGES:
        for _c, slug, _hl, _l in LANGS:
            urls.append("  <url>\n    <loc>%s</loc>%s\n  </url>" % (page_url(page, slug), alt_lines(page)))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n")
    open(os.path.join(WEB, "sitemap.xml"), "w", encoding="utf-8").write(xml)
    open(os.path.join(WEB, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)


def main():
    bc = load_bc_strings()
    meta = json.load(open(os.path.join(WEB, "_meta_i18n.json"), encoding="utf-8"))
    templates = {p: open(os.path.join(WEB, p), encoding="utf-8").read() for p in PAGES}

    # coverage check: every data-i18n key should exist in every non-English language
    keys = set(re.findall(r'data-i18n="([^"]+)"', "".join(templates.values())))
    for code, _s, _hl, _l in LANGS:
        if code == "en":
            continue
        miss = sorted(k for k in keys if k not in bc.get(code, {}))
        if miss:
            print("  [warn] %s missing %d body key(s): %s%s" % (code, len(miss), ", ".join(miss[:8]), "…" if len(miss) > 8 else ""))
        for pk in PAGEKEY.values():
            if code not in meta[pk]:
                print("  [warn] %s missing meta for page '%s' (falling back to en)" % (code, pk))

    written = []
    for code, slug, hreflang, _label in LANGS:
        outdir = WEB if not slug else os.path.join(WEB, slug)
        os.makedirs(outdir, exist_ok=True)
        for page in PAGES:
            html = translate_body(templates[page], code, bc)
            html = strip_runtime(html)
            html = set_html_lang(html, hreflang)
            html = set_meta(html, meta[PAGEKEY[page]].get(code, meta[PAGEKEY[page]]["en"]))
            html = inject_head(html, head_block(page, slug))
            if slug:
                html = rewrite_assets(html)
            open(os.path.join(outdir, page), "w", encoding="utf-8").write(html)
            written.append(os.path.relpath(os.path.join(outdir, page), WEB))

    write_sitemap()
    print("=== WROTE %d pages + sitemap.xml + robots.txt ===" % len(written))
    print("  langs: " + ", ".join("%s→/%s" % (c, s or "(root)") for c, s, _h, _l in LANGS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
