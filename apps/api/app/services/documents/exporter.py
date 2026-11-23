from __future__ import annotations

import io
from typing import Any

from docx import Document as DocxDocument
from docx.shared import Inches, Pt, RGBColor
from fpdf import FPDF


def _latin_safe(text: str) -> str:
    """Keep standard core PDF fonts safe by normalizing common Unicode punctuation."""
    replacements = {
        "\u2013": "-",
        "\u2014": "--",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u00a0": " ",
    }
    out = text
    for src, dst in replacements.items():
        out = out.replace(src, dst)
    return out.encode("latin-1", errors="replace").decode("latin-1")


def export_resume_docx(title: str, content: dict[str, Any]) -> bytes:
    """Export a clean, single-column, watermark-free ATS-safe DOCX resume."""
    doc = DocxDocument()
    for sec in doc.sections:
        sec.top_margin = Inches(0.7)
        sec.bottom_margin = Inches(0.7)
        sec.left_margin = Inches(0.75)
        sec.right_margin = Inches(0.75)

    full_name = str(content.get("full_name") or title)
    heading = doc.add_paragraph()
    run = heading.add_run(full_name)
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0x11, 0x18, 0x27)

    prof_title = content.get("professional_title")
    if prof_title:
        p = doc.add_paragraph()
        r = p.add_run(str(prof_title))
        r.font.size = Pt(11)
        r.font.color.rgb = RGBColor(0x37, 0x41, 0x51)

    contact = content.get("contact") or {}
    contact_parts = [str(v) for k, v in contact.items() if v and k in {"email", "phone", "location", "linkedin"}]
    if contact_parts:
        p = doc.add_paragraph(" | ".join(contact_parts))
        for r in p.runs:
            r.font.size = Pt(9.5)

    def _add_section(name: str) -> None:
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        hr = h.add_run(name.upper())
        hr.bold = True
        hr.font.size = Pt(11)
        hr.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)

    if content.get("summary"):
        _add_section("Professional Summary")
        doc.add_paragraph(str(content["summary"]))

    skills = content.get("skills") or []
    if skills:
        _add_section("Skills")
        doc.add_paragraph(", ".join(str(s) for s in skills))

    experiences = content.get("experiences") or []
    if experiences:
        _add_section("Experience")
        for exp in experiences:
            header_parts = [str(exp.get("job_title") or "")]
            if exp.get("employer"):
                header_parts.append(str(exp["employer"]))
            if exp.get("period"):
                header_parts.append(str(exp["period"]))
            p = doc.add_paragraph()
            r = p.add_run(" | ".join(part for part in header_parts if part))
            r.bold = True
            for bullet in exp.get("bullets") or []:
                doc.add_paragraph(str(bullet), style="List Bullet")

    education = content.get("education") or []
    if education:
        _add_section("Education")
        for edu in education:
            parts = [str(edu.get("qualification") or edu.get("institution") or "")]
            if edu.get("institution") and edu.get("qualification") and edu["institution"] != edu["qualification"]:
                parts.append(str(edu["institution"]))
            if edu.get("period"):
                parts.append(str(edu["period"]))
            doc.add_paragraph(" | ".join(part for part in parts if part))

    certifications = content.get("certifications") or []
    if certifications:
        _add_section("Certifications")
        for cert in certifications:
            name = cert.get("name") if isinstance(cert, dict) else str(cert)
            if name:
                doc.add_paragraph(str(name), style="List Bullet")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def export_resume_pdf(title: str, content: dict[str, Any], template: str = "classic") -> bytes:
    """Export a clean, single-column, selectable-text, watermark-free ATS-safe PDF."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    accent = (29, 78, 216) if template == "modern" else (17, 24, 39)
    body_size = 9.5 if template == "compact" else 10.5

    full_name = _latin_safe(str(content.get("full_name") or title))
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*accent)
    pdf.cell(0, 9, full_name, new_x="LMARGIN", new_y="NEXT")

    if content.get("professional_title"):
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(55, 65, 81)
        pdf.cell(0, 6, _latin_safe(str(content["professional_title"])), new_x="LMARGIN", new_y="NEXT")

    contact = content.get("contact") or {}
    contact_parts = [str(v) for k, v in contact.items() if v and k in {"email", "phone", "location", "linkedin"}]
    if contact_parts:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(75, 85, 99)
        pdf.cell(0, 5, _latin_safe(" | ".join(contact_parts)), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    def _section_heading(label: str) -> None:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*accent)
        pdf.cell(0, 6, _latin_safe(label.upper()), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(209, 213, 219)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(2)
        pdf.set_text_color(17, 24, 39)
        pdf.set_font("Helvetica", "", body_size)

    if content.get("summary"):
        _section_heading("Professional Summary")
        pdf.multi_cell(pdf.epw, 5, _latin_safe(str(content["summary"])), new_x="LMARGIN", new_y="NEXT")

    skills = content.get("skills") or []
    if skills:
        _section_heading("Skills")
        pdf.multi_cell(pdf.epw, 5, _latin_safe(", ".join(str(s) for s in skills)), new_x="LMARGIN", new_y="NEXT")

    experiences = content.get("experiences") or []
    if experiences:
        _section_heading("Experience")
        for exp in experiences:
            header_parts = [str(exp.get("job_title") or "")]
            if exp.get("employer"):
                header_parts.append(str(exp["employer"]))
            if exp.get("period"):
                header_parts.append(str(exp["period"]))
            pdf.set_font("Helvetica", "B", body_size)
            pdf.multi_cell(pdf.epw, 5, _latin_safe(" | ".join(p for p in header_parts if p)), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", body_size)
            for bullet in exp.get("bullets") or []:
                pdf.multi_cell(pdf.epw, 5, _latin_safe(f"- {bullet}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    education = content.get("education") or []
    if education:
        _section_heading("Education")
        for edu in education:
            parts = [str(edu.get("qualification") or edu.get("institution") or "")]
            if edu.get("institution") and edu.get("qualification") and edu["institution"] != edu["qualification"]:
                parts.append(str(edu["institution"]))
            if edu.get("period"):
                parts.append(str(edu["period"]))
            pdf.multi_cell(pdf.epw, 5, _latin_safe(" | ".join(p for p in parts if p)), new_x="LMARGIN", new_y="NEXT")

    certifications = content.get("certifications") or []
    if certifications:
        _section_heading("Certifications")
        for cert in certifications:
            name = cert.get("name") if isinstance(cert, dict) else str(cert)
            if name:
                pdf.multi_cell(pdf.epw, 5, _latin_safe(f"- {name}"), new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


def export_cover_letter_docx(title: str, content: str) -> bytes:
    doc = DocxDocument()
    for sec in doc.sections:
        sec.top_margin = Inches(0.85)
        sec.bottom_margin = Inches(0.85)
        sec.left_margin = Inches(0.85)
        sec.right_margin = Inches(0.85)

    h = doc.add_paragraph()
    r = h.add_run(title)
    r.bold = True
    r.font.size = Pt(14)

    for para in content.split("\n\n"):
        if para.strip():
            doc.add_paragraph(para.strip())

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def export_cover_letter_pdf(title: str, content: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, _latin_safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    for para in content.split("\n\n"):
        if para.strip():
            pdf.multi_cell(pdf.epw, 6, _latin_safe(para.strip()), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
    return bytes(pdf.output())
