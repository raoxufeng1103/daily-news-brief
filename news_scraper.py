#!/usr/bin/env python3
"""每日新闻简报 · BBC/Reuters/Bloomberg/人民网/CGTN 自动抓取"""
import urllib.request, ssl, json, time, re, xml.etree.ElementTree as ET, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, t=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"})
    with urllib.request.urlopen(req, timeout=t, context=ctx) as resp:
        return resp.read().decode('utf-8', errors='replace')

def parse_rss(text):
    root = ET.fromstring(text)
    items = []
    for item in root.findall(".//item"):
        t = (item.find("title").text or "").strip()
        d_elem = item.find("description")
        d = (d_elem.text or "")[:200] if d_elem is not None else ""
        items.append({"title": t, "desc": d})
    return items

now = time.time()
GMB = ['足彩','竞彩','彩票','开奖','投注','赔率','盘口','彩民','刮中','中奖','福彩','体彩']
sections = {}

# ===== BBC: Try 3 different URLs =====
bbc_urls = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.bbc.com/news/10628494",
]
for url in bbc_urls:
    try:
        text = fetch(url)
        if "<?xml" in text or "<rss" in text:
            items = parse_rss(text)
            sections['bbc'] = [{"title": i['title'], "desc": i['desc'][:150], "source": "BBC"} for i in items[:10]]
            print(f"BBC: {len(items)} items from {url.split('/')[2]}", file=sys.stderr)
            break
        elif len(text) > 500 and ("BBC" in text or "news" in text.lower()):
            sections['bbc'] = [{"title": "BBC top stories fetched", "source": "BBC"}]
            break
    except Exception as e:
        print(f"BBC {url.split('/')[2]}: {type(e).__name__}", file=sys.stderr)

# ===== Reuters via Google News =====
try:
    rss = fetch("https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en")
    items = parse_rss(rss)
    sections['reuters'] = [{"title": i['title'], "source": "Reuters"} for i in items[:10]]
    print(f"Reuters: {len(sections['reuters'])} items", file=sys.stderr)
except Exception as e:
    print(f"Reuters: {type(e).__name__}", file=sys.stderr)

# ===== Bloomberg via Google News =====
try:
    rss = fetch("https://news.google.com/rss/search?q=site:bloomberg.com&hl=en-US&gl=US&ceid=US:en")
    items = parse_rss(rss)
    sections['bloomberg'] = [{"title": i['title'], "source": "Bloomberg"} for i in items[:8]]
    print(f"Bloomberg: {len(sections['bloomberg'])} items", file=sys.stderr)
except Exception as e:
    print(f"Bloomberg: {type(e).__name__}", file=sys.stderr)

# ===== China Daily =====
try:
    items = parse_rss(fetch("https://www.chinadaily.com.cn/rss/world_rss.xml"))
    sections['cd'] = [{"title": i['title'], "source": "China Daily"} for i in items[:10]]
except: pass

# ===== CGTN =====
try:
    items = parse_rss(fetch("https://www.cgtn.com/subscribe/rss/section/world.xml"))
    sections['cgtn'] = [{"title": i['title'], "source": "CGTN"} for i in items[:10]]
except: pass

# ===== 人民网 =====
try:
    items = parse_rss(fetch("http://www.people.com.cn/rss/politics.xml"))
    sections['rmw'] = [{"title": i['title'], "source": "人民网"} for i in items[:12]]
except: pass

# ===== Sina =====
for lid, cat in [(2515,"科技"),(2512,"体育"),(2516,"财经")]:
    try:
        data = json.loads(fetch(f"https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid={lid}&k=&num=50&page=1"))
        items = data.get("result",{}).get("data",[])
        key = f"sina_{cat}"
        sections[key] = [{"title": i['title'], "desc": i.get('intro','')[:120], "source": f"新浪{cat}"}
            for i in items if (now - int(i['ctime'])) < 86400]
    except: pass

# Filter sports (remove gambling)
if 'sina_体育' in sections:
    sections['sina_体育'] = [i for i in sections['sina_体育'] if not any(k in i['title'] for k in GMB)][:8]

# ===== Ziyang =====
try:
    html = fetch("https://zigong.scol.com.cn")
    titles = re.findall(r'<a[^>]*>([^<]{10,60})</a>', html)
    sections['zigong'] = [{"title": t.strip(), "source": "自贡新闻网"} 
        for t in titles if any(k in t for k in ['自贡','四川','供电','数据','献血','工会','彩灯'])][:8]
except: pass

print(json.dumps(sections, ensure_ascii=False, indent=2))
