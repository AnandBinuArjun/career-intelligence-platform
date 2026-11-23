import uuid
from collections import Counter
from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.models.entities import (
    Analysis,
    CandidateProfile,
    Experience,
    JobDescription,
    Resume,
    ResumeVersion,
    Skill,
)
from app.schemas import CareerOverviewResponse, InterviewPrepRequest

router = APIRouter(prefix="/career", tags=["career-development"])


def _learning_action_for_skill(skill: str, frequency: int) -> dict[str, Any]:
    priority = "High" if frequency >= 2 else "Medium"
    return {
        "skill": skill,
        "priority": priority,
        "demand_count": frequency,
        "recommended_step": (
            f"Build a small, verifiable portfolio artifact demonstrating {skill}, document the "
            f"architecture and outcomes, and add it to your profile once completed."
        ),
        "evidence_goal": f"At least one concrete project or role bullet proving applied {skill} usage.",
    }


def _build_interview_questions(
    *,
    role_title: str,
    matched_skills: list[str],
    missing_skills: list[str],
    experiences: Sequence[Experience],
) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []

    for skill in matched_skills[:3]:
        questions.append(
            {
                "category": "Technical deep-dive",
                "topic": skill,
                "question": f"Walk through a real project where you applied {skill} in production. What trade-offs did you evaluate and what measurable result did you achieve?",
                "evidence_tip": f"Anchor your answer in your verified {skill} work using Situation-Task-Action-Result (STAR).",
            }
        )

    for gap in missing_skills[:2]:
        questions.append(
            {
                "category": "Gap & adaptability",
                "topic": gap,
                "question": f"This {role_title} role values {gap}. How would you ramp up on {gap} quickly using your adjacent technical strengths?",
                "evidence_tip": f"Be transparent about your current depth in {gap} while connecting it to verifiable adjacent systems you have already built.",
            }
        )

    if experiences:
        recent = experiences[0]
        questions.append(
            {
                "category": "Behavioral / Impact",
                "topic": recent.job_title,
                "question": f"Tell me about the hardest technical or stakeholder challenge you navigated as {recent.job_title}"
                + (f" at {recent.employer}" if recent.employer else "")
                + ".",
                "evidence_tip": "Cite specific constraints, decisions you owned personally, and verifiable outcomes.",
            }
        )

    if not questions:
        questions.append(
            {
                "category": "Role alignment",
                "topic": role_title,
                "question": f"What specific problems in a {role_title} role are you most prepared to solve in your first 90 days?",
                "evidence_tip": "Add verified experiences and run an ATS analysis to generate tailored evidence-based questions.",
            }
        )

    return questions


@router.get("/overview", response_model=CareerOverviewResponse)
def career_overview(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CareerOverviewResponse:
    profile = db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    ).scalar_one_or_none()
    skills = db.execute(select(Skill).where(Skill.user_id == user_id)).scalars().all()
    experiences = db.execute(
        select(Experience).where(Experience.user_id == user_id).order_by(Experience.start_date.desc())
    ).scalars().all()
    analyses = db.execute(
        select(Analysis).where(Analysis.user_id == user_id).order_by(Analysis.created_at.desc()).limit(20)
    ).scalars().all()

    missing_counter: Counter[str] = Counter()
    matched_counter: Counter[str] = Counter()
    for an in analyses:
        data = an.scoring_data or {}
        for sk in data.get("missing_required_skills") or []:
            missing_counter[sk] += 2  # Required gaps weighted higher
        for sk in data.get("missing_preferred_skills") or []:
            missing_counter[sk] += 1
        for row in data.get("requirement_matrix") or []:
            if row.get("match_state") == "direct_match" and row.get("requirement"):
                matched_counter[row["requirement"]] += 1

    top_gaps: list[dict[str, Any]] = [
        {"skill": skill, "gap_weight": count, "status": "missing_evidence"}
        for skill, count in missing_counter.most_common(8)
    ]
    learning_plan = [
        _learning_action_for_skill(str(g["skill"]), int(g["gap_weight"])) for g in top_gaps[:6]
    ]

    target_roles = list(profile.target_roles or []) if profile else []
    focus_role = target_roles[0] if target_roles else (profile.professional_title if profile and profile.professional_title else "target role")
    matched_list = [s for s, _ in matched_counter.most_common(5)] or [s.name for s in skills[:4]]
    missing_list = [str(g["skill"]) for g in top_gaps[:3]]

    questions = _build_interview_questions(
        role_title=focus_role,
        matched_skills=matched_list,
        missing_skills=missing_list,
        experiences=experiences,
    )

    return CareerOverviewResponse(
        target_roles=target_roles,
        verified_skills_count=len(skills),
        analyzed_jobs_count=len(analyses),
        top_skill_gaps=top_gaps,
        learning_plan=learning_plan,
        interview_questions=questions,
    )


@router.post("/interview-prep")
def generate_interview_prep(
    payload: InterviewPrepRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    role_title = payload.focus_role or "Target Role"
    matched_skills: list[str] = []
    missing_skills: list[str] = []

    if payload.job_description_id:
        try:
            jd_id = uuid.UUID(payload.job_description_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid job_description_id") from None
        job = db.execute(
            select(JobDescription).where(JobDescription.id == jd_id, JobDescription.user_id == user_id)
        ).scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=404, detail="Job description not found")
        role_title = job.job_title
        reqs = job.extracted_requirements or {}
        jd_skills = list(reqs.get("required_skills") or [])

        candidate_skills: set[str] = {
            s.name.lower()
            for s in db.execute(select(Skill).where(Skill.user_id == user_id)).scalars().all()
        }
        if payload.resume_version_id:
            try:
                rv_id = uuid.UUID(payload.resume_version_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid resume_version_id") from None
            rv_row = db.execute(
                select(ResumeVersion)
                .join(Resume, ResumeVersion.resume_id == Resume.id)
                .where(ResumeVersion.id == rv_id, Resume.user_id == user_id)
            ).scalar_one_or_none()
            if rv_row is not None:
                for sk in (rv_row.content or {}).get("skills") or []:
                    candidate_skills.add(str(sk.get("name") if isinstance(sk, dict) else sk).lower())

        for sk in jd_skills:
            if sk.lower() in candidate_skills:
                matched_skills.append(sk)
            else:
                missing_skills.append(sk)

    experiences = db.execute(
        select(Experience).where(Experience.user_id == user_id).order_by(Experience.start_date.desc())
    ).scalars().all()

    questions = _build_interview_questions(
        role_title=role_title,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        experiences=experiences,
    )
    return {
        "role": role_title,
        "matched_topics": matched_skills,
        "gap_topics": missing_skills,
        "questions": questions,
    }
