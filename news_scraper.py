#!/usr/bin/env python3
"""China News Aggregator v3.1 - 11 sources, full text, 10-article limit, improved extraction + diagnostics"""
import urllib.request, ssl, json, time, re, xml.etree.ElementTree as ET, sys, html as html_mod, traceback
from datetime import datetime, timedelta, timezone

ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
MAX_PER_SOURCE = 10

CUTOFF = datetime.now(timezone.utc) - timedelta(days=4)

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
    fetch_log.append((url[:100], 'ERR:' + repr(last_err)[:200]))
    raise last_err

def extract(html_text, source_hint=""):
    """Extract article body text, with source-specific hints and robust fallbacks"""
    if not html_text: return ""
    h = re.sub(r"<(script|style|nav|footer|header|aside|noscript|iframe|form)[^>]*>.*?</\1>",
               "", html_text, flags=re.DOTALL|re.IGNORECASE)
    patterns = []
    if source_hint == "BBC":
        patterns = [r'<div[^>]*data-component="text-block"[^>]*>(.*?)</div>']
    elif source_hint == "APP":
        patterns = [r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>']
    elif source_hint == "IRNA":
        patterns = [r'<div[^>]*class="[^"]*(?:body|news-body|item-text|text|content)[^"]*"[^>]*>(.*?)</div>']
    generic = [
        r'<div[^>]*data-component="text-block"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*(?:article-body|story-body|entry-content|content-body|field-item|news-body|article-text|post-content|content__body|Paywall|article__content|article_body|rich-text|post-body|Article__content)[^"]*"[^>]*>(.*?)</div>',
        r'<body[^>]*>(.*?)</body>',
    ]
    patterns.extend(generic)
    for pat in patterns:
        matches = re.findall(pat, h, re.DOTALL)
        if matches:
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
                return text[:15000]
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', h, re.DOTALL)
    if paragraphs:
        text = "\n".join([re.sub(r"<[^>]+>", " ", p).strip() for p in paragraphs if len(p.strip()) > 10])
        text = html_mod.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 150:
            return text[:15000]
    return ""

def fetch_article_text(url, hint="", t=15):
    try:
        html = fetch(url, t, retries=0)
        text = extract(html, hint)
        if text and len(text) > 200:
            return text[:15000]
    except:
        pass
    return ""

def parse_date(date_str):
    if not date_str:
        return None
    s = date_str.strip()
    m = re.match(r'\w{3}, (\d{1,2}) (\w{3}) (\d{4}) (\d{2}):(\d{2}):(\d{2})', s)
    if m:
        day, mon, year, hh, mm, ss = m.groups()
        months = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                  "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
        if mon in months:
            return datetime(int(year), months[mon], int(day), int(hh), int(mm), int(ss), tzinfo=timezone.utc)
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})', s)
    if m:
        return datetime(*[int(x) for x in m.groups()], tzinfo=timezone.utc)
    return None

def is_recent(pub):
    dt = parse_date(pub)
    if dt is None:
        return False
    return dt >= CUTOFF

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
        pub = item.findtext("pubDate") or ""
        if t: res.append({"t": t, "l": link, "d": d, "pub": pub})
    if not res:
        ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.findall(ns + "entry"):
            t = (entry.findtext(ns + "title") or "").strip()
            link = ""
            for ln in entry.findall(ns + "link"):
                link = ln.get("href", "")
                break
            d = re.sub(r"<[^>]+>", "", (entry.findtext(ns + "summary") or "")[:300])
            pub = entry.findtext(ns + "published") or entry.findtext(ns + "updated") or ""
            if t: res.append({"t": t, "l": link, "d": d, "pub": pub})
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
fetch_log = []  # 诊断：记录每个外部请求成败

def add(s, t, u, sm, ft, pub=""):
    if source_counts.get(s, 0) >= MAX_PER_SOURCE:
        return False
    if len(results) >= 500:
        return False
    if pub and not is_recent(pub):
        return False
    t_norm = t.lower().strip()
    if any(r["title"].lower().strip() == t_norm for r in results):
        return False
    results.append({"source": s, "title": t, "url": u, "summary": sm[:2000], "full_text": ft[:15000], "pub_date": pub})
    source_counts[s] = source_counts.get(s, 0) + 1
    return True


def run():
    # ===== WorldMonitor API feeds (NASA EONET, USGS, Fear/Greed, GDACS) =====
    print("Fetching WorldMonitor API feeds...", file=sys.stderr)

    def safe_fetch_json(url, name="API"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=20)
            return json.loads(resp.read().decode())
        except Exception as e:
            print(f"  ⚠️ {name}: {e}", file=sys.stderr)
            fetch_log.append(('JSON:' + name, 'ERR:' + repr(e)[:160]))
            return None

    eonet = safe_fetch_json("https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=10", "NASA EONET")
    if eonet:
        for ev in eonet.get("events", []):
            title = ev.get("title", "?")
            cat = ev.get("categories", [{}])[0].get("title", "自然灾害")
            desc = f"{cat}：{title}。来源：NASA EONET全球事件观测系统。"
            url = f"https://eonet.gsfc.nasa.gov/api/v3/events/{ev.get('id','')}"
            add("NASA EONET", title, url, desc[:2000], desc[:15000], time.strftime("%Y-%m-%d"))
        print(f"  NASA EONET: {len(eonet.get('events',[]))} events", file=sys.stderr)

    usgs = safe_fetch_json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson", "USGS")
    if usgs:
        for eq in usgs.get("features", [])[:8]:
            mag = eq["properties"]["mag"]
            place = eq["properties"]["place"]
            title = f"M{mag}地震 - {place}"
            desc = f"美国地质调查局(USGS)记录到{place}发生M{mag}级地震。"
            url = eq["properties"]["url"]
            add("USGS", title, url, desc[:2000], desc[:15000], time.strftime("%Y-%m-%d"))
        print(f"  USGS: {len(usgs.get('features',[]))} quakes", file=sys.stderr)

    fng = safe_fetch_json("https://api.alternative.me/fng/?limit=2", "Fear&Greed")
    if fng and fng.get("data"):
        d = fng["data"][0]
        val = d.get("value", "?")
        cls = d.get("value_classification", "?")
        title = f"恐惧贪婪指数：{val}（{cls}）"
        desc = f"加密货币市场恐惧与贪婪指数当前为{val}，处于「{cls}」区间。0=极度恐惧，100=极度贪婪。该指数综合波动率、交易量、社交媒体、市场占比和趋势五个维度计算。"
        add("Market", title, "https://alternative.me/crypto/fear-and-greed-index/", desc[:2000], desc[:15000], time.strftime("%Y-%m-%d"))
        print(f"  Fear&Greed: {val} ({cls})", file=sys.stderr)

    gdacs = safe_fetch_json("https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?fromDate=" + (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d"), "GDACS")
    if gdacs:
        count = 0
        for ev in gdacs[:5] if isinstance(gdacs, list) else []:
            title = ev.get("eventname", ev.get("name", "?"))
            etype = ev.get("eventtype", "灾害")
            desc = f"GDACS全球灾害预警系统：{etype}「{title}」正在活跃。严重程度：{ev.get('severity', '?')}。"
            add("GDACS", str(title), f"https://www.gdacs.org/report.aspx?eventid={ev.get('eventid','')}", desc[:2000], desc[:15000], time.strftime("%Y-%m-%d"))
            count += 1
        print(f"  GDACS: {count} disasters", file=sys.stderr)

    print("WorldMonitor API feeds done.", file=sys.stderr)
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
                    if "china" in feed_url or is_cn(t_combined):
                        add("BBC", it["t"], it["l"], it["d"], "", it.get("pub",""))
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
            fetch_log.append(('BBC', 'ERR:' + repr(e)[:160]))
    print(f"BBC: {source_counts.get('BBC', 0)}", file=sys.stderr)

    # 2-6. Google News RSS sources (聚合各媒体官网涉华报道)
    gn_sources = [
        ("Reuters", "site:reuters.com+china", "Reuters"),
        ("Bloomberg", "site:bloomberg.com+china", "Bloomberg"),
        ("AP", "site:apnews.com+china", "AP"),
        ("Nikkei Asia", "site:asia.nikkei.com+china", "Nikkei"),
        ("Financial Times", "site:ft.com+china", "FT"),
        ("New York Times", "site:nytimes.com+china", "NYT"),
        ("BBC", "site:bbc.com+china", "BBC"),
        ("The Guardian", "site:theguardian.com+china", "Guardian"),
        ("Nature", "site:nature.com+china", "Nature"),
        ("CNN China", "CNN+china+news+update", "CNN"),
        ("AFP China", "AFP+china+news", "AFP"),
        ("Economist China", "The+Economist+china", "Economist"),
        ("Defense China", "defense+news+china+military", "Defense"),
        ("MIT Tech China", "MIT+Technology+Review+china", "MIT Tech"),
        ("China EV News", "china+electric+vehicle+BYD+NIO", "NEV"),
        ("China AI News", "china+artificial+intelligence+deepseek+kimi", "AI"),
        ("China Science", "china+science+physics+mathematics+breakthrough", "Science"),
        ("Kimi K3 News", "kimi+k3+moonshot+open+source+AI", "Kimi K3"),
        # 直接官网聚合（Google News 索引 Atlantic 官网涉华报道）
        ("The Atlantic", "site:theatlantic.com+china", "Atlantic"),
    ]
    for src, query, hint in gn_sources:
        try:
            time.sleep(2)
            items = parse_rss(fetch(f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"))
            for it in items:
                if is_cn(it["t"] + " " + it.get("d","")):
                    ft = it.get("d","")
                    if it["l"]:
                        try:
                            article_ft = fetch_article_text(it["l"], hint, 15)
                            if article_ft: ft = article_ft
                        except: pass
                    add(src, it["t"], it.get("l",""), it.get("d",""), ft, it.get("pub",""))
        except Exception as e:
            print(f"  {src}: {e}", file=sys.stderr)
            fetch_log.append((src, 'ERR:' + repr(e)[:160]))
        print(f"{src}: {source_counts.get(src, 0)}", file=sys.stderr)

    # 7. The Guardian China - Direct RSS with full text
    try:
        items = parse_rss(fetch("https://www.theguardian.com/world/china/rss"))
        for it in items:
            if is_cn(it["t"] + " " + it.get("d","")) or True:
                ft = it.get("d","")
                if it.get("l"):
                    try:
                        article_ft = fetch_article_text(it["l"], "BBC", 15)
                        if article_ft: ft = article_ft
                    except: pass
                add("The Guardian", it["t"], it.get("l",""), it.get("d",""), ft, it.get("pub",""))
    except Exception as e:
        print(f"  Guardian: {e}", file=sys.stderr)
        fetch_log.append(('Guardian', 'ERR:' + repr(e)[:160]))
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
                add("VOA News", it["t"], it.get("l",""), it.get("d",""), ft, it.get("pub",""))
    except Exception as e:
        print(f"  VOA: {e}", file=sys.stderr)
        fetch_log.append(('VOA', 'ERR:' + repr(e)[:160]))
    print(f"VOA: {source_counts.get('VOA News', 0)}", file=sys.stderr)

    # Output
    out = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(results),
           "articles": results, "source_counts": dict(source_counts), "fetch_log": fetch_log[-80:]}
    print(f"\n{'='*50}", file=sys.stderr)
    print(f"CUTOFF: {CUTOFF.strftime('%Y-%m-%d')} | TOTAL: {len(results)} articles from {len(source_counts)} sources", file=sys.stderr)
    for src, cnt in sorted(source_counts.items()):
        ft_count = sum(1 for r in results if r["source"] == src and r.get("full_text") and len(r["full_text"]) > 80)
        print(f"  {src}: {cnt} ({ft_count} with full text)", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        fetch_log.append(("FATAL", repr(e)[:400]))
        traceback.print_exc()
        out = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(results),
               "articles": results, "source_counts": dict(source_counts),
               "fetch_log": fetch_log[-80:], "fatal": repr(e)[:400]}
        print(json.dumps(out, ensure_ascii=False, indent=2))
