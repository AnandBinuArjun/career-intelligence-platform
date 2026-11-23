import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.models.entities import (
    Analysis,
    Application,
    CandidateProfile,
    Certification,
    CoverLetter,
    Education,
    Experience,
    InterviewRecord,
    JobDescription,
    PrivacySettings,
    Resume,
    Skill,
    User,
    utcnow,
)
from app.schemas import (
    CandidateProfileUpdate,
    CertificationCreate,
    CertificationResponse,
    DashboardSummaryResponse,
    EducationCreate,
    EducationResponse,
    ExperienceCreate,
    ExperienceResponse,
    FullProfileResponse,
    SkillCreate,
    SkillResponse,
)

router = APIRouter(tags=["profile"])


def _ensure_profile(db: Session, user_id: uuid.UUID) -> CandidateProfile:
    profile = db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    ).scalar_one_or_none()
    if profile is None:
        profile = CandidateProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _serialize_full_profile(db: Session, user_id: uuid.UUID) -> FullProfileResponse:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    profile = _ensure_profile(db, user_id)
    experiences = db.execute(
        select(Experience).where(Experience.user_id == user_id).order_by(Experience.start_date.desc())
    ).scalars().all()
    education = db.execute(
        select(Education).where(Education.user_id == user_id).order_by(Education.end_date.desc())
    ).scalars().all()
    skills = db.execute(
        select(Skill).where(Skill.user_id == user_id).order_by(Skill.name.asc())
    ).scalars().all()
    certifications = db.execute(
        select(Certification).where(Certification.user_id == user_id).order_by(Certification.issued_on.desc())
    ).scalars().all()

    return FullProfileResponse(
        user_id=str(user_id),
        email=user.email,
        full_name=profile.full_name,
        professional_title=profile.professional_title,
        summary=profile.summary,
        location=profile.location,
        contact_data=profile.contact_data or {},
        target_roles=list(profile.target_roles or []),
        years_experience=float(profile.years_experience) if profile.years_experience is not None else None,
        experiences=[
            ExperienceResponse(
                id=str(e.id),
                employer=e.employer,
                job_title=e.job_title,
                location=e.location,
                start_date=e.start_date,
                end_date=e.end_date,
                is_current=e.is_current,
                description=e.description,
                achievements=list(e.achievements or []),
                verified=e.verified,
                source_reference=e.source_reference or {},
            )
            for e in experiences
        ],
        education=[
            EducationResponse(
                id=str(ed.id),
                institution=ed.institution,
                qualification=ed.qualification,
                field_of_study=ed.field_of_study,
                start_date=ed.start_date,
                end_date=ed.end_date,
                source_reference=ed.source_reference or {},
            )
            for ed in education
        ],
        skills=[
            SkillResponse(
                id=str(s.id),
                name=s.name,
                category=s.category,
                proficiency=s.proficiency,
                years_experience=float(s.years_experience) if s.years_experience is not None else None,
                evidence_reference=s.evidence_reference or {},
            )
            for s in skills
        ],
        certifications=[
            CertificationResponse(
                id=str(c.id),
                name=c.name,
                issuer=c.issuer,
                credential_id=c.credential_id,
                issued_on=c.issued_on,
                expires_on=c.expires_on,
                evidence_reference=c.evidence_reference or {},
            )
            for c in certifications
        ],
    )


@router.get("/profile", response_model=FullProfileResponse)
def get_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FullProfileResponse:
    return _serialize_full_profile(db, user_id)


@router.put("/profile", response_model=FullProfileResponse)
def update_profile(
    payload: CandidateProfileUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FullProfileResponse:
    profile = _ensure_profile(db, user_id)
    profile.full_name = payload.full_name
    profile.professional_title = payload.professional_title
    profile.summary = payload.summary
    profile.location = payload.location
    profile.contact_data = payload.contact_data
    profile.target_roles = payload.target_roles
    profile.years_experience = (
        Decimal(str(payload.years_experience)) if payload.years_experience is not None else None
    )
    profile.updated_at = utcnow()
    db.commit()
    return _serialize_full_profile(db, user_id)


@router.post("/profile/experiences", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
def add_experience(
    payload: ExperienceCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ExperienceResponse:
    item = Experience(
        user_id=user_id,
        employer=payload.employer,
        job_title=payload.job_title,
        location=payload.location,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
        description=payload.description,
        achievements=payload.achievements,
        verified=True,
        source_reference=payload.source_reference or {"origin": "user_verified"},
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ExperienceResponse(
        id=str(item.id),
        employer=item.employer,
        job_title=item.job_title,
        location=item.location,
        start_date=item.start_date,
        end_date=item.end_date,
        is_current=item.is_current,
        description=item.description,
        achievements=list(item.achievements or []),
        verified=item.verified,
        source_reference=item.source_reference or {},
    )


@router.delete("/profile/experiences/{exp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience(
    exp_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    item = db.execute(
        select(Experience).where(Experience.id == exp_id, Experience.user_id == user_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Experience record not found")
    db.delete(item)
    db.commit()


@router.post("/profile/education", response_model=EducationResponse, status_code=status.HTTP_201_CREATED)
def add_education(
    payload: EducationCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> EducationResponse:
    item = Education(
        user_id=user_id,
        institution=payload.institution,
        qualification=payload.qualification,
        field_of_study=payload.field_of_study,
        start_date=payload.start_date,
        end_date=payload.end_date,
        source_reference=payload.source_reference or {"origin": "user_verified"},
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return EducationResponse(
        id=str(item.id),
        institution=item.institution,
        qualification=item.qualification,
        field_of_study=item.field_of_study,
        start_date=item.start_date,
        end_date=item.end_date,
        source_reference=item.source_reference or {},
    )


@router.delete("/profile/education/{edu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_education(
    edu_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    item = db.execute(
        select(Education).where(Education.id == edu_id, Education.user_id == user_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Education record not found")
    db.delete(item)
    db.commit()


@router.post("/profile/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def add_skill(
    payload: SkillCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SkillResponse:
    item = Skill(
        user_id=user_id,
        name=payload.name.strip(),
        category=payload.category,
        proficiency=payload.proficiency,
        years_experience=(
            Decimal(str(payload.years_experience)) if payload.years_experience is not None else None
        ),
        evidence_reference=payload.evidence_reference or {"origin": "user_verified"},
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Skill already exists on your profile") from None
    db.refresh(item)
    return SkillResponse(
        id=str(item.id),
        name=item.name,
        category=item.category,
        proficiency=item.proficiency,
        years_experience=float(item.years_experience) if item.years_experience is not None else None,
        evidence_reference=item.evidence_reference or {},
    )


@router.delete("/profile/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    item = db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(item)
    db.commit()


@router.post("/profile/certifications", response_model=CertificationResponse, status_code=status.HTTP_201_CREATED)
def add_certification(
    payload: CertificationCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CertificationResponse:
    item = Certification(
        user_id=user_id,
        name=payload.name.strip(),
        issuer=payload.issuer,
        credential_id=payload.credential_id,
        issued_on=payload.issued_on,
        expires_on=payload.expires_on,
        evidence_reference=payload.evidence_reference or {"origin": "user_verified"},
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return CertificationResponse(
        id=str(item.id),
        name=item.name,
        issuer=item.issuer,
        credential_id=item.credential_id,
        issued_on=item.issued_on,
        expires_on=item.expires_on,
        evidence_reference=item.evidence_reference or {},
    )


@router.delete("/profile/certifications/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certification(
    cert_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    item = db.execute(
        select(Certification).where(Certification.id == cert_id, Certification.user_id == user_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Certification not found")
    db.delete(item)
    db.commit()


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    profile = _ensure_profile(db, user_id)
    exp_count = db.execute(select(func.count()).select_from(Experience).where(Experience.user_id == user_id)).scalar_one()
    edu_count = db.execute(select(func.count()).select_from(Education).where(Education.user_id == user_id)).scalar_one()
    skill_count = db.execute(select(func.count()).select_from(Skill).where(Skill.user_id == user_id)).scalar_one()

    completeness_checks = [
        bool(profile.full_name),
        bool(profile.professional_title),
        bool(profile.summary),
        exp_count > 0,
        edu_count > 0,
        skill_count > 0,
    ]
    completeness_pct = round(sum(completeness_checks) / len(completeness_checks) * 100)

    resumes_count = db.execute(select(func.count()).select_from(Resume).where(Resume.user_id == user_id)).scalar_one()
    jobs_count = db.execute(select(func.count()).select_from(JobDescription).where(JobDescription.user_id == user_id)).scalar_one()
    analyses_count = db.execute(select(func.count()).select_from(Analysis).where(Analysis.user_id == user_id)).scalar_one()
    cover_letters_count = db.execute(select(func.count()).select_from(CoverLetter).where(CoverLetter.user_id == user_id)).scalar_one()

    apps = db.execute(select(Application).where(Application.user_id == user_id)).scalars().all()
    pipeline: dict[str, int] = {}
    active_statuses = {"ready", "applied", "screening", "interview", "assessment", "offer"}
    active_count = 0
    for app_row in apps:
        pipeline[app_row.status] = pipeline.get(app_row.status, 0) + 1
        if app_row.status in active_statuses:
            active_count += 1

    now = datetime.now(UTC)
    app_ids = [a.id for a in apps]
    upcoming_interviews = 0
    if app_ids:
        interviews = db.execute(
            select(InterviewRecord).where(InterviewRecord.application_id.in_(app_ids))
        ).scalars().all()
        for iv in interviews:
            if iv.scheduled_at is not None:
                dt = iv.scheduled_at if iv.scheduled_at.tzinfo else iv.scheduled_at.replace(tzinfo=UTC)
                if dt >= now:
                    upcoming_interviews += 1

    recent_rows = db.execute(
        select(Analysis, JobDescription)
        .join(JobDescription, Analysis.job_description_id == JobDescription.id)
        .where(Analysis.user_id == user_id)
        .order_by(Analysis.created_at.desc())
        .limit(5)
    ).all()
    recent_analyses = [
        {
            "id": str(an.id),
            "job_title": jd.job_title,
            "company_name": jd.company_name,
            "status": an.status,
            "overall_score": float(an.overall_score) if an.overall_score is not None else None,
            "scoring_version": an.scoring_version,
            "created_at": an.created_at.isoformat(),
        }
        for an, jd in recent_rows
    ]

    priv = db.execute(select(PrivacySettings).where(PrivacySettings.user_id == user_id)).scalar_one_or_none()
    ai_pref = priv.ai_routing_preference if priv else "local"

    return DashboardSummaryResponse(
        profile_completeness_pct=completeness_pct,
        resumes_count=resumes_count,
        jobs_count=jobs_count,
        analyses_count=analyses_count,
        cover_letters_count=cover_letters_count,
        active_applications_count=active_count,
        upcoming_interviews_count=upcoming_interviews,
        application_pipeline=pipeline,
        recent_analyses=recent_analyses,
        ai_routing_status={
            "mode": settings.ai_routing_mode,
            "user_preference": ai_pref,
            "external_ai_enabled": settings.external_ai_enabled,
            "local_model": settings.ollama_model,
            "local_first": True,
        },
    )
