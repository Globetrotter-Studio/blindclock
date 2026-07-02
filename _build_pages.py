#!/usr/bin/env python3
"""Pre-render per-language static pages for path-based i18n on GitHub Pages.

English lives at the site root and is the hand-edited source of truth for body
copy (the `data-i18n` elements in index/privacy/support.html). This script bakes
each translation into its own static page so every language gets a real,
indexable URL:

    /                 /privacy.html        /support.html          (English, root)
    /zh/  /zh/privacy.html ...             (繁體中文)
    /jp/  /jp/privacy.html ...             (日本語)   ...and 9 more

It also generates the whole SEO/GEO head + artifact layer (strategy notes in
the app repo: docs/product/seo-geo.md):

    - <link canonical> + hreflang alternates (incl. es/pt generic aliases)
    - Open Graph + Twitter Card tags, localized per page/language
    - JSON-LD: Organization + WebSite + SoftwareApplication on index,
      FAQPage on support — built from the ALREADY-TRANSLATED page text so the
      markup always matches the visible copy in every language
    - sitemap.xml with honest <lastmod> (git commit dates; today if dirty)
    - robots.txt (fully open — AI answer engines must be able to fetch pages)
    - llms.txt (llmstxt.org index for AI/agent tooling)

Inputs
    index/privacy/support.html  — English templates (body via data-i18n keys)
    assets/i18n.js              — window.BC_STRINGS[lang][key]  (body translations)
    _meta_i18n.json             — per-page <title>/<meta description> per language

Outputs (all generated — DO NOT hand-edit the language subfolders)
    <slug>/index.html, <slug>/privacy.html, <slug>/support.html
    sitemap.xml, robots.txt, llms.txt

Run:  python3 _build_pages.py
"""
import datetime
import json
import os
import re
import subprocess
import html as htmllib

WEB = os.path.dirname(os.path.abspath(__file__))
SITE = "https://blindclock.app"          # canonical origin (custom domain)
APPSTORE_URL = "https://apps.apple.com/app/blindclock/id6775924424"
CONTACT_EMAIL = "panshikai0117@gmail.com"
OG_IMAGE = SITE + "/assets/og.png"       # 1200x630 share card
PAGES = ["index.html", "privacy.html", "support.html"]
PAGEKEY = {"index.html": "index", "privacy.html": "privacy", "support.html": "support"}

# code (matches BC_STRINGS / _meta_i18n.json), URL slug, BCP-47 hreflang,
# dropdown label, Open Graph locale. en uses slug "" (root).
# Keep in sync with assets/lang.js.
LANGS = [
    ("en",      "",   "en",      "English",        "en_US"),
    ("zh-Hant", "zh", "zh-Hant", "繁體中文",        "zh_TW"),
    ("ja",      "jp", "ja",      "日本語",          "ja_JP"),
    ("ko",      "ko", "ko",      "한국어",          "ko_KR"),
    ("de",      "de", "de",      "Deutsch",        "de_DE"),
    ("fr-FR",   "fr", "fr",      "Français",       "fr_FR"),
    ("it",      "it", "it",      "Italiano",       "it_IT"),
    ("pl",      "pl", "pl",      "Polski",         "pl_PL"),
    ("pt-BR",   "pt", "pt-BR",   "Português (BR)", "pt_BR"),
    ("es-MX",   "es", "es-MX",   "Español (LA)",   "es_MX"),
    ("tr",      "tr", "tr",      "Türkçe",         "tr_TR"),
    ("vi",      "vi", "vi",      "Tiếng Việt",     "vi_VN"),
]

# Generic-language hreflang aliases: a searcher in Spain/Portugal matches no
# regional code above, so also annotate the same URL with the bare language code.
HREFLANG_ALIASES = {"es-MX": "es", "pt-BR": "pt"}

FEATURE_LIST = [
    "Blind structure generator",
    "Time bank",
    "Payout calculator",
    "Live Activity and Dynamic Island",
    "iPad table display",
    "Live table stats",
    "iCloud sync",
]

HEAD_START = "<!--BC_I18N_HEAD_START-->"
HEAD_END = "<!--BC_I18N_HEAD_END-->"

# data-i18n wrappers are only span/p/li/h1/h2 (verified) — none nest a same-named
# child, so a tag-balanced, non-greedy match is safe.
I18N_RE = re.compile(r'(<(h1|h2|li|p|span)\b[^>]*\bdata-i18n="([^"]+)"[^>]*>)(.*?)(</\2>)', re.DOTALL)

# support.html FAQ items: <details class="faq"...><summary>Q</summary><div class="answer">A</div>
FAQ_RE = re.compile(r'<details class="faq"[^>]*>\s*<summary>(.*?)</summary>\s*<div class="answer">(.*?)</div>', re.DOTALL)


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


def strip_tags(fragment):
    return htmllib.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def extract_faq(translated_html):
    """(question, answer) plain-text pairs from the baked support page —
    guarantees FAQPage JSON-LD matches the visible text in every language."""
    return [(strip_tags(q), strip_tags(a)) for q, a in FAQ_RE.findall(translated_html)]


def parse_app_facts(index_template):
    """Version + minimum OS from the English hero pill (i8) so JSON-LD/llms.txt
    can never drift from the visible release info."""
    pill = re.search(r'data-i18n="i8">([^<]*)', index_template)
    pill = pill.group(1) if pill else ""
    ver = re.search(r"Version\s+([0-9.]+)", pill)
    min_os = re.search(r"iOS\s+([0-9.]+)\+", pill)
    return (ver.group(1) if ver else "2.1",
            "iOS %s or later" % min_os.group(1) if min_os else "iOS")


def git_date(paths):
    """Honest lastmod: today if any input is uncommitted, else the newest commit
    date (YYYY-MM-DD) touching any of the inputs. Falls back to today."""
    today = datetime.date.today().isoformat()
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--"] + paths,
                               capture_output=True, text=True, cwd=WEB, timeout=10).stdout.strip()
        if dirty:
            return today
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--"] + paths,
                             capture_output=True, text=True, cwd=WEB, timeout=10).stdout.strip()
        return out or today
    except Exception:
        return today


def compute_lastmods():
    # every page's output also depends on the shared translation/meta/build inputs
    common = ["assets/i18n.js", "_meta_i18n.json", "_build_pages.py"]
    return {p: git_date([p] + common) for p in PAGES}


def alternates(page):
    """(hreflang, url) pairs shared by the head block and the sitemap."""
    pairs = []
    for _c, s, hl, _l, _og in LANGS:
        pairs.append((hl, page_url(page, s)))
        if hl in HREFLANG_ALIASES:
            pairs.append((HREFLANG_ALIASES[hl], page_url(page, s)))
    pairs.append(("x-default", page_url(page, "")))
    return pairs


def jsonld_script(graph):
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return '  <script type="application/ld+json">%s</script>' % payload


def jsonld_index(slug, hreflang, meta_entry, app_version, min_os, lastmod):
    org = {
        "@type": "Organization",
        "@id": SITE + "/#org",
        "name": "Globetrotter Studio",
        "url": SITE + "/",
        "email": CONTACT_EMAIL,
        "logo": SITE + "/assets/icon-large.png",
    }
    website = {
        "@type": "WebSite",
        "@id": SITE + "/#website",
        "name": "BlindClock",
        "url": SITE + "/",
        "publisher": {"@id": SITE + "/#org"},
        "inLanguage": [hl for _c, _s, hl, _l, _og in LANGS],
    }
    app = {
        "@type": "SoftwareApplication",
        "@id": SITE + "/#app",
        "name": "BlindClock",
        "description": meta_entry["desc"],
        "url": page_url("index.html", slug),
        "image": OG_IMAGE,
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": min_os,
        "softwareVersion": app_version,
        "dateModified": lastmod,
        "inLanguage": hreflang,
        "installUrl": APPSTORE_URL,
        "sameAs": [APPSTORE_URL],
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD",
            "description": "Free download. Optional one-time BlindClock Pro in-app purchase — no subscription.",
        },
        "featureList": FEATURE_LIST,
        "author": {"@id": SITE + "/#org"},
    }
    return jsonld_script([org, website, app])


def jsonld_faq(slug, hreflang, faq_pairs):
    if not faq_pairs:
        return None
    faq = {
        "@type": "FAQPage",
        "@id": page_url("support.html", slug) + "#faq",
        "url": page_url("support.html", slug),
        "inLanguage": hreflang,
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in faq_pairs
        ],
    }
    return jsonld_script([faq])


def head_block(page, slug, hreflang, og_locale, meta_entry, jsonld=None):
    url = page_url(page, slug)
    title = htmllib.escape(meta_entry["title"], quote=True)
    desc = htmllib.escape(meta_entry["desc"], quote=True)

    lines = ['  <link rel="canonical" href="%s">' % url]
    for hl, href in alternates(page):
        lines.append('  <link rel="alternate" hreflang="%s" href="%s">' % (hl, href))

    lines += [
        '  <meta property="og:type" content="website">',
        '  <meta property="og:site_name" content="BlindClock">',
        '  <meta property="og:url" content="%s">' % url,
        '  <meta property="og:title" content="%s">' % title,
        '  <meta property="og:description" content="%s">' % desc,
        '  <meta property="og:image" content="%s">' % OG_IMAGE,
        '  <meta property="og:image:width" content="1200">',
        '  <meta property="og:image:height" content="630">',
        '  <meta property="og:image:alt" content="BlindClock app icon and name — poker tournament blind timer for iPhone and iPad">',
        '  <meta property="og:locale" content="%s">' % og_locale,
    ]
    lines += ['  <meta property="og:locale:alternate" content="%s">' % other
              for _c, _s, _hl, _l, other in LANGS if other != og_locale]
    lines += [
        '  <meta name="twitter:card" content="summary_large_image">',
        '  <meta name="twitter:title" content="%s">' % title,
        '  <meta name="twitter:description" content="%s">' % desc,
        '  <meta name="twitter:image" content="%s">' % OG_IMAGE,
    ]
    if jsonld:
        lines.append(jsonld)
    return "\n".join(lines)


def inject_head(html, block):
    new = HEAD_START + "\n" + block + "\n  " + HEAD_END
    if HEAD_START in html and HEAD_END in html:
        return re.sub(re.escape(HEAD_START) + r".*?" + re.escape(HEAD_END), lambda m: new, html, count=1, flags=re.DOTALL)
    return html.replace("</head>", new + "\n</head>", 1)


def rewrite_assets(html):
    # subfolder pages are one level deep → point at the shared /assets at root
    return html.replace('"assets/', '"../assets/').replace("(assets/", "(../assets/")


def write_sitemap(lastmods):
    urls = []
    for page in PAGES:
        alt = "".join('\n    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (hl, href)
                      for hl, href in alternates(page))
        for _c, slug, _hl, _l, _og in LANGS:
            urls.append("  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>%s\n  </url>"
                        % (page_url(page, slug), lastmods[page], alt))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n")
    open(os.path.join(WEB, "sitemap.xml"), "w", encoding="utf-8").write(xml)


def write_robots():
    # GEO posture: fully open. AI answer engines (ChatGPT search via OAI-SearchBot
    # + Bing's index, Perplexity, Claude, Google AI Overviews, Siri/Apple
    # Intelligence via Applebot) can only cite pages their bots may fetch.
    open(os.path.join(WEB, "robots.txt"), "w", encoding="utf-8").write(
        "# BlindClock — deliberately open to ALL crawlers, including AI answer\n"
        "# engines (OAI-SearchBot, Bingbot, Googlebot, PerplexityBot,\n"
        "# Claude-SearchBot, Applebot, ...). Blocking them removes the site from\n"
        "# ChatGPT / Perplexity / Claude / AI Overviews / Siri answers — keep open.\n"
        "# Strategy notes: docs/product/seo-geo.md in the app repo.\n"
        "\n"
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "Sitemap: %s/sitemap.xml\n" % SITE)


def write_llms(app_version, min_os, lastmods):
    langs_line = ", ".join("/%s/ %s" % (s, l) for _c, s, _hl, l, _og in LANGS if s)
    txt = """# BlindClock

> BlindClock is a poker tournament blind timer (tournament clock) app for iPhone and iPad by Globetrotter Studio. Free download with an optional one-time Pro purchase — no account, no ads, no subscription. Requires %s. Current version: %s (site updated %s).

Key features: blind structure generator, time bank, payout calculator, Live Activity and Dynamic Island, iPad landscape table display, live table stats (players remaining, average stack), iCloud sync. Available in 12 languages.

## Pages

- [Home](%s/): features and what's new in the latest version
- [Support & FAQ](%s/support.html): sounds, Pro purchase and restore, iCloud sync, sharing tournaments, Live Activity, supported devices
- [Privacy Policy](%s/privacy.html): no account, no ads, anonymous analytics only

## App Store

- [BlindClock on the App Store](%s)

## Languages

English lives at the site root; the same three pages exist under each slug: %s.
""" % (min_os, app_version, lastmods["index.html"], SITE, SITE, SITE, APPSTORE_URL, langs_line)
    open(os.path.join(WEB, "llms.txt"), "w", encoding="utf-8").write(txt)


def main():
    bc = load_bc_strings()
    meta = json.load(open(os.path.join(WEB, "_meta_i18n.json"), encoding="utf-8"))
    templates = {p: open(os.path.join(WEB, p), encoding="utf-8").read() for p in PAGES}
    app_version, min_os = parse_app_facts(templates["index.html"])
    lastmods = compute_lastmods()

    # coverage check: every data-i18n key should exist in every non-English language
    keys = set(re.findall(r'data-i18n="([^"]+)"', "".join(templates.values())))
    for code, _s, _hl, _l, _og in LANGS:
        if code == "en":
            continue
        miss = sorted(k for k in keys if k not in bc.get(code, {}))
        if miss:
            print("  [warn] %s missing %d body key(s): %s%s" % (code, len(miss), ", ".join(miss[:8]), "…" if len(miss) > 8 else ""))
        for pk in PAGEKEY.values():
            if code not in meta[pk]:
                print("  [warn] %s missing meta for page '%s' (falling back to en)" % (code, pk))

    written = []
    for code, slug, hreflang, _label, og_locale in LANGS:
        outdir = WEB if not slug else os.path.join(WEB, slug)
        os.makedirs(outdir, exist_ok=True)
        for page in PAGES:
            html = translate_body(templates[page], code, bc)
            html = strip_runtime(html)
            html = set_html_lang(html, hreflang)
            m = meta[PAGEKEY[page]].get(code, meta[PAGEKEY[page]]["en"])
            html = set_meta(html, m)
            if page == "index.html":
                jld = jsonld_index(slug, hreflang, m, app_version, min_os, lastmods[page])
            elif page == "support.html":
                jld = jsonld_faq(slug, hreflang, extract_faq(html))
            else:
                jld = None
            html = inject_head(html, head_block(page, slug, hreflang, og_locale, m, jld))
            if slug:
                html = rewrite_assets(html)
            open(os.path.join(outdir, page), "w", encoding="utf-8").write(html)
            written.append(os.path.relpath(os.path.join(outdir, page), WEB))

    write_sitemap(lastmods)
    write_robots()
    write_llms(app_version, min_os, lastmods)
    print("=== WROTE %d pages + sitemap.xml + robots.txt + llms.txt ===" % len(written))
    print("  app %s · %s · lastmod %s" % (app_version, min_os, ", ".join("%s=%s" % (PAGEKEY[p], d) for p, d in lastmods.items())))
    print("  langs: " + ", ".join("%s→/%s" % (c, s or "(root)") for c, s, _h, _l, _og in LANGS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
