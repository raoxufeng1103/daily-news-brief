#!/usr/bin/env python3
"""China News Aggregator v2 - 10 foreign sources, China articles full text"""
import urllib.request, ssl, json, time, re, xml.etree.ElementTree as ET, sys, html as html_mod

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

CKW = [
    'china','chinese','beijing','xi jinping','li qiang','wang yi',
    'sino-','taiwan','hong kong','xinjiang','tibet','south china sea',
    'belt and road','made in china','huawei','tencent','alibaba',
    'tiktok','shein','temu','cpec','china-pakistan',
    'shenzhen','shanghai','renminbi','yuan','pboc',
    'zhipu','deepseek','baidu','xiaomi','didi','meituan',
    'chinese economy','china economy','chinese market',
    'chinese official','chinese ambassador','chinese foreign',
]

def is_cn(t):
    tl = t.lower()
    for k in CKW:
        if k in tl: return True
    return False

def fetch(url, t=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=t, context=ctx) as r:
        return r.read().decode('utf-8','replace')

def extract(html):
    html = re.sub(r'<(script|style|nav|footer|header)[^>]*>.*?</\1>', '', html, flags=re.DOTALL|re.IGNORECASE)
    for pat in [
        r'<div[^>]*data-component="text-block"[^>]*>(.*?)</div>\s*</div>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*(?:article-body|story-body|entry-content|content|field-item|body|news-body|article-text|Paywall)[^"]*"[^>]*>(.*?)</div>',
        r'<body[^>]*>(.*?)</body>',
    ]:
        m = re.search(pat, html, re.DOTALL)
        if m:
            body = m.group(1)
            body = re.sub(r'<[^>]+>', ' ', body)
            body = html_mod.unescape(body)
            body = re.sub(r'\s+', ' ', body).strip()
            return body[:2500]
    return ""

def rss(text):
    root = ET.fromstring(text)
    res = []
    for item in root.findall(".//item"):
        t = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        d = re.sub(r'<[^>]+>', '', (item.findtext("description") or "")[:200])
        if t: res.append({"t": t, "l": link, "d": d})
    return res

def hplinks(html):
    links = set()
    for m in re.finditer(r'<a[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>([^<]{25,})</a>', html):
        links.add((m.group(1), m.group(2).strip()))
    return list(links)

results = []
def add(s, t, u, sm, ft):
    results.append({"source": s, "title": t, "url": u, "summary": sm[:200], "full_text": ft[:2500]})

print("ChinaNewsAgg v2 starting...", file=sys.stderr)

# 1. BBC
for u in ["https://feeds.bbci.co.uk/news/rss.xml","https://feeds.bbci.co.uk/news/world/rss.xml"]:
    try:
        for it in rss(fetch(u)):
            if is_cn(it["t"]+" "+it["d"]):
                ft = ""
                if it["l"]:
                    try: ft = extract(fetch(it["l"]))
                    except: ft = it["d"]
                add("BBC", it["t"], it["l"], it["d"], ft)
        break
    except: pass

# 2-6 Google News
for s, q in [("Reuters","site:reuters.com+china"),("Bloomberg","site:bloomberg.com+china"),
             ("AP","site:apnews.com+china"),("AFP","site:afp.com+china"),
             ("Nikkei Asia","site:asia.nikkei.com+china")]:
    try:
        for it in rss(fetch(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")):
            if is_cn(it["t"]):
                ft = ""
                if it["l"] and s=="Nikkei Asia":
                    try: ft = extract(fetch(it["l"],15))
                    except: pass
                add(s, it["t"], it.get("l",""), it.get("d",""), ft)
    except: pass

# 7. APP Pakistan
try:
    for u,t in hplinks(fetch("https://www.app.com.pk/")):
        if is_cn(t): add("APP (Pakistan)", t, u, "", "")
except: pass

# 8. IRNA Iran
try:
    for it in rss(fetch("https://en.irna.ir/rss")):
        if is_cn(it["t"]):
            ft = ""
            if it["l"]:
                try: ft = extract(fetch(it["l"],15))
                except: pass
            add("IRNA (Iran)", it["t"], it.get("l",""), it.get("d",""), ft)
except: pass

# 9. Tanjug Serbia
try:
    for u,t in hplinks(fetch("https://www.tanjug.rs/en")):
        if is_cn(t): add("Tanjug (Serbia)", t, u, "", "")
except: pass

# 10. SAnews SA
try:
    for u,t in hplinks(fetch("https://www.sanews.gov.za/")):
        if is_cn(t): add("SAnews (S.Africa)", t, u, "", "")
except: pass

out = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(results), "articles": results}
print(json.dumps(out, ensure_ascii=False, indent=2))
