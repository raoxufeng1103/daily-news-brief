#!/usr/bin/env python3
"""Generate bilingual China News Briefing Word doc with translations"""
import json, os, re, sys, time, urllib.request, ssl
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC_META = {
    "BBC":("C41E3A","BBC News"),"Reuters":("FF8000","Reuters"),
    "Bloomberg":("0053A0","Bloomberg"),"AP":("1A1A1A","Associated Press"),
    "AFP":("003D7A","AFP"),"Nikkei Asia":("8B0000","Nikkei Asia"),
    "APP (Pakistan)":("014B1A","APP Pakistan"),"IRNA (Iran)":("239B56","IRNA Iran"),
    "Tanjug (Serbia)":("00437C","Tanjug Serbia"),"SAnews (S.Africa)":("006633","SAnews"),
}

def translate(texts):
    key = os.environ.get("GLM_API_KEY","")
    if not key or key == "***":
        return [""]*len(texts)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    results = []
    for i in range(0, len(texts), 25):
        chunk = texts[i:i+25]
        prompt = "Translate these news headlines to Chinese. One per line, no numbering:\n"
        prompt += "\n".join(f"- {t}" for t in chunk)
        try:
            payload = json.dumps({"model":"glm-4.7-flash","messages":[{"role":"user","content":prompt}],"max_tokens":4096}).encode()
            req = urllib.request.Request("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                data=payload, headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            resp = json.loads(urllib.request.urlopen(req, timeout=60, context=ctx).read())
            text = resp["choices"][0]["message"]["content"].strip()
            lines = [l.strip().lstrip("- ") for l in text.split("\n") if l.strip()]
            results.extend(lines[:len(chunk)])
        except:
            results.extend([""]*len(chunk))
        time.sleep(0.5)
    return results

def build(data):
    doc = Document()
    s = doc.sections[0]
    s.page_width = Cm(21); s.page_height = Cm(29.7)
    s.top_margin = Cm(2.0); s.bottom_margin = Cm(1.5)
    s.left_margin = Cm(2.2); s.right_margin = Cm(2.2)
    
    # Cover
    for _ in range(5): doc.add_paragraph("")
    bar = doc.add_paragraph(); bar.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = bar.add_run(" "*120); r.font.size = Pt(3)
    shd = OxmlElement("w:shd"); shd.set(qn("w:fill"),"C41E3A"); shd.set(qn("w:val"),"clear")
    r._element.get_or_add_rPr().append(shd)
    doc.add_paragraph("")
    
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("涉 华 新 闻 日 报"); r.font.size = Pt(36); r.bold = True
    r.font.color.rgb = RGBColor(0xC4,0x1E,0x3A)
    doc.add_paragraph("")
    t2 = doc.add_paragraph(); t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = t2.add_run("CHINA NEWS BRIEFING"); r2.font.size = Pt(20)
    r2.font.color.rgb = RGBColor(0x33,0x33,0x33)
    doc.add_paragraph("")
    b2 = doc.add_paragraph(); b2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = b2.add_run(" "*120); r.font.size = Pt(3)
    shd = OxmlElement("w:shd"); shd.set(qn("w:fill"),"C41E3A"); shd.set(qn("w:val"),"clear")
    r._element.get_or_add_rPr().append(shd)
    for _ in range(4): doc.add_paragraph("")
    
    dp = doc.add_paragraph(); dp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dr = dp.add_run(f"  {data.get('generated_at','')[:10]}  "); dr.font.size = Pt(14)
    dr.font.color.rgb = RGBColor(0x66,0x66,0x66)
    doc.add_paragraph("")
    
    arts = data["articles"]
    ft = sum(1 for a in arts if a.get("full_text") and len(a["full_text"])>80)
    sp = doc.add_paragraph(); sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sp.add_run(f" {len(arts)} articles  ·  10 sources  ·  {ft} with full text")
    r.font.size = Pt(11); r.font.color.rgb = RGBColor(0x88,0x88,0x88)
    doc.add_page_break()
    
    groups = {}
    for a in arts: groups.setdefault(a["source"],[]).append(a)
    
    # Translate titles
    print("Translating titles to Chinese...", flush=True)
    all_titles = [item["title"] for src,items in groups.items() for item in items]
    cn = translate(all_titles)
    idx = 0
    cn_map = {}
    for src,items in groups.items():
        for item in items:
            cn_map[id(item)] = cn[idx] if idx < len(cn) else ""
            idx += 1
    
    gidx = 0
    for src,items in groups.items():
        color,full = SRC_META.get(src,("333333",src))
        bar = doc.add_paragraph(); bar.paragraph_format.space_before = Pt(0); bar.paragraph_format.space_after = Pt(0)
        r = bar.add_run(" "*90); r.font.size = Pt(4)
        shd = OxmlElement("w:shd"); shd.set(qn("w:fill"),color); shd.set(qn("w:val"),"clear")
        r._element.get_or_add_rPr().append(shd)
        hp = doc.add_paragraph()
        hp.paragraph_format.space_before = Pt(6); hp.paragraph_format.space_after = Pt(2)
        r = hp.add_run(f" {full}  |  {len(items)} articles")
        r.font.size = Pt(16); r.bold = True; r.font.color.rgb = RGBColor.from_string(color)
        
        for item in items:
            gidx += 1
            cn_title = cn_map.get(id(item),"")
            
            tp = doc.add_paragraph()
            tp.paragraph_format.space_before = Pt(10); tp.paragraph_format.space_after = Pt(1)
            nr = tp.add_run(f" {gidx:03d} "); nr.font.size = Pt(8); nr.bold = True
            nr.font.color.rgb = RGBColor(0xFF,0xFF,0xFF)
            shd = OxmlElement("w:shd"); shd.set(qn("w:fill"),color); shd.set(qn("w:val"),"clear")
            nr._element.get_or_add_rPr().append(shd)
            tr = tp.add_run(f"  {item['title']}"); tr.font.size = Pt(11)
            tr.bold = True; tr.font.color.rgb = RGBColor(0x1A,0x1A,0x1A)
            
            if cn_title:
                ct = doc.add_paragraph()
                ct.paragraph_format.space_before = Pt(0); ct.paragraph_format.space_after = Pt(2)
                ct.paragraph_format.left_indent = Cm(0.7)
                cr = ct.add_run(cn_title); cr.font.size = Pt(10)
                cr.font.color.rgb = RGBColor(0x66,0x66,0x66); cr.italic = True
            
            sm = item.get("summary","")
            if sm and len(sm) > 10:
                sp = doc.add_paragraph()
                sp.paragraph_format.space_before = Pt(2); sp.paragraph_format.space_after = Pt(1)
                sp.paragraph_format.left_indent = Cm(0.7)
                sr = sp.add_run(sm); sr.font.size = Pt(9)
                sr.font.color.rgb = RGBColor(0x44,0x44,0x44); sr.italic = True
            
            ft = item.get("full_text","")
            if ft and len(ft) > 80:
                fp = doc.add_paragraph()
                fp.paragraph_format.space_before = Pt(3)
                fp.paragraph_format.left_indent = Cm(0.7)
                lb = fp.add_run("Full Text: "); lb.font.size = Pt(8)
                lb.bold = True; lb.font.color.rgb = RGBColor(0x88,0x88,0x88)
                fr = fp.add_run(ft[:1500]); fr.font.size = Pt(9)
                fr.font.color.rgb = RGBColor(0x33,0x33,0x33)
            
            dp = doc.add_paragraph()
            dp.paragraph_format.space_before = Pt(4); dp.paragraph_format.space_after = Pt(0)
            dr = dp.add_run("." * 3); dr.font.size = Pt(8)
            dr.font.color.rgb = RGBColor(0xBB,0xBB,0xBB); dr.italic = True
        
        doc.add_page_break()
    
    return doc

if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv)>1 else "china_news_raw.json"
    out = sys.argv[2] if len(sys.argv)>2 else "China_News_Briefing.docx"
    with open(inp,"r",encoding="utf-8") as f:
        data = json.load(f)
    print(f"Building doc ({data['total']} articles)...", flush=True)
    doc = build(data)
    doc.save(out)
    print(f"Saved: {out}", flush=True)
