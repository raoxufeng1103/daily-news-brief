#!/usr/bin/env python3
import json, sys
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC_COLORS = {
    "BBC":"BB191F","Reuters":"FF8000","Bloomberg":"0053A0","AP":"000000",
    "AFP":"003D7A","Nikkei Asia":"8B0000","APP (Pakistan)":"014B1A",
    "IRNA (Iran)":"239B56","Tanjug (Serbia)":"00437C","SAnews (S.Africa)":"006633",
}

def add_url(p, text, url):
    part = p.part
    rid = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    hl = OxmlElement('w:hyperlink')
    hl.set(qn('r:id'), rid)
    rn = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    c = OxmlElement('w:color'); c.set(qn('w:val'), '0563C1'); rPr.append(c)
    u = OxmlElement('w:u'); u.set(qn('w:val'), 'single'); rPr.append(u)
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '20'); rPr.append(sz)
    rn.append(rPr); rn.text = text; hl.append(rn); p._p.append(hl)


def translate(texts):
    """Translate English titles to Chinese via GLM API"""
    key = os.environ.get("GLM_API_KEY", "")
    if not key or key == "***": return [""]*len(texts)
    import urllib.request, ssl, json, time
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    results = []
    chunks = [texts[i:i+25] for i in range(0,len(texts),25)]
    for chunk in chunks:
        q = "Translate to Chinese, one per line:
" + "
".join(f"- {t}" for t in chunk)
        try:
            p = json.dumps({"model":"glm-4.7-flash","messages":[{"role":"user","content":q}],"max_tokens":4096}).encode()
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                data=p, headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}
            ), timeout=60, context=ctx).read())
            txt = r["choices"][0]["message"]["content"].strip()
            lines = [l.strip().lstrip("- ") for l in txt.split("
") if l.strip()]
            results.extend(lines[:len(chunk)])
        except:
            results.extend([""]*len(chunk))
        time.sleep(0.5)
    return results

def make_doc(data):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21); sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.5); sec.bottom_margin = Cm(2)
    sec.left_margin = Cm(2.5); sec.right_margin = Cm(2.5)
    
    for _ in range(4): doc.add_paragraph('')
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run('China News Briefing'); r.font.size = Pt(32)
    r.font.color.rgb = RGBColor(0xBB,0x19,0x1F); r.bold = True
    
    t2 = doc.add_paragraph(); t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = t2.add_run('涉华新闻日报'); r2.font.size = Pt(24)
    r2.font.color.rgb = RGBColor(0x33,0x33,0x33)
    doc.add_paragraph('')
    
    info = doc.add_paragraph(); info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = info.add_run(data.get("generated_at","")); r3.font.size = Pt(14)
    r3.font.color.rgb = RGBColor(0x66,0x66,0x66)
    doc.add_paragraph('')
    
    tot = doc.add_paragraph(); tot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r4 = tot.add_run(f"Total: {data.get('total',0)} China articles")
    r4.font.size = Pt(16); r4.font.color.rgb = RGBColor(0xBB,0x19,0x1F); r4.bold = True
    doc.add_page_break()
    
    articles = data.get("articles", [])
    groups = {}
    # Translate titles
    all_titles = [item["title"] for src,items in groups.items() for item in items]
    cn_titles = translate(all_titles)
    title_idx = 0
    for a in articles:
        s = a.get("source","Other")
        if s not in groups: groups[s] = []
        groups[s].append(a)
    
    gidx = 0
    for src, items in groups.items():
        color = SRC_COLORS.get(src,"333333")
        sh = doc.add_paragraph()
        sr = sh.add_run(f"  {src}  "); sr.font.size = Pt(16)
        sr.bold = True; sr.font.color.rgb = RGBColor(0xFF,0xFF,0xFF)
        shd = OxmlElement('w:shd'); shd.set(qn('w:fill'),color); shd.set(qn('w:val'),'clear')
        sr._element.get_or_add_rPr().append(shd)
        
        for item in items:
            gidx += 1
            tp = doc.add_paragraph()
            nr = tp.add_run(f" #{gidx} "); nr.font.size = Pt(10); nr.bold = True
            nr.font.color.rgb = RGBColor(0xFF,0xFF,0xFF)
            shd2 = OxmlElement('w:shd'); shd2.set(qn('w:fill'),color); shd2.set(qn('w:val'),'clear')
            nr._element.get_or_add_rPr().append(shd2)
            tr = tp.add_run(f"  {item['title']}")
            # Chinese translation
            cn_title = cn_titles[title_idx] if title_idx < len(cn_titles) else ""
            title_idx += 1
            if cn_title:
                ctp = doc.add_paragraph()
                ctp.paragraph_format.space_before = Pt(0); ctp.paragraph_format.space_after = Pt(1)
                ctp.paragraph_format.left_indent = Cm(0.7)
                cr = ctp.add_run(cn_title); cr.font.size = Pt(10)
                cr.font.color.rgb = RGBColor(0x66,0x66,0x66); cr.italic = True; tr.font.size = Pt(13); tr.bold = True
            
            sp = doc.add_paragraph()
            sr2 = sp.add_run(f"Source: {src}"); sr2.font.size = Pt(8)
            sr2.font.color.rgb = RGBColor.from_string(color); sr2.italic = True
            
            url = item.get("url","")
            if url and len(url) > 10:
                up = doc.add_paragraph()
                add_url(up, url[:80], url)
            
            sm = item.get("summary","")
            if sm and len(sm) > 10:
                smp = doc.add_paragraph()
                smr = smp.add_run(f"[Summary] {sm}"); smr.font.size = Pt(10)
                smr.font.color.rgb = RGBColor(0x55,0x55,0x55); smr.italic = True
            
            ft = item.get("full_text","")
            if ft and len(ft) > 50:
                fp = doc.add_paragraph()
                fr = fp.add_run(ft); fr.font.size = Pt(10.5)
            
            dp = doc.add_paragraph()
            dr = dp.add_run("-" * 60); dr.font.size = Pt(6)
            dr.font.color.rgb = RGBColor(0xCC,0xCC,0xCC)
        doc.add_page_break()
    
    fp = doc.add_paragraph(); fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = fp.add_run('China News Briefing'); fr.font.size = Pt(9)
    fr.font.color.rgb = RGBColor(0x99,0x99,0x99); fr.italic = True
    return doc

if __name__ == "__main__":
    in_path = sys.argv[1] if len(sys.argv) > 1 else "china_news_raw.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "China_News_Briefing.docx"
    with open(in_path, encoding='utf-8') as f:
        doc = make_doc(json.load(f))
    doc.save(out_path)
    print(f"Saved: {out_path}", file=sys.stderr)
