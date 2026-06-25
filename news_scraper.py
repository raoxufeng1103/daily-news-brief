#!/usr/bin/env python3
"""China News Aggregator v2 - 10 foreign sources, full text"""
import urllib.request, ssl, json, time, re, xml.etree.ElementTree as ET, sys, html as html_mod

ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

CKW = ["china","chinese","beijing","xi jinping","li qiang","wang yi",
       "sino-","taiwan","hong kong","xinjiang","tibet","south china sea",
       "belt and road","made in china","huawei","tencent","alibaba",
       "tiktok","shein","temu","cpec","china-pakistan","shenzhen",
       "shanghai","renminbi","yuan","pboc","zhipu","deepseek","baidu",
       "xiaomi","didi","meituan","chinese economy","china economy",
       "chinese market","chinese official","chinese ambassador","chinese foreign"]

def is_cn(t):
    tl = t.lower()
    return any(k in tl for k in CKW)

def fetch(url, t=20):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=t, context=ctx) as r:
        return r.read().decode("utf-8","replace")

def extract(html_text):
    if not html_text: return ""
    h = re.sub(r"<(script|style|nav|footer|header|aside)[^>]*>.*?</>", "", html_text, flags=re.DOTALL|re.IGNORECASE)
    for pat in [
        r'<div[^>]*data-component="text-block"[^>]*>(.*?)</div>\s*</div>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*(?:article-body|story-body|entry-content|content-body|field-item|news-body|article-text|post-content|content__body|Paywall)[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*text[^"]*"[^>]*>(.*?)</div>',
        r'<body[^>]*>(.*?)</body>',
    ]:
        m = re.search(pat, h, re.DOTALL)
        if m:
            b = m.group(1)
            b = re.sub(r"<br\s*/?>", "
", b)
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
        if t: res.append({"t":t, "l":link, "d":d})
    return res

def hp_links(html):
    links = set()
    for m in re.finditer(r'<a[^>]*href=["'](https?://[^"']+)["'][^>]*>([^<]{25,})</a>', html):
        links.add((m.group(1), m.group(2).strip()))
    return list(links)

results = []
def add(s,t,u,sm,ft):
    results.append({"source":s,"title":t,"url":u,"summary":sm[:200],"full_text":ft[:3000]})

print("ChinaNewsAgg v2 starting...", file=sys.stderr)

# 1. BBC
for u in ["https://feeds.bbci.co.uk/news/rss.xml","https://feeds.bbci.co.uk/news/world/rss.xml"]:
    try:
        items = parse_rss(fetch(u))
        for it in items:
            if is_cn(it["t"]+" "+it["d"]):
                ft = ""
                if it["l"]:
                    try: ft = extract(fetch(it["l"]))
                    except: ft = it["d"]
                add("BBC",it["t"],it["l"],it["d"],ft)
        break
    except: pass
print(f"BBC: {sum(1 for r in results if r['source']=='BBC')}", file=sys.stderr)

# 2. Reuters
try:
    items = parse_rss(fetch("https://news.google.com/rss/search?q=site:reuters.com+china&hl=en-US&gl=US&ceid=US:en"))
    for it in items:
        if is_cn(it["t"]):
            ft = ""
            if it["l"] and "reuters.com" in it["l"]:
                try: ft = extract(fetch(it["l"],15))
                except: pass
            add("Reuters",it["t"],it.get("l",""),it.get("d",""),ft)
except: pass
print(f"Reuters: {sum(1 for r in results if r['source']=='Reuters')}", file=sys.stderr)

# 3. Bloomberg
try:
    items = parse_rss(fetch("https://news.google.com/rss/search?q=site:bloomberg.com+china&hl=en-US&gl=US&ceid=US:en"))
    for it in items:
        if is_cn(it["t"]):
            add("Bloomberg",it["t"],it.get("l",""),it.get("d",""),"")
except: pass
print(f"Bloomberg: {sum(1 for r in results if r['source']=='Bloomberg')}", file=sys.stderr)

# 4. AP
try:
    items = parse_rss(fetch("https://news.google.com/rss/search?q=site:apnews.com+china&hl=en-US&gl=US&ceid=US:en"))
    for it in items:
        if is_cn(it["t"]):
            ft = ""
            if it["l"]:
                try: ft = extract(fetch(it["l"],15))
                except: pass
            add("AP",it["t"],it.get("l",""),it.get("d",""),ft)
except: pass
print(f"AP: {sum(1 for r in results if r['source']=='AP')}", file=sys.stderr)

# 5. AFP
try:
    items = parse_rss(fetch("https://news.google.com/rss/search?q=site:afp.com+china&hl=en-US&gl=US&ceid=US:en"))
    for it in items:
        if is_cn(it["t"]):
            add("AFP",it["t"],it.get("l",""),it.get("d",""),"")
except: pass
print(f"AFP: {sum(1 for r in results if r['source']=='AFP')}", file=sys.stderr)

# 6. Nikkei Asia
try:
    items = parse_rss(fetch("https://news.google.com/rss/search?q=site:asia.nikkei.com+china&hl=en-US&gl=US&ceid=US:en"))
    for it in items:
        if is_cn(it["t"]):
            ft = ""
            if it["l"]:
                try: ft = extract(fetch(it["l"],15))
                except: pass
            add("Nikkei Asia",it["t"],it.get("l",""),it.get("d",""),ft)
except: pass
print(f"Nikkei: {sum(1 for r in results if r['source']=='Nikkei Asia')}", file=sys.stderr)

# 7. APP Pakistan (homepage scrape)
try:
    html = fetch("https://www.app.com.pk/")
    for u,t in hp_links(html):
        if is_cn(t): add("APP (Pakistan)",t,u,"","")
except: pass
print(f"APP: {sum(1 for r in results if r['source']=='APP (Pakistan)')}", file=sys.stderr)

# 8. IRNA Iran (RSS + full text)
try:
    items = parse_rss(fetch("https://en.irna.ir/rss"))
    for it in items:
        if is_cn(it["t"]):
            ft = ""
            if it["l"]:
                try: ft = extract(fetch(it["l"],15))
                except: pass
            add("IRNA (Iran)",it["t"],it.get("l",""),it.get("d",""),ft)
except: pass
print(f"IRNA: {sum(1 for r in results if r['source']=='IRNA (Iran)')}", file=sys.stderr)

# 9. Tanjug Serbia (homepage scrape)
try:
    html = fetch("https://www.tanjug.rs/en")
    for u,t in hp_links(html):
        if is_cn(t): add("Tanjug (Serbia)",t,u,"","")
except: pass
print(f"Tanjug: {sum(1 for r in results if r['source']=='Tanjug (Serbia)')}", file=sys.stderr)

# 10. SAnews South Africa (homepage scrape)
try:
    html = fetch("https://www.sanews.gov.za/")
    for u,t in hp_links(html):
        if is_cn(t): add("SAnews (S.Africa)",t,u,"","")
except: pass
print(f"SAnews: {sum(1 for r in results if r['source']=='SAnews (S.Africa)')}", file=sys.stderr)

out = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(results), "articles": results}
print(json.dumps(out, ensure_ascii=False, indent=2))
