from __future__ import annotations

import re
from typing import Any

from app.services.matching.taxonomy import (
    extract_certifications,
    extract_skills_from_text,
    normalize_skill,
)

SCORING_VERSION = "v1.0"

METHODOLOGY_NOTE = (
    "Platform compatibility estimate (scoring v1.0). Calculated deterministically from document "
    "readability, explicit requirement evidence, skills alignment, experience overlap, education/"
    "certifications, and measurable achievement clarity. This is not a proprietary ATS vendor score "
    "and does not guarantee interview selection."
)

DEFAULT_WEIGHTS: dict[str, float] = {
    "skills_relevance": 0.30,
    "experience_relevance": 0.25,
    "keyword_coverage": 0.15,
    "education_certification": 0.10,
    "achievement_evidence": 0.10,
    "document_readability": 0.10,
}

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "will", "have", "into",
    "about", "more", "than", "such", "their", "they", "been", "were", "also", "other",
    "work", "working", "team", "role", "ability", "strong", "using", "across", "within",
    "experience", "skills", "years", "including", "ensure", "support", "build", "building",
}

_METRIC_RE = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*%|\$\s*\d[\d,.]*[kmb]?|\£\s*\d[\d,.]*[kmb]?|\b\d+(?:\.\d+)?x\b|\b\d{2,}\+?\s+(?:users|clients|engineers|requests|endpoints|incidents|systems|servers|customers|projects|hours|days)\b)",
    re.IGNORECASE,
)

_ACTION_VERBS = {
    "architected", "automated", "built", "created", "delivered", "designed", "developed",
    "engineered", "implemented", "improved", "increased", "launched", "led", "migrated",
    "mitigated", "optimized", "reduced", "remediated", "resolved", "scaled", "secured",
    "streamlined",
}


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z0-9+#.-]{3,}", text.lower())
    return {t for t in tokens if t not in _STOPWORDS and not t.isdigit()}


def _flatten_resume_content(resume_content: dict[str, Any], profile_context: dict[str, Any] | None = None) -> tuple[str, list[dict[str, str]]]:
    """Flatten structured resume content into full text plus traceable evidence snippets."""
    snippets: list[dict[str, str]] = []
    parts: list[str] = []

    summary = str(resume_content.get("summary") or "").strip()
    if summary:
        parts.append(summary)
        snippets.append({"source": "resume.summary", "text": summary})

    for idx, exp in enumerate(resume_content.get("experiences") or []):
        if not isinstance(exp, dict):
            continue
        header = " ".join(str(exp.get(k) or "") for k in ("job_title", "employer", "period")).strip()
        if header:
            parts.append(header)
            snippets.append({"source": f"resume.experience[{idx}].header", "text": header})
        if exp.get("description"):
            desc = str(exp["description"]).strip()
            parts.append(desc)
            snippets.append({"source": f"resume.experience[{idx}].description", "text": desc})
        for b_idx, bullet in enumerate(exp.get("bullets") or exp.get("achievements") or []):
            b_str = str(bullet).strip()
            if b_str:
                parts.append(b_str)
                snippets.append({"source": f"resume.experience[{idx}].bullet[{b_idx}]", "text": b_str})

    for idx, edu in enumerate(resume_content.get("education") or []):
        if isinstance(edu, dict):
            text = " ".join(
                str(edu.get(k) or "") for k in ("qualification", "field_of_study", "institution", "period")
            ).strip()
            if text:
                parts.append(text)
                snippets.append({"source": f"resume.education[{idx}]", "text": text})
        elif isinstance(edu, str) and edu.strip():
            parts.append(edu.strip())
            snippets.append({"source": f"resume.education[{idx}]", "text": edu.strip()})

    skills = resume_content.get("skills") or []
    if skills:
        skill_text = ", ".join(
            str(s.get("name") if isinstance(s, dict) else s) for s in skills
        )
        parts.append(skill_text)
        snippets.append({"source": "resume.skills", "text": skill_text})

    for idx, cert in enumerate(resume_content.get("certifications") or []):
        name = cert.get("name") if isinstance(cert, dict) else str(cert)
        if name:
            parts.append(str(name))
            snippets.append({"source": f"resume.certifications[{idx}]", "text": str(name)})

    raw_text = str(resume_content.get("raw_text") or "").strip()
    if raw_text and not parts:
        parts.append(raw_text)
        snippets.append({"source": "resume.raw_text", "text": raw_text[:600]})

    # Optionally include verified profile facts that aren't in the draft yet as separate context.
    if profile_context:
        for p_skill in profile_context.get("skills") or []:
            if isinstance(p_skill, str) and p_skill.strip():
                snippets.append({"source": "profile.verified_skills", "text": p_skill.strip()})

    return "\n".join(parts), snippets


def _find_evidence_snippet(term: str, snippets: list[dict[str, str]]) -> dict[str, str] | None:
    lowered = term.lower()
    for snip in snippets:
        if lowered in snip["text"].lower():
            return {"source": snip["source"], "excerpt": snip["text"][:220]}
    # Check token-level partial overlap (possible match, never silent direct match)
    term_tokens = _tokenize(term)
    if not term_tokens:
        return None
    for snip in snippets:
        snip_tokens = _tokenize(snip["text"])
        overlap = term_tokens & snip_tokens
        if overlap and len(overlap) / len(term_tokens) >= 0.5:
            return {"source": snip["source"], "excerpt": snip["text"][:220]}
    return None


def _normalize_weights(custom_weights: dict[str, float] | None) -> dict[str, float]:
    weights = dict(DEFAULT_WEIGHTS)
    if custom_weights:
        for key in DEFAULT_WEIGHTS:
            if key in custom_weights and custom_weights[key] is not None:
                weights[key] = max(0.0, float(custom_weights[key]))
    total = sum(weights.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: round(v / total, 4) for k, v in weights.items()}


def evaluate_compatibility(
    resume_content: dict[str, Any],
    job_requirements: dict[str, Any],
    job_description_text: str,
    *,
    weights: dict[str, float] | None = None,
    profile_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic, reproducible 8-dimension compatibility engine with evidence traceability."""
    norm_weights = _normalize_weights(weights)
    resume_text, snippets = _flatten_resume_content(resume_content, profile_context)
    resume_tokens = _tokenize(resume_text)

    # Canonical skills present in the resume
    explicit_resume_skills = {
        normalize_skill(str(s.get("name") if isinstance(s, dict) else s))
        for s in (resume_content.get("skills") or [])
        if str(s.get("name") if isinstance(s, dict) else s).strip()
    }
    extracted_resume_skills = set(extract_skills_from_text(resume_text))
    resume_skills = {s for s in (explicit_resume_skills | extracted_resume_skills) if s}
    resume_skills_lower = {s.lower() for s in resume_skills}

    required_skills = [normalize_skill(s) for s in (job_requirements.get("required_skills") or []) if s]
    preferred_skills = [normalize_skill(s) for s in (job_requirements.get("preferred_skills") or []) if s]
    req_certs = list(job_requirements.get("certifications") or [])
    req_edu = list(job_requirements.get("education_requirements") or [])
    responsibilities = list(job_requirements.get("responsibilities") or [])

    # 1. Skills Alignment & Requirement-by-Requirement Matrix
    requirement_matrix: list[dict[str, Any]] = []
    matched_required = 0
    possible_required = 0
    missing_required: list[str] = []

    for skill in required_skills:
        ev = _find_evidence_snippet(skill, snippets)
        if skill.lower() in resume_skills_lower:
            matched_required += 1
            requirement_matrix.append(
                {
                    "requirement": skill,
                    "priority": "required",
                    "match_state": "direct_match",
                    "evidence": ev or {"source": "resume.skills", "excerpt": skill},
                    "note": "Direct skill evidence found in resume.",
                }
            )
        elif ev is not None:
            possible_required += 1
            requirement_matrix.append(
                {
                    "requirement": skill,
                    "priority": "required",
                    "match_state": "possible_match",
                    "evidence": ev,
                    "note": "Related phrasing found; clarify explicitly only if you hold this skill.",
                }
            )
        else:
            missing_required.append(skill)
            requirement_matrix.append(
                {
                    "requirement": skill,
                    "priority": "required",
                    "match_state": "missing_evidence",
                    "evidence": None,
                    "note": "No evidence found in this resume version (missing evidence, not necessarily missing capability).",
                }
            )

    matched_preferred = 0
    missing_preferred: list[str] = []
    for skill in preferred_skills:
        ev = _find_evidence_snippet(skill, snippets)
        if skill.lower() in resume_skills_lower:
            matched_preferred += 1
            requirement_matrix.append(
                {
                    "requirement": skill,
                    "priority": "preferred",
                    "match_state": "direct_match",
                    "evidence": ev or {"source": "resume.skills", "excerpt": skill},
                    "note": "Direct preferred-skill evidence found.",
                }
            )
        elif ev is not None:
            matched_preferred += 0.5  # type: ignore[assignment]
            requirement_matrix.append(
                {
                    "requirement": skill,
                    "priority": "preferred",
                    "match_state": "possible_match",
                    "evidence": ev,
                    "note": "Partial evidence found.",
                }
            )
        else:
            missing_preferred.append(skill)
            requirement_matrix.append(
                {
                    "requirement": skill,
                    "priority": "preferred",
                    "match_state": "missing_evidence",
                    "evidence": None,
                    "note": "Preferred skill not evidenced in resume.",
                }
            )

    if required_skills:
        req_skill_ratio = (matched_required + 0.5 * possible_required) / len(required_skills)
    else:
        req_skill_ratio = 0.75
    pref_skill_ratio = (matched_preferred / len(preferred_skills)) if preferred_skills else req_skill_ratio
    skills_score = round((0.75 * req_skill_ratio + 0.25 * pref_skill_ratio) * 100, 1)

    # 2. Experience Relevance (responsibility overlap against experience bullets)
    exp_snippets = [s for s in snippets if s["source"].startswith("resume.experience")]
    exp_tokens = _tokenize(" ".join(s["text"] for s in exp_snippets)) if exp_snippets else resume_tokens
    resp_matches = 0
    resp_total = len(responsibilities)
    for resp in responsibilities[:10]:
        r_tokens = _tokenize(resp)
        if not r_tokens:
            continue
        overlap_ratio = len(r_tokens & exp_tokens) / len(r_tokens)
        if overlap_ratio >= 0.30:
            resp_matches += 1
        elif overlap_ratio >= 0.15:
            resp_matches += 0.5  # type: ignore[assignment]
    if resp_total > 0:
        experience_score = round(min(100.0, (resp_matches / min(resp_total, 10)) * 100), 1)
    else:
        experience_score = 75.0 if exp_snippets else 30.0

    # 3. Keyword Coverage (salient non-stopword JD terms)
    jd_tokens = _tokenize(job_description_text)
    if jd_tokens:
        overlap_terms = sorted(jd_tokens & resume_tokens)
        # Normal CVs match ~30-60% of distinct JD tokens; calibrate linearly with cap at 100
        keyword_coverage = round(min(100.0, (len(overlap_terms) / max(len(jd_tokens) * 0.55, 1)) * 100), 1)
    else:
        overlap_terms = []
        keyword_coverage = 0.0

    # 4. Education & Certifications
    resume_certs = set(extract_certifications(resume_text))
    for cert in resume_content.get("certifications") or []:
        c_name = cert.get("name") if isinstance(cert, dict) else str(cert)
        if c_name:
            resume_certs.add(str(c_name))
    has_edu = bool(resume_content.get("education"))
    edu_score = 85.0 if has_edu else 45.0
    if req_certs:
        matched_certs = sum(
            1 for rc in req_certs if any(rc.lower() in existing.lower() for existing in resume_certs)
        )
        cert_ratio = matched_certs / len(req_certs)
        edu_score = round((0.5 * (1.0 if has_edu else 0.4) + 0.5 * cert_ratio) * 100, 1)
    elif not req_edu and has_edu:
        edu_score = 95.0

    # 5. Achievement Evidence (measurable metrics & strong action verbs in experience bullets)
    bullets = [
        str(b)
        for exp in (resume_content.get("experiences") or [])
        if isinstance(exp, dict)
        for b in (exp.get("bullets") or exp.get("achievements") or [])
    ]
    if bullets:
        quantified = sum(1 for b in bullets if _METRIC_RE.search(b))
        action_led = sum(
            1 for b in bullets if b.strip() and b.strip().split()[0].lower().rstrip(".,:") in _ACTION_VERBS
        )
        quant_ratio = min(1.0, quantified / max(len(bullets) * 0.45, 1))
        action_ratio = min(1.0, action_led / max(len(bullets) * 0.6, 1))
        achievement_score = round((0.65 * quant_ratio + 0.35 * action_ratio) * 100, 1)
    else:
        achievement_score = 35.0

    # 6. Document Parsing, Formatting & Completeness (Readability)
    diag = resume_content.get("diagnostics") or {}
    parsing_score = 100.0 if diag.get("text_extractable", True) else 35.0
    formatting_score = 100.0
    if diag.get("has_tables"):
        formatting_score -= 20.0
    if diag.get("has_multi_column_risk"):
        formatting_score -= 20.0
    if diag.get("has_headers_footers"):
        formatting_score -= 10.0

    completeness_checks = [
        bool(resume_content.get("summary")),
        bool(resume_content.get("experiences")),
        bool(resume_content.get("education")),
        bool(resume_content.get("skills")),
    ]
    completeness_score = round(sum(completeness_checks) / len(completeness_checks) * 100, 1)
    readability_score = round(
        (0.35 * parsing_score + 0.35 * max(0.0, formatting_score) + 0.30 * completeness_score),
        1,
    )

    # Weighted Overall Estimate
    weighted_overall = (
        skills_score * norm_weights["skills_relevance"]
        + experience_score * norm_weights["experience_relevance"]
        + keyword_coverage * norm_weights["keyword_coverage"]
        + edu_score * norm_weights["education_certification"]
        + achievement_score * norm_weights["achievement_evidence"]
        + readability_score * norm_weights["document_readability"]
    )

    # Mandatory qualification guardrail: do not inflate score if most required skills lack evidence.
    mandatory_cap_applied = False
    if required_skills and (matched_required / len(required_skills)) < 0.35 and weighted_overall > 62.0:
        weighted_overall = 62.0
        mandatory_cap_applied = True

    overall_score = round(min(100.0, max(0.0, weighted_overall)), 2)

    if overall_score >= 80:
        band = "Strong alignment"
    elif overall_score >= 65:
        band = "Good alignment"
    elif overall_score >= 45:
        band = "Moderate alignment"
    else:
        band = "Early gap — needs targeted evidence"

    return {
        "overall_score": overall_score,
        "alignment_band": band,
        "scoring_version": SCORING_VERSION,
        "methodology_note": METHODOLOGY_NOTE,
        "mandatory_cap_applied": mandatory_cap_applied,
        "weights_used": norm_weights,
        "dimensions": {
            "document_parsing": {"score": parsing_score, "label": "Document parsing"},
            "formatting": {"score": max(0.0, formatting_score), "label": "Formatting safety"},
            "keyword_relevance": {"score": keyword_coverage, "label": "Keyword coverage"},
            "skills_alignment": {"score": skills_score, "label": "Skills alignment"},
            "experience_relevance": {"score": experience_score, "label": "Experience evidence"},
            "education_certification": {"score": edu_score, "label": "Education & certifications"},
            "achievement_evidence": {"score": achievement_score, "label": "Achievement clarity"},
            "completeness": {"score": completeness_score, "label": "Section completeness"},
            "document_readability": {"score": readability_score, "label": "Document readability (combined)"},
        },
        "requirement_matrix": requirement_matrix,
        "summary_counts": {
            "required_total": len(required_skills),
            "required_direct": matched_required,
            "required_possible": possible_required,
            "required_missing": len(missing_required),
            "preferred_total": len(preferred_skills),
            "preferred_missing": len(missing_preferred),
            "matched_keywords_count": len(overlap_terms),
        },
        "missing_required_skills": missing_required,
        "missing_preferred_skills": missing_preferred,
        "formatting_warnings": list(diag.get("warnings") or []),
    }
