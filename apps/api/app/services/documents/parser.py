from __future__ import annotations

import io
import re
from typing import Any

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.services.matching.taxonomy import extract_skills_from_text

MAX_PDF_PAGES = 15

_SECTION_ALIASES: dict[str, list[str]] = {
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "about",
        "about me",
        "executive summary",
        "objective",
        "career summary",
    ],
    "experience": [
        "experience",
        "work experience",
        "employment history",
        "professional experience",
        "career history",
        "relevant experience",
    ],
    "education": [
        "education",
        "academic background",
        "qualifications",
        "academic qualifications",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "technologies",
        "tools & technologies",
        "key skills",
    ],
    "certifications": [
        "certifications",
        "licenses & certifications",
        "licences & certifications",
        "certificates",
        "accreditations",
    ],
    "projects": [
        "projects",
        "selected projects",
        "key projects",
    ],
}

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-()]{7,}\d)")
_DATE_RANGE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})\s*[-–—to]+\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}|Present|Current)",
    re.IGNORECASE,
)


def _match_heading(line: str) -> str | None:
    cleaned = re.sub(r"[:\-_|]+$", "", line.strip()).strip().lower()
    if not cleaned or len(cleaned) > 48:
        return None
    for canonical, aliases in _SECTION_ALIASES.items():
        if cleaned in aliases:
            return canonical
    return None


def _extract_raw_text(data: bytes, content_type: str) -> tuple[str, dict[str, Any]]:
    diagnostics: dict[str, Any] = {
        "page_count": 1,
        "has_tables": False,
        "has_multi_column_risk": False,
        "has_headers_footers": False,
        "text_extractable": True,
        "warnings": [],
    }

    if content_type == "text/plain":
        text = data.decode("utf-8", errors="replace")
        return text, diagnostics

    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        page_count = len(reader.pages)
        diagnostics["page_count"] = page_count
        if page_count > MAX_PDF_PAGES:
            diagnostics["warnings"].append(
                f"Document has {page_count} pages; only the first {MAX_PDF_PAGES} pages were parsed."
            )
        pages_text: list[str] = []
        for idx, page in enumerate(reader.pages[:MAX_PDF_PAGES]):
            extracted = page.extract_text() or ""
            pages_text.append(extracted)
            # Heuristic for multi-column layouts: many lines containing wide internal spacing
            wide_gap_lines = sum(1 for ln in extracted.splitlines() if re.search(r"\S\s{6,}\S", ln))
            if wide_gap_lines >= 4:
                diagnostics["has_multi_column_risk"] = True
        full_text = "\n".join(pages_text).strip()
        if len(full_text) < 40:
            diagnostics["text_extractable"] = False
            diagnostics["warnings"].append(
                "Very little selectable text was extracted. The PDF may be scanned or image-based; OCR or a text-based PDF is recommended."
            )
        if diagnostics["has_multi_column_risk"]:
            diagnostics["warnings"].append(
                "Detected wide horizontal spacing consistent with multi-column layouts or tables, which some ATS parsers read out of order."
            )
        return full_text, diagnostics

    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = DocxDocument(io.BytesIO(data))
        lines: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                lines.append(para.text.strip())
        if doc.tables:
            diagnostics["has_tables"] = True
            diagnostics["warnings"].append(
                "Document contains tables. Single-column layouts without layout tables are more reliable across ATS parsers."
            )
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        lines.append(" | ".join(row_cells))
        for sec in doc.sections:
            if (sec.header and any(p.text.strip() for p in sec.header.paragraphs)) or (
                sec.footer and any(p.text.strip() for p in sec.footer.paragraphs)
            ):
                diagnostics["has_headers_footers"] = True
        if diagnostics["has_headers_footers"]:
            diagnostics["warnings"].append(
                "Text found in Word headers/footers. Avoid putting critical contact info exclusively in headers or footers."
            )
        return "\n".join(lines), diagnostics

    raise ValueError(f"Unsupported content type for parsing: {content_type}")


def parse_resume_text(raw_text: str, diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Parse plain resume text into structured sections, source spans, and ATS diagnostics."""
    diag = dict(diagnostics or {})
    diag.setdefault("page_count", 1)
    diag.setdefault("has_tables", False)
    diag.setdefault("has_multi_column_risk", False)
    diag.setdefault("has_headers_footers", False)
    diag.setdefault("text_extractable", len(raw_text.strip()) >= 40)
    diag.setdefault("warnings", [])

    lines = [ln.rstrip() for ln in raw_text.splitlines()]
    non_empty = [ln.strip() for ln in lines if ln.strip()]

    # Partition lines into sections while tracking line numbers (source spans).
    sections: dict[str, list[dict[str, Any]]] = {"header": []}
    current_section = "header"
    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        heading = _match_heading(stripped)
        if heading is not None:
            current_section = heading
            sections.setdefault(current_section, [])
            continue
        sections.setdefault(current_section, []).append({"line": idx, "text": stripped})

    # Contact & identity extraction from header block
    header_text = "\n".join(item["text"] for item in sections.get("header", []))
    emails = _EMAIL_RE.findall(header_text or raw_text[:600])
    phones = _PHONE_RE.findall(header_text or raw_text[:600])
    full_name = ""
    professional_title = ""
    for item in sections.get("header", []):
        t = item["text"]
        if not full_name and "@" not in t and len(t.split()) <= 5 and not re.search(r"\d{4}", t):
            full_name = t
            continue
        if full_name and not professional_title and "@" not in t and len(t) <= 90:
            professional_title = t
            break

    # Summary
    summary_items = sections.get("summary", [])
    summary_text = " ".join(item["text"] for item in summary_items).strip()

    # Experience entries
    experiences: list[dict[str, Any]] = []
    current_exp: dict[str, Any] | None = None
    for item in sections.get("experience", []):
        txt = item["text"]
        is_bullet = txt.startswith(("-", "•", "*", "▪", "–"))
        date_match = _DATE_RANGE_RE.search(txt)
        if not is_bullet and (date_match or " | " in txt or " at " in txt.lower() or " — " in txt):
            if current_exp is not None:
                experiences.append(current_exp)
            period = date_match.group(0) if date_match else ""
            role_header = _DATE_RANGE_RE.sub("", txt).strip(" |-–—")
            parts = re.split(r"\s+\|\s+|\s+—\s+|\s+at\s+", role_header, maxsplit=1)
            job_title = parts[0].strip() if parts else role_header
            employer = parts[1].strip() if len(parts) > 1 else ""
            current_exp = {
                "job_title": job_title or txt,
                "employer": employer,
                "period": period,
                "bullets": [],
                "source_span": {"start_line": item["line"], "end_line": item["line"]},
            }
        else:
            cleaned_bullet = txt.lstrip("-•*▪– ").strip()
            if current_exp is None:
                current_exp = {
                    "job_title": cleaned_bullet[:100],
                    "employer": "",
                    "period": "",
                    "bullets": [cleaned_bullet],
                    "source_span": {"start_line": item["line"], "end_line": item["line"]},
                }
            else:
                current_exp["bullets"].append(cleaned_bullet)
                current_exp["source_span"]["end_line"] = item["line"]
    if current_exp is not None:
        experiences.append(current_exp)

    # Education entries
    education: list[dict[str, Any]] = []
    for item in sections.get("education", []):
        txt = item["text"].lstrip("-•* ").strip()
        date_match = _DATE_RANGE_RE.search(txt)
        education.append(
            {
                "institution": txt,
                "qualification": txt,
                "period": date_match.group(0) if date_match else "",
                "source_span": {"line": item["line"], "text": txt},
            }
        )

    # Skills: combine explicit skills section + normalized taxonomy matches across full CV
    skills_section_text = "\n".join(item["text"] for item in sections.get("skills", []))
    explicit_tokens: list[str] = []
    for raw_item in re.split(r"[,|•;\n]+", skills_section_text):
        cleaned = re.sub(r"^[A-Za-z &/]+:\s*", "", raw_item.strip()).strip("-•* ")
        if 1 < len(cleaned) <= 50:
            explicit_tokens.append(cleaned)

    taxonomy_matches = extract_skills_from_text(raw_text)
    merged_skills: list[str] = []
    seen_lower: set[str] = set()
    for skill_name in [*taxonomy_matches, *explicit_tokens]:
        key = skill_name.lower()
        if key not in seen_lower:
            seen_lower.add(key)
            merged_skills.append(skill_name)

    # Certifications
    certifications = [
        {"name": item["text"].lstrip("-•* ").strip(), "source_span": {"line": item["line"]}}
        for item in sections.get("certifications", [])
    ]

    # Extraction confidence calculation
    detected_sections = [k for k in ("summary", "experience", "education", "skills", "certifications") if sections.get(k)]
    confidence = 0.25
    if diag["text_extractable"]:
        confidence += 0.30
    confidence += min(len(detected_sections) * 0.11, 0.44)
    if diag["has_tables"] or diag["has_multi_column_risk"]:
        confidence = max(0.2, confidence - 0.10)
    confidence = round(min(confidence, 0.99), 2)

    # Readability score (0-100) for ATS formatting/parsing dimension
    readability_score = 100
    if not diag["text_extractable"]:
        readability_score -= 60
    if diag["has_tables"]:
        readability_score -= 15
    if diag["has_multi_column_risk"]:
        readability_score -= 15
    if diag["has_headers_footers"]:
        readability_score -= 5
    if len(detected_sections) < 3:
        readability_score -= 10
    if diag["page_count"] > 3:
        readability_score -= 5
    diag["readability_score"] = max(0, readability_score)
    diag["detected_sections"] = detected_sections
    diag["word_count"] = len(raw_text.split())
    diag["line_count"] = len(non_empty)

    return {
        "full_name": full_name,
        "professional_title": professional_title,
        "contact": {
            "email": emails[0] if emails else None,
            "phone": phones[0] if phones else None,
        },
        "summary": summary_text,
        "experiences": experiences,
        "education": education,
        "skills": merged_skills,
        "certifications": certifications,
        "raw_text": raw_text,
        "extraction_confidence": confidence,
        "diagnostics": diag,
    }


def parse_resume_bytes(data: bytes, content_type: str) -> dict[str, Any]:
    raw_text, diagnostics = _extract_raw_text(data, content_type)
    return parse_resume_text(raw_text, diagnostics)
