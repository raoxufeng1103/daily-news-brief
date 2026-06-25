#!/usr/bin/env python3
"""China News Aggregator v2 - 10 sources, full text extraction"""
import urllib.request, ssl, json, time, re, xml.etree.ElementTree as ET, sys, html as html_mod

ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

CKW = ["china","chinese","beijing","xi jinping","li qiang","wang yi",
       "taiwan","hong kong","xinjiang","tibet","south china sea",
       "belt and road","huawei","tencent","alibaba","tiktok","shein",
       "temu","cpec","renminbi","yuan","pboc","deepseek","baidu",
       "xiaomi","chinese economy","chinese market","chinese official"]

def is_cn(t):
    tl = t.lower()
    for k in CKW:
        if k in tl: return True
    return False

def fetch(url, t=20):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=t, context=ctx) as r:
        return r.read().decode("utf-8","replace")

def extract(html_text):
    if not html_text: return ""
    h = re.sub(r"<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", "", html_text, flags=re.DOTALL|re.IGNORECASE)
    pats = [
        r'<div[^>]*data-component="text-block"[^>]*>(.*?)</div>\s*</div>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*(?:article-body|story-body|entry-content|content-body|field-item|news-body|article-text|post-content|content__body|Paywall)[^"]*"[^>]*>(.*?)</div>',
        r'<body[^>]*>(.*?)</body>',
    ]
    for pat in pats:
        m = re.search(pat, h, re.DOTALL)
        if m:
            b = m.group(1)
            b = re.sub(r"<br\s*/?>", "\n", b)
            b = re.sub(r"<p[^>]*>", "\n", b)
            b = re.sub(r"<[^>]+>", " ", b)
            b = html_mod.unescape(b)
            b = re.sub(r"\s+", " ", b).strip()
            if len(b) > 150: return b[:3000]
    return ""

def parse_rss(text):
    root = ET.fromstring(text)
    res = []
    for item in root.findall(".//item"):
        t = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        d = re.sub(r"<[^>]+>", "", (item.findtext("description") or "")[:200])
        if t: res.append({"t": t, "l": link, "d": d})
    return res

def hp_links(html):
    links = set()
    for m in re.finditer(r'<a[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>([^<]{25,})</a>', html):
        links.add((m.group(1), m.group(2).strip()))
    return list(links)

results = []
def add(s, t, u, sm, ft):
    results.append({"source": s, "title": t, "url": u, "summary": sm[:200], "full_text": ft[:3000]})

print("ChinaNewsAgg v2 starting...", file=sys.stderr)

# 1. BBC
for u in ["https://feeds.bbci.co.uk/news/rss.xml","https://feeds.bbci.co.uk/news/world/rss.xml"]:
    try:
        items = parse_rss(fetch(u))
        for it in items:
            if is_cn(it["t"] + " " + it["d"]):
                ft = ""
                if it["l"]:
                    try: ft = extract(fetch(it["l"]))
                    except: ft = it["d"]
                add("BBC", it["t"], it["l"], it["d"], ft)
        break
    except: pass
print(f"BBC: {sum(1 for r in results if r['source']=='BBC')}", file=sys.stderr)

# 2-6: Google News RSS with full text
for src, q in [
    ("Reuters", "site:reuters.com+china"),
    ("Bloomberg", "site:bloomberg.com+china"),
    ("AP", "site:apnews.com+china"),
    ("AFP", "site:afp.com+china"),
    ("Nikkei Asia", "site:asia.nikkei.com+china"),
]:
    try:
        items = parse_rss(fetch(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"))
        for it in items:
            if is_cn(it["t"]):
                ft = ""
                if it["l"]:
                    try: ft = extract(fetch(it["l"], 15))
                    except: pass
                add(src, it["t"], it.get("l",""), it.get("d",""), ft)
    except: pass
    print(f"{src}: {sum(1 for r in results if r['source']==src)}", file=sys.stderr)

# 7. APP Pakistan
try:
    for u, t in hp_links(fetch("https://www.app.com.pk/")):
        if is_cn(t): add("APP (Pakistan)", t, u, "", "")
except: pass
print(f"APP: {sum(1 for r in results if r['source']=='APP (Pakistan)')}", file=sys.stderr)

# 8. IRNA Iran
try:
    items = parse_rss(fetch("https://en.irna.ir/rss"))
    for it in items:
        if is_cn(it["t"]):
            ft = ""
            if it["l"]:
                try: ft = extract(fetch(it["l"], 15))
                except: pass
            add("IRNA (Iran)", it["t"], it.get("l",""), it.get("d",""), ft)
except: pass
print(f"IRNA: {sum(1 for r in results if r['source']=='IRNA (Iran)')}", file=sys.stderr)

# 9. Tanjug Serbia
try:
    for u, t in hp_links(fetch("https://www.tanjug.rs/en")):
        if is_cn(t): add("Tanjug (Serbia)", t, u, "", "")
except: pass
print(f"Tanjug: {sum(1 for r in results if r['source']=='Tanjug (Serbia)')}", file=sys.stderr)

# 10. SAnews
try:
    for u, t in hp_links(fetch("https://www.sanews.gov.za/")):
        if is_cn(t): add("SAnews (S.Africa)", t, u, "", "")
except: pass
print(f"SAnews: {sum(1 for r in results if r['source']=='SAnews (S.Africa)')}", file=sys.stderr)

out = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(results), "articles": results}
print(json.dumps(out, ensure_ascii=False, indent=2))
