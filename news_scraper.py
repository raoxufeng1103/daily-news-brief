#!/usr/bin/env python3
"""每日新闻简报 · BBC/Reuters/人民网/新浪/自贡 """
import urllib.request, ssl, json, time, re, xml.etree.ElementTree as ET, sys, os

ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, t=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=t, context=ctx) as resp:
        return resp.read().decode('utf-8', errors='replace')

def parse_rss(xml_text):
    root = ET.fromstring(xml_text)
    return [(item.find("title").text or "").strip() for item in root.findall(".//item")]

now = time.time()
GMB = ['足彩','竞彩','彩票','开奖','投注','赔率','盘口','彩民','刮中','中奖','福彩','体彩']
NE = ['光伏','锂电','风电','储能','新能源','电动','电池','充电','宁德','比亚迪','氢能','碳中和']

sections = {}

# BBC
try:
    titles = parse_rss(fetch("https://feeds.bbci.co.uk/news/rss.xml"))
    sections['bbc'] = [{"title": t, "source": "BBC"} for t in titles[:10]]
    print(f"BBC: {len(sections['bbc'])} items", file=sys.stderr)
except Exception as e:
    print(f"BBC failed: {e}", file=sys.stderr)

# Reuters via Google News
try:
    gnews = fetch("https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en")
    titles = parse_rss(gnews)
    sections['reuters'] = [{"title": t, "source": "Reuters"} for t in titles[:10]]
except: pass

# 人民网
try:
    titles = parse_rss(fetch("http://www.people.com.cn/rss/politics.xml"))
    sections['rmw'] = [{"title": t, "source": "人民网"} for t in titles[:12]]
except: pass

# China Daily
try:
    titles = parse_rss(fetch("https://www.chinadaily.com.cn/rss/world_rss.xml"))
    sections['cd'] = [{"title": t, "source": "China Daily"} for t in titles[:10]]
except: pass

# CGTN
try:
    titles = parse_rss(fetch("https://www.cgtn.com/subscribe/rss/section/world.xml"))
    sections['cgtn'] = [{"title": t, "source": "CGTN"} for t in titles[:10]]
except: pass

# Sina tech/sports/finance
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
    sections['sina_体育'] = [i for i in sections['sina_体育'] 
        if not any(k in i['title'] for k in GMB)][:8]

# Ziyang
try:
    html = fetch("https://zigong.scol.com.cn")
    titles = re.findall(r'<a[^>]*>([^<]{10,60})</a>', html)
    sections['zigong'] = [{"title": t.strip(), "source": "自贡新闻网"} 
        for t in titles if any(k in t for k in ['自贡','四川','供电','数据','献血','工会'])][:8]
except: pass

# Output JSON
print(json.dumps(sections, ensure_ascii=False, indent=2))
