from __future__ import annotations

import re
from typing import Any

from app.services.matching.taxonomy import extract_skills_from_text

PROMPT_VERSION = "v1.0"
SCHEMA_VERSION = "v1.0"


def build_candidate_evidence_corpus(
    resume_content: dict[str, Any],
    profile_data: dict[str, Any] | None = None,
) -> tuple[str, set[str], list[dict[str, str]]]:
    """Build a verifiable text corpus + canonical skills + traceable snippets for evidence checks."""
    chunks: list[str] = []
    snippets: list[dict[str, str]] = []

    if resume_content.get("summary"):
        s = str(resume_content["summary"])
        chunks.append(s)
        snippets.append({"source": "resume.summary", "excerpt": s[:220]})

    for idx, exp in enumerate(resume_content.get("experiences") or []):
        if not isinstance(exp, dict):
            continue
        header = " ".join(str(exp.get(k) or "") for k in ("job_title", "employer", "period")).strip()
        if header:
            chunks.append(header)
            snippets.append({"source": f"resume.experience[{idx}]", "excerpt": header[:220]})
        for b_idx, bullet in enumerate(exp.get("bullets") or exp.get("achievements") or []):
            bt = str(bullet).strip()
            if bt:
                chunks.append(bt)
                snippets.append({"source": f"resume.experience[{idx}].bullet[{b_idx}]", "excerpt": bt[:220]})

    for idx, edu in enumerate(resume_content.get("education") or []):
        if isinstance(edu, dict):
            et = " ".join(str(edu.get(k) or "") for k in ("qualification", "field_of_study", "institution")).strip()
            if et:
                chunks.append(et)
                snippets.append({"source": f"resume.education[{idx}]", "excerpt": et[:220]})

    skills_list = [
        str(s.get("name") if isinstance(s, dict) else s)
        for s in (resume_content.get("skills") or [])
    ]
    if skills_list:
        joined = ", ".join(skills_list)
        chunks.append(joined)
        snippets.append({"source": "resume.skills", "excerpt": joined[:220]})

    if profile_data:
        if profile_data.get("summary"):
            chunks.append(str(profile_data["summary"]))
            snippets.append({"source": "profile.summary", "excerpt": str(profile_data["summary"])[:220]})
        for ps in profile_data.get("skills") or []:
            ps_name = ps.get("name") if isinstance(ps, dict) else str(ps)
            if ps_name:
                chunks.append(str(ps_name))
                snippets.append({"source": "profile.skills", "excerpt": str(ps_name)})

    corpus = "\n".join(chunks)
    evidenced_skills = set(extract_skills_from_text(corpus))
    for s in skills_list:
        if s.strip():
            evidenced_skills.add(s.strip())
    return corpus, {s.lower() for s in evidenced_skills}, snippets


def validate_recommendation_claim(
    suggested_text: str,
    corpus: str,
    evidenced_skills_lower: set[str],
) -> tuple[bool, list[str]]:
    """Detect whether a suggested rewrite introduces skills or metrics absent from candidate evidence."""
    unverified_items: list[str] = []

    claimed_skills = extract_skills_from_text(suggested_text)
    for skill in claimed_skills:
        if skill.lower() not in evidenced_skills_lower and skill.lower() not in corpus.lower():
            unverified_items.append(f"skill:{skill}")

    # Detect invented percentage/currency metrics not found in candidate source corpus
    claimed_metrics = re.findall(r"\b\d+(?:\.\d+)?%|\$\d[\d,.]*|\£\d[\d,.]*", suggested_text)
    for metric in claimed_metrics:
        if metric not in corpus:
            unverified_items.append(f"metric:{metric}")

    requires_confirmation = len(unverified_items) > 0
    return requires_confirmation, unverified_items


def generate_deterministic_recommendations(
    resume_content: dict[str, Any],
    scoring_data: dict[str, Any],
    job_title: str,
    profile_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Produce strictly evidence-backed, hallucination-free recommendations."""
    corpus, evidenced_skills_lower, snippets = build_candidate_evidence_corpus(resume_content, profile_data)
    recs: list[dict[str, Any]] = []

    # 1. Missing required skills -> explicitly framed as confirmation prompts, NEVER silently added
    missing_req = scoring_data.get("missing_required_skills") or []
    for skill in missing_req[:5]:
        recs.append(
            {
                "category": "missing_evidence",
                "original_text": None,
                "suggested_text": (
                    f"If you genuinely have hands-on experience with {skill}, add a concrete example "
                    f"in your Experience section showing how you used {skill} and the outcome."
                ),
                "rationale": f"'{skill}' is listed as a required skill for {job_title}, but no evidence was found in this resume version.",
                "evidence_reference": {
                    "type": "job_requirement_gap",
                    "requirement": skill,
                    "candidate_evidence_found": False,
                },
                "requires_user_confirmation": True,
            }
        )

    # 2. Possible matches -> suggest clarifying terminology if supported by actual work
    for row in scoring_data.get("requirement_matrix") or []:
        if row.get("match_state") == "possible_match":
            ev = row.get("evidence") or {}
            recs.append(
                {
                    "category": "keyword_clarity",
                    "original_text": ev.get("excerpt"),
                    "suggested_text": (
                        f"Your resume references related work ({ev.get('source', 'experience')}). "
                        f"If accurate, explicitly name '{row['requirement']}' alongside your existing bullet."
                    ),
                    "rationale": f"Helps both recruiters and parsers connect your existing evidence to '{row['requirement']}'.",
                    "evidence_reference": {
                        "type": "resume_span",
                        "source": ev.get("source"),
                        "excerpt": ev.get("excerpt"),
                    },
                    "requires_user_confirmation": True,
                }
            )

    # 3. Achievement quantification opportunities on existing bullets lacking metrics
    for idx, exp in enumerate(resume_content.get("experiences") or []):
        if not isinstance(exp, dict):
            continue
        for b_idx, bullet in enumerate(exp.get("bullets") or []):
            b_text = str(bullet).strip()
            if len(b_text) > 25 and not re.search(r"\d", b_text):
                recs.append(
                    {
                        "category": "achievement_clarity",
                        "original_text": b_text,
                        "suggested_text": (
                            f"{b_text.rstrip('.')} — quantify the scope or outcome "
                            "(e.g., team size, latency reduction, incidents handled, or time saved) using real figures."
                        ),
                        "rationale": "Adding real, verifiable metrics makes existing impact concrete without fabricating claims.",
                        "evidence_reference": {
                            "type": "resume_span",
                            "source": f"resume.experience[{idx}].bullet[{b_idx}]",
                            "excerpt": b_text[:220],
                        },
                        "requires_user_confirmation": False,
                    }
                )
                break
        if len(recs) >= 8:
            break

    # 4. Formatting & ATS readability warnings
    for warning in scoring_data.get("formatting_warnings") or []:
        recs.append(
            {
                "category": "formatting",
                "original_text": None,
                "suggested_text": f"Switch to a single-column, standard-heading layout: {warning}",
                "rationale": "Improves reliable text extraction across different ATS parsers.",
                "evidence_reference": {"type": "document_diagnostics", "warning": warning},
                "requires_user_confirmation": False,
            }
        )

    # 5. Summary tailoring suggestion grounded strictly in matched required skills
    matched_skills = [
        r["requirement"]
        for r in (scoring_data.get("requirement_matrix") or [])
        if r.get("match_state") == "direct_match"
    ]
    if matched_skills:
        top_matched = ", ".join(matched_skills[:4])
        original_summary = str(resume_content.get("summary") or "").strip() or None
        suggested_summary = (
            f"Tailor your summary for {job_title} by highlighting your verified experience in "
            f"{top_matched}."
        )
        req_confirm, unverified = validate_recommendation_claim(
            suggested_summary, corpus, evidenced_skills_lower
        )
        recs.append(
            {
                "category": "summary_tailoring",
                "original_text": original_summary,
                "suggested_text": suggested_summary,
                "rationale": "Foregrounds already-verified skills that directly match the target role.",
                "evidence_reference": {
                    "type": "verified_skills_overlap",
                    "matched_skills": matched_skills[:6],
                    "unverified_flags": unverified,
                    "snippets": snippets[:2],
                },
                "requires_user_confirmation": req_confirm,
            }
        )

    return recs[:12]


def generate_grounded_cover_letter(
    *,
    resume_content: dict[str, Any],
    job_title: str,
    company_name: str | None,
    job_requirements: dict[str, Any],
    tone: str = "professional",
    length: str = "medium",
    custom_notes: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Generate a strictly evidence-grounded cover letter draft with explicit citations."""
    candidate_name = str(resume_content.get("full_name") or "Candidate").strip()
    employer_label = company_name or "your organization"
    resume_skills = {
        str(s.get("name") if isinstance(s, dict) else s).lower(): str(
            s.get("name") if isinstance(s, dict) else s
        )
        for s in (resume_content.get("skills") or [])
    }
    req_skills = list(job_requirements.get("required_skills") or [])
    matched_skills = [s for s in req_skills if s.lower() in resume_skills]
    if not matched_skills:
        matched_skills = list(resume_skills.values())[:4]

    experiences = [e for e in (resume_content.get("experiences") or []) if isinstance(e, dict)]
    evidence_refs: list[dict[str, Any]] = []

    if tone == "concise":
        opening = f"Dear Hiring Team,\n\nI am writing to apply for the {job_title} position at {employer_label}."
    elif tone == "formal":
        opening = (
            f"Dear Hiring Manager,\n\nPlease accept this letter as my formal application for the "
            f"{job_title} role at {employer_label}."
        )
    elif tone == "executive":
        opening = (
            f"Dear Hiring Committee,\n\nI am pleased to submit my candidacy for the {job_title} role at "
            f"{employer_label}, bringing a track record of delivering measurable outcomes."
        )
    else:
        opening = (
            f"Dear Hiring Team,\n\nI am excited to apply for the {job_title} role at {employer_label}. "
            f"My background aligns closely with your core priorities for this position."
        )

    body_paragraphs: list[str] = []
    if matched_skills:
        skills_str = ", ".join(matched_skills[:5])
        body_paragraphs.append(
            f"Across my work, I have built verified hands-on experience with {skills_str}, "
            f"directly supporting the core technical and operational needs outlined in your job description."
        )
        evidence_refs.append(
            {
                "claim": f"Experience with {skills_str}",
                "source": "resume.skills",
                "verified": True,
            }
        )

    for idx, exp in enumerate(experiences[:2 if length != "short" else 1]):
        role = exp.get("job_title") or "my previous role"
        org = f" at {exp['employer']}" if exp.get("employer") else ""
        bullets = [str(b).strip() for b in (exp.get("bullets") or []) if str(b).strip()]
        if bullets:
            highlight = bullets[0].rstrip(".")
            second = f" In addition, I {bullets[1][0].lower() + bullets[1][1:].rstrip('.')}." if len(bullets) > 1 and length == "detailed" else ""
            body_paragraphs.append(
                f"As {role}{org}, I contributed directly to relevant initiatives: {highlight}.{second}"
            )
            evidence_refs.append(
                {
                    "claim": f"Role evidence from {role}{org}",
                    "source": f"resume.experience[{idx}].bullet[0]",
                    "excerpt": bullets[0][:200],
                    "verified": True,
                }
            )

    if custom_notes and custom_notes.strip():
        body_paragraphs.append(custom_notes.strip())
        evidence_refs.append(
            {
                "claim": "Candidate-supplied motivation/context",
                "source": "user.custom_notes",
                "verified": True,
            }
        )

    closing = (
        f"I would welcome the opportunity to discuss how my verified experience can contribute to "
        f"{employer_label}. Thank you for your time and consideration.\n\nSincerely,\n{candidate_name}"
    )

    full_letter = "\n\n".join([opening, *body_paragraphs, closing])
    return full_letter, evidence_refs
