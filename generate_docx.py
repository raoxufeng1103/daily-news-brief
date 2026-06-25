#!/usr/bin/env python3
"""Generate beautiful Word doc from China news JSON"""
import json, sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# Source color mapping
SRC_COLORS = {
    "BBC": RGBColor(0xBB, 0x19, 0x1F),
    "Reuters": RGBColor(0xFF, 0x80, 0x00),
    "Bloomberg": RGBColor(0x00, 0x53, 0xA0),
    "AP": RGBColor(0x00, 0x00, 0x00),
    "AFP": RGBColor(0x00, 0x3D, 0x7A),
    "Nikkei Asia": RGBColor(0x8B, 0x00, 0x00),
    "APP (Pakistan)": RGBColor(0x01, 0x4B, 0x1A),
    "IRNA (Iran)": RGBColor(0x23, 0x9B, 0x56),
    "Tanjug (Serbia)": RGBColor(0x00, 0x43, 0x7C),
    "SAnews (S.Africa)": RGBColor(0x00, 0x66, 0x33),
}
SRC_NAMES = {
    "BBC": "BBC News (UK)",
    "Reuters": "Reuters (UK)",
    "Bloomberg": "Bloomberg (US)",
    "AP": "Associated Press (US)",
    "AFP": "Agence France-Presse (France)",
    "Nikkei Asia": "Nikkei Asia (Japan)",
    "APP (Pakistan)": "Assoc. Press of Pakistan",
    "IRNA (Iran)": "IRNA (Iran)",
    "Tanjug (Serbia)": "Tanjug (Serbia)",
    "SAnews (S.Africa)": "SAnews (South Africa)",
}

def set_cell_shading(cell, color):
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color)
    shading.set(qn('w:val'), 'clear')
    cell._tc.get_or_add_tcPr().append(shading)

def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    color = OxmlElement('w:color')
    color.set(qn('w:val'), '0563C1')
    rPr.append(color)
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), '20')
    rPr.append(sz)
    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return paragraph

def from_cn_news(data):
    doc = Document()
    
    # Page setup
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    
    # ===== Title Page =====
    for _ in range(4):
        doc.add_paragraph("")
    
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("China News Briefing")
    run.font.size = Pt(32)
    run.font.color.rgb = RGBColor(0xBB, 0x19, 0x1F)
    run.bold = True
    run.font.name = 'Arial'
    
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run("涉华新闻日报")
    run.font.size = Pt(24)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    run.font.name = 'SimSun'
    
    doc.add_paragraph("")
    
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info.add_run(data.get("generated_at", ""))
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    
    doc.add_paragraph("")
    total = doc.add_paragraph()
    total.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = total.add_run(f"Total: {data.get('total', 0)} China-related articles")
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0xBB, 0x19, 0x1F)
    run.bold = True
    
    # Sources
    sources = doc.add_paragraph()
    sources.alignment = WD_ALIGN_PARAGRAPH.CENTER
    src_text = "Sources: " + " | ".join(SRC_NAMES.values())
    run = sources.add_run(src_text)
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    
    doc.add_page_break()
    
    # ===== Table of Contents =====
    toc_title = doc.add_paragraph()
    run = toc_title.add_run("CONTENTS  /  目录")
    run.font.size = Pt(20)
    run.bold = True
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    
    doc.add_paragraph("")
    
    articles = data.get("articles", [])
    
    # Group by source
    groups = {}
    for a in articles:
        s = a.get("source", "Other")
        if s not in groups: groups[s] = []
        groups[s].append(a)
    
    # TOC entries
    for idx, (src, items) in enumerate(groups.items(), 1):
        p = doc.add_paragraph()
        run = p.add_run(f"[{idx}]  {SRC_NAMES.get(src, src)}  ({len(items)} articles)")
        run.font.size = Pt(12)
        run.font.color.rgb = SRC_COLORS.get(src, RGBColor(0,0,0))
        run.bold = True
    
    doc.add_page_break()
    
    # ===== Articles =====
    global_idx = 0
    for src, items in groups.items():
        color = SRC_COLORS.get(src, RGBColor(0,0,0))
        full_name = SRC_NAMES.get(src, src)
        
        # Section header
        section_h = doc.add_paragraph()
        section_h.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Colored bar
        run = section_h.add_run(f"  {full_name}  ")
        run.font.size = Pt(18)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.name = 'Arial'
        # Add shading via run properties
        rPr = run._element.get_or_add_rPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:fill'), f'{color:06X}' if hasattr(color, '__str__') else 'BB191F')
        shd.set(qn('w:val'), 'clear')
        rPr.append(shd)
        
        # Underline separator
        sep = doc.add_paragraph()
        sep_run = sep.add_run("_" * 80)
        sep_run.font.color.rgb = color
        sep_run.font.size = Pt(8)
        
        for item in items:
            global_idx += 1
            
            # Number + Title
            title_p = doc.add_paragraph()
            
            # Number badge
            num_run = title_p.add_run(f" #{global_idx} ")
            num_run.font.size = Pt(10)
            num_run.bold = True
            num_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            num_rPr = num_run._element.get_or_add_rPr()
            num_shd = OxmlElement('w:shd')
            num_shd.set(qn('w:fill'), f'{color:06X}')
            num_shd.set(qn('w:val'), 'clear')
            num_rPr.append(num_shd)
            
            # Title text
            title_text = item.get("title", "Untitled")
            t_run = title_p.add_run(f"  {title_text}")
            t_run.font.size = Pt(14)
            t_run.bold = True
            t_run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
            
            # Source line
            src_line = doc.add_paragraph()
            src_run = src_line.add_run(f"Source: {src}")
            src_run.font.size = Pt(8)
            src_run.font.color.rgb = color
            src_run.italic = True
            
            # URL
            url = item.get("url", "")
            if url and len(url) > 10:
                url_p = doc.add_paragraph()
                add_hyperlink(url_p, url[:80] + ("..." if len(url)>80 else ""), url)
            
            # Summary
            summary = item.get("summary", "")
            if summary and len(summary) > 10:
                sm_p = doc.add_paragraph()
                sm_run = sm_p.add_run(f"[Summary] {summary}")
                sm_run.font.size = Pt(10)
                sm_run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
                sm_run.italic = True
            
            # Full text
            ft = item.get("full_text", "")
            if ft and len(ft) > 20:
                ft_p = doc.add_paragraph()
                ft_run = ft_p.add_run(ft[:1800])
                ft_run.font.size = Pt(10.5)
                ft_run.font.name = 'Calibri'
            
            # Separator
            div = doc.add_paragraph()
            div_run = div.add_run("─" * 70)
            div_run.font.size = Pt(6)
            div_run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        
        doc.add_page_break()
    
    # ===== Footer =====
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("China News Briefing  ·  涉华新闻日报")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    run.italic = True
    
    return doc

if __name__ == "__main__":
    data = json.load(sys.stdin)
    doc = from_cn_news(data)
    out_path = sys.argv[1] if len(sys.argv) > 1 else "China_News_Briefing.docx"
    doc.save(out_path)
    print(f"Saved: {out_path}", file=sys.stderr)
