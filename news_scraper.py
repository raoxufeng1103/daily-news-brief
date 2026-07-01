#!/usr/bin/env python3
"""China News Aggregator v3 - 10 sources, full text, 10-article limit, improved extraction"""
import urllib.request, ssl, json, time, re, xml.etree.ElementTree as ET, sys, html as html_mod

ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
MAX_PER_SOURCE = 10

CKW = ["china","chinese","beijing","xi jinping","li qiang","wang yi",
       "taiwan","hong kong","xinjiang","tibet","south china sea",
       "belt and road","huawei","tencent","alibaba","tiktok","shein",
       "temu","cpec","renminbi","yuan","pboc","deepseek","baidu",
       "xiaomi","chinese economy","chinese market","chinese official",
       "sino-","brics","shanghai","shenzhen","guangzhou"]

def is_cn(t):
    tl = t.lower()
    for k in CKW:
        if k in tl: return True
    return False

def fetch(url, t=20, retries=2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=t, context=ctx) as r:
                return r.read().decode("utf-8","replace")
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(2)
    raise last_err

def extract(html_text, source_hint=""):
    """Extract article body text, with source-specific hints and robust fallbacks"""
    if not html_text: return ""
    
    # Remove noise
    h = re.sub(r"<(script|style|nav|footer|header|aside|noscript|iframe|form)[^>]*>.*?</\1>", 
               "", html_text, flags=re.DOTALL|re.IGNORECASE)
    
    # Build patterns: source-specific first, then generic
    patterns = []
    
    if source_hint == "BBC":
        patterns = [
            r'<div[^>]*data-component="text-block"[^>]*>(.*?)</div>',
        ]
    elif source_hint == "APP":
        patterns = [
            r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>',
        ]
    elif source_hint == "IRNA":
        patterns = [
            r'<div[^>]*class="[^"]*(?:body|news-body|item-text|text|content)[^"]*"[^>]*>(.*?)</div>',
        ]
    
    # Generic patterns (same as v2 that worked)
    generic = [
        r'<div[^>]*data-component="text-block"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*(?:article-body|story-body|entry-content|content-body|field-item|news-body|article-text|post-content|content__body|Paywall|article__content|article_body|rich-text|post-body|Article__content)[^"]*"[^>]*>(.*?)</div>',
        r'<body[^>]*>(.*?)</body>',
    ]
    patterns.extend(generic)
    
    for pat in patterns:
        # For non-greedy patterns, use findall to collect all matches
        matches = re.findall(pat, h, re.DOTALL)
        if matches:
            # Combine all matched blocks
            combined = []
            for m in matches:
                b = m
                b = re.sub(r"<br\s*/?>", "\n", b)
                b = re.sub(r"<p[^>]*>", "\n", b)
                b = re.sub(r"<li[^>]*>", "\n- ", b)
                b = re.sub(r"</li>", "", b)
                b = re.sub(r"<h[1-6][^>]*>", "\n", b)
                b = re.sub(r"</h[1-6]>", "\n", b)
                b = re.sub(r"<[^>]+>", " ", b)
                b = html_mod.unescape(b)
                combined.append(b)
            
            text = "\n".join(combined)
            text = re.sub(r"\n\s*\n", "\n", text)
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n +", "\n", text)
            text = text.strip()
            if len(text) > 150:
                return text[:3000]
    
    # Last resort: all <p> tags
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', h, re.DOTALL)
    if paragraphs:
        text = "\n".join([re.sub(r"<[^>]+>", " ", p).strip() for p in paragraphs if len(p.strip()) > 10])
        text = html_mod.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 150:
            return text[:3000]
    return ""

def fetch_article_text(url, hint="", t=20):
    """Get article body: try direct fetch, then Jina AI proxy"""
    # Method 1: Direct fetch
    try:
        html = fetch(url, t, retries=1)
        text = extract(html, hint)
        if text and len(text) > 200:
            return text
    except: pass
    
    # Method 2: Jina AI reader proxy (free, bypasses paywalls)
    try:
        proxy = "https://r.jina.ai/" + url
        req = urllib.request.Request(proxy, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/plain"
        })
        ctx2 = ssl.create_default_context()
        ctx2.check_hostname = False; ctx2.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=30, context=ctx2) as r:
            text = r.read().decode("utf-8","replace")
            # Clean Jina AI header lines
            text = re.sub(r'^Title:.*\n', '', text)
            text = re.sub(r'^URL Source:.*\n', '', text)
            text = text.strip()
            if text and len(text) > 200:
                return text[:3000]
    except: pass
    
    return ""

def parse_rss(text):
    root = ET.fromstring(text)
    res = []
    for item in root.findall(".//item"):
        t = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not link:
            for ln in item.findall("{http://www.w3.org/2005/Atom}link"):
                link = ln.get("href", "")
                break
        d = re.sub(r"<[^>]+>", "", (item.findtext("description") or "")[:2000])
        if t: res.append({"t": t, "l": link, "d": d})
    if not res:
        ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.findall(ns + "entry"):
            t = (entry.findtext(ns + "title") or "").strip()
            link = ""
            for ln in entry.findall(ns + "link"):
                link = ln.get("href", "")
                break
            d = re.sub(r"<[^>]+>", "", (entry.findtext(ns + "summary") or "")[:300])
            if t: res.append({"t": t, "l": link, "d": d})
    return res

def hp_links_container(html):
    links = set()
    for m in re.finditer(r'<(?:h[1-4]|div)[^>]*>\s*<a[^>]*href=[\"\'](https?://[^\"\']+)[\"\'][^>]*>(.*?)</a>', html, re.DOTALL):
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if len(text) > 15 and not any(skip in text.lower() for skip in ["read more","click here","ad","subscribe","cookie","privacy"]):
            links.add((m.group(1), text))
    if len(links) < 3:
        for m in re.finditer(r'<a[^>]*href=[\"\'](https?://[^\"\']+)[\"\'][^>]*>([^<]{20,})</a>', html):
            text = m.group(2).strip()
            if not any(skip in text.lower() for skip in ["read more","click here","ad","subscribe","cookie","privacy"]):
                links.add((m.group(1), text))
    return list(links)

results = []
source_counts = {}

def add(s, t, u, sm, ft):
    if source_counts.get(s, 0) >= MAX_PER_SOURCE:
        return False
    if len(results) >= 500:
        return False
    t_norm = t.lower().strip()
    if any(r["title"].lower().strip() == t_norm for r in results):
        return False
    results.append({"source": s, "title": t, "url": u, "summary": sm[:2000], "full_text": ft[:3000]})
    source_counts[s] = source_counts.get(s, 0) + 1
    return True

print("ChinaNewsAgg v3 starting...", file=sys.stderr)

# 1. BBC - China-specific + Asia RSS
bbc_feeds = [
    "https://feeds.bbci.co.uk/news/world/asia/china/rss.xml",
    "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
]
for feed_url in bbc_feeds:
    try:
        items = parse_rss(fetch(feed_url))
        for it in items:
            t_combined = it["t"] + " " + it.get("d","")
            if source_counts.get("BBC", 0) < MAX_PER_SOURCE:
                # BBC China feed doesn't need keyword filter
                if "china" in feed_url or is_cn(t_combined):
                    add("BBC", it["t"], it["l"], it["d"], "")
                    if it["l"]:
                        try:
                            ft = fetch_article_text(it["l"], "BBC", 15)
                            if ft:
                                for r in reversed(results):
                                    if r["source"] == "BBC" and r["title"] == it["t"]:
                                        r["full_text"] = ft
                                        break
                        except: pass
    except Exception as e:
        print(f"  BBC feed {feed_url}: {e}", file=sys.stderr)
print(f"BBC: {source_counts.get('BBC', 0)}", file=sys.stderr)

# 2-6. Google News RSS sources
gn_sources = [
    ("Reuters", "site:reuters.com+china", "Reuters"),
    ("Bloomberg", "site:bloomberg.com+china", "Bloomberg"),
    ("AP", "site:apnews.com+china", "AP"),
    ("AFP", "site:afp.com+china", "AFP"),
    ("Nikkei Asia", "site:asia.nikkei.com+china", "Nikkei"),
]
for src, query, hint in gn_sources:
    try:
        time.sleep(2)  # Avoid Google rate limiting
        items = parse_rss(fetch(f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"))
        for it in items:
            if is_cn(it["t"]):
                ft = it.get("d","")
                if it["l"]:
                    try:
                        article_ft = fetch_article_text(it["l"], hint, 15)
                        if article_ft: ft = article_ft
                    except: pass
                add(src, it["t"], it.get("l",""), it.get("d",""), ft)
    except Exception as e:
        print(f"  {src}: {e}", file=sys.stderr)
    print(f"{src}: {source_counts.get(src, 0)}", file=sys.stderr)

# 7. The Guardian China - Direct RSS with full text
try:
    items = parse_rss(fetch("https://www.theguardian.com/world/china/rss"))
    for it in items:
        if is_cn(it["t"] + " " + it.get("d","")) or True:  # China section, filter by section
            ft = it.get("d","")
            if it.get("l"):
                try:
                    article_ft = fetch_article_text(it["l"], "BBC", 15)  # Guardian similar to BBC
                    if article_ft: ft = article_ft
                except: pass
            add("The Guardian", it["t"], it.get("l",""), it.get("d",""), ft)
except Exception as e:
    print(f"  Guardian: {e}", file=sys.stderr)
print(f"Guardian: {source_counts.get('The Guardian', 0)}", file=sys.stderr)

# 8. VOA News China - RSS feed
try:
    items = parse_rss(fetch("https://news.google.com/rss/search?q=site:voanews.com+china&hl=en-US&gl=US&ceid=US:en"))
    for it in items:
        if is_cn(it["t"] + " " + it.get("d","")):
            ft = it.get("d","")
            if it.get("l"):
                try:
                    article_ft = fetch_article_text(it["l"], "BBC", 15)
                    if article_ft: ft = article_ft
                except: pass
            add("VOA News", it["t"], it.get("l",""), it.get("d",""), ft)
except Exception as e:
    print(f"  VOA: {e}", file=sys.stderr)
print(f"VOA: {source_counts.get('VOA News', 0)}", file=sys.stderr)

# Output
out = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(results), "articles": results}
print(f"\n{'='*50}", file=sys.stderr)
print(f"TOTAL: {len(results)} articles from {len(source_counts)} sources", file=sys.stderr)
for src, cnt in sorted(source_counts.items()):
    ft_count = sum(1 for r in results if r["source"] == src and r.get("full_text") and len(r["full_text"]) > 80)
    print(f"  {src}: {cnt} ({ft_count} with full text)", file=sys.stderr)
print(json.dumps(out, ensure_ascii=False, indent=2))
