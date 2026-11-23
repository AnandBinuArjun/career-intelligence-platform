from __future__ import annotations

import re
from typing import Any

from app.services.matching.taxonomy import (
    extract_certifications,
    extract_skills_from_text,
    extract_soft_skills,
)

_PREFERRED_HEADERS = re.compile(
    r"^(?:preferred|nice to have|desirable|bonus|optional|plus|advantageous)\b",
    re.IGNORECASE,
)
_REQUIRED_HEADERS = re.compile(
    r"^(?:required|requirements|must have|essential|qualifications|minimum qualifications|what you bring|skills required)\b",
    re.IGNORECASE,
)
_RESPONSIBILITY_HEADERS = re.compile(
    r"^(?:responsibilities|what you(?:'ll| will) do|key duties|role overview|the role)\b",
    re.IGNORECASE,
)
_YEARS_RE = re.compile(r"(\d{1,2})\+?\s*(?:to\s*\d{1,2}\s*)?years?\s+(?:of\s+)?experience", re.IGNORECASE)
_DEGREE_RE = re.compile(
    r"\b(bachelor'?s|master'?s|phd|b\.?sc|m\.?sc|degree in [A-Za-z &/]+|computer science|cybersecurity|engineering)\b",
    re.IGNORECASE,
)


def _infer_seniority(title: str, description: str, min_years: int | None) -> str:
    combined = f"{title} {description[:400]}".lower()
    if any(k in combined for k in ("principal", "staff", "director", "head of", "vp ", "vp,")):
        return "Principal / Leadership"
    if any(k in combined for k in ("lead", "senior", "sr.", "sr ")):
        return "Senior"
    if any(k in combined for k in ("junior", "jr.", "graduate", "entry-level", "intern")):
        return "Junior / Entry"
    if min_years is not None:
        if min_years >= 6:
            return "Senior"
        if min_years <= 2:
            return "Junior / Entry"
    return "Mid-level"


def parse_job_description(job_title: str, description: str, company_name: str | None = None) -> dict[str, Any]:
    """Deterministically parse a job description into explicit required/preferred criteria."""
    lines = [ln.strip() for ln in description.splitlines() if ln.strip()]

    required_lines: list[str] = []
    preferred_lines: list[str] = []
    responsibility_lines: list[str] = []

    section = "general"
    for line in lines:
        cleaned = line.rstrip(":").strip()
        if len(cleaned) <= 60:
            if _PREFERRED_HEADERS.search(cleaned):
                section = "preferred"
                continue
            if _REQUIRED_HEADERS.search(cleaned):
                section = "required"
                continue
            if _RESPONSIBILITY_HEADERS.search(cleaned):
                section = "responsibilities"
                continue

        lowered = line.lower()
        if any(marker in lowered for marker in ("nice to have", "preferred", "desirable", "bonus", "plus")) or section == "preferred":
            preferred_lines.append(line.lstrip("-•* ").strip())
        elif section == "responsibilities":
            responsibility_lines.append(line.lstrip("-•* ").strip())
        elif section == "required" or any(
            marker in lowered for marker in ("must have", "required", "essential", "mandatory", "proficient in")
        ):
            required_lines.append(line.lstrip("-•* ").strip())
        else:
            # General lines can still carry explicit technical requirements.
            responsibility_lines.append(line.lstrip("-•* ").strip())

    required_text = "\n".join(required_lines)
    preferred_text = "\n".join(preferred_lines)
    all_skills = extract_skills_from_text(description)
    required_skills = extract_skills_from_text(required_text) if required_text else []
    preferred_skills = [s for s in extract_skills_from_text(preferred_text) if s not in required_skills]

    # If the JD had no explicit requirement section headers, treat non-preferred skills as required.
    if not required_skills:
        required_skills = [s for s in all_skills if s not in preferred_skills]
    else:
        # Any additional skills mentioned in responsibilities not marked preferred go into preferred/context.
        for s in all_skills:
            if s not in required_skills and s not in preferred_skills:
                preferred_skills.append(s)

    years_matches = [int(m.group(1)) for m in _YEARS_RE.finditer(description)]
    min_years = min(years_matches) if years_matches else None

    education_requirements: list[str] = []
    for line in lines:
        if _DEGREE_RE.search(line):
            cleaned_line = line.lstrip("-•* ").strip()
            if cleaned_line not in education_requirements:
                education_requirements.append(cleaned_line[:180])

    certifications = extract_certifications(description)
    soft_skills = extract_soft_skills(description)
    seniority = _infer_seniority(job_title, description, min_years)

    return {
        "job_title": job_title,
        "company_name": company_name,
        "seniority": seniority,
        "min_years_experience": min_years,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "soft_skills": soft_skills,
        "education_requirements": education_requirements[:6],
        "certifications": certifications,
        "responsibilities": responsibility_lines[:15],
        "explicit_requirements": required_lines[:15],
        "preferred_requirements": preferred_lines[:10],
        "extraction_source": "deterministic_v1",
        "inferred_fields": ["seniority"],
    }
