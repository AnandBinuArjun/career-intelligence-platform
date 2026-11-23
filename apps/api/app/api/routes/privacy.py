import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import ACCESS_COOKIE_NAME, CSRF_COOKIE_NAME, get_current_user_id
from app.models.entities import (
    Analysis,
    Application,
    AuditLog,
    CandidateProfile,
    Certification,
    ConsentRecord,
    CoverLetter,
    Education,
    Experience,
    JobDescription,
    PrivacySettings,
    Resume,
    ResumeVersion,
    Skill,
    User,
    utcnow,
)
from app.schemas import (
    AuditLogResponse,
    ConsentCreateRequest,
    ConsentResponse,
    PrivacySettingsResponse,
    PrivacySettingsUpdate,
)
from app.services.storage.s3 import delete_object

router = APIRouter(tags=["privacy-and-account"])


def _ensure_privacy_settings(db: Session, user_id: uuid.UUID) -> PrivacySettings:
    ps = db.execute(
        select(PrivacySettings).where(PrivacySettings.user_id == user_id)
    ).scalar_one_or_none()
    if ps is None:
        ps = PrivacySettings(user_id=user_id)
        db.add(ps)
        db.commit()
        db.refresh(ps)
    return ps


@router.get("/privacy/settings", response_model=PrivacySettingsResponse)
def get_privacy_settings(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PrivacySettingsResponse:
    ps = _ensure_privacy_settings(db, user_id)
    active_provider = (
        settings.external_ai_model or "external"
        if ps.ai_routing_preference == "external_with_consent" and settings.external_ai_enabled
        else f"local ({settings.ollama_model})"
    )
    return PrivacySettingsResponse(
        retention_days=ps.retention_days,
        ai_routing_preference=ps.ai_routing_preference,
        external_ai_server_enabled=settings.external_ai_enabled,
        active_provider=active_provider,
        updated_at=ps.updated_at,
    )


@router.put("/privacy/settings", response_model=PrivacySettingsResponse)
def update_privacy_settings(
    payload: PrivacySettingsUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PrivacySettingsResponse:
    ps = _ensure_privacy_settings(db, user_id)
    ps.retention_days = payload.retention_days
    ps.ai_routing_preference = payload.ai_routing_preference
    ps.updated_at = utcnow()
    record_audit_event(
        db,
        user_id=user_id,
        action="privacy.settings_update",
        resource_type="privacy_settings",
        metadata={
            "retention_days": payload.retention_days,
            "ai_routing_preference": payload.ai_routing_preference,
        },
    )
    db.commit()
    db.refresh(ps)
    active_provider = (
        settings.external_ai_model or "external"
        if ps.ai_routing_preference == "external_with_consent" and settings.external_ai_enabled
        else f"local ({settings.ollama_model})"
    )
    return PrivacySettingsResponse(
        retention_days=ps.retention_days,
        ai_routing_preference=ps.ai_routing_preference,
        external_ai_server_enabled=settings.external_ai_enabled,
        active_provider=active_provider,
        updated_at=ps.updated_at,
    )


@router.get("/privacy/consents", response_model=list[ConsentResponse])
def list_consents(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[ConsentResponse]:
    rows = db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id)
        .order_by(ConsentRecord.recorded_at.desc())
    ).scalars().all()
    return [
        ConsentResponse(
            id=str(c.id),
            purpose=c.purpose,
            provider=c.provider,
            policy_version=c.policy_version,
            granted=c.granted,
            recorded_at=c.recorded_at,
            withdrawn_at=c.withdrawn_at,
        )
        for c in rows
    ]


@router.post("/privacy/consents", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
def record_consent(
    payload: ConsentCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ConsentResponse:
    now = utcnow()
    # If withdrawing consent, mark any active granted records for the same purpose withdrawn.
    if not payload.granted:
        active = db.execute(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.purpose == payload.purpose,
                ConsentRecord.granted.is_(True),
                ConsentRecord.withdrawn_at.is_(None),
            )
        ).scalars().all()
        for existing in active:
            existing.withdrawn_at = now

    record = ConsentRecord(
        user_id=user_id,
        purpose=payload.purpose.strip(),
        provider=payload.provider.strip() if payload.provider else None,
        policy_version=payload.policy_version,
        granted=payload.granted,
        recorded_at=now,
        withdrawn_at=None if payload.granted else now,
    )
    db.add(record)
    record_audit_event(
        db,
        user_id=user_id,
        action="privacy.consent_recorded",
        resource_type="consent_record",
        resource_id=record.id,
        metadata={"purpose": record.purpose, "granted": record.granted, "provider": record.provider},
    )
    db.commit()
    db.refresh(record)
    return ConsentResponse(
        id=str(record.id),
        purpose=record.purpose,
        provider=record.provider,
        policy_version=record.policy_version,
        granted=record.granted,
        recorded_at=record.recorded_at,
        withdrawn_at=record.withdrawn_at,
    )


@router.get("/privacy/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    rows = db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    ).scalars().all()
    return [
        AuditLogResponse(
            id=str(row.id),
            action=row.action,
            resource_type=row.resource_type,
            resource_id=str(row.resource_id) if row.resource_id else None,
            metadata=row.metadata_json or {},
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/account/export")
def export_account_data(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Portable JSON export of all personal data held for the authenticated user."""
    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    profile = db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id)).scalar_one_or_none()
    resumes = db.execute(select(Resume).where(Resume.user_id == user_id)).scalars().all()
    resume_ids = [r.id for r in resumes]
    versions = (
        db.execute(select(ResumeVersion).where(ResumeVersion.resume_id.in_(resume_ids))).scalars().all()
        if resume_ids
        else []
    )
    jobs = db.execute(select(JobDescription).where(JobDescription.user_id == user_id)).scalars().all()
    analyses = db.execute(select(Analysis).where(Analysis.user_id == user_id)).scalars().all()
    letters = db.execute(select(CoverLetter).where(CoverLetter.user_id == user_id)).scalars().all()
    apps = db.execute(select(Application).where(Application.user_id == user_id)).scalars().all()
    consents = db.execute(select(ConsentRecord).where(ConsentRecord.user_id == user_id)).scalars().all()
    experiences = db.execute(select(Experience).where(Experience.user_id == user_id)).scalars().all()
    education = db.execute(select(Education).where(Education.user_id == user_id)).scalars().all()
    skills = db.execute(select(Skill).where(Skill.user_id == user_id)).scalars().all()
    certs = db.execute(select(Certification).where(Certification.user_id == user_id)).scalars().all()

    record_audit_event(db, user_id=user_id, action="account.export", resource_type="user", resource_id=user_id)
    db.commit()

    return {
        "exported_at": utcnow().isoformat(),
        "account": {"id": str(user.id), "email": user.email, "created_at": user.created_at.isoformat()},
        "profile": {
            "full_name": profile.full_name if profile else None,
            "professional_title": profile.professional_title if profile else None,
            "summary": profile.summary if profile else None,
            "location": profile.location if profile else None,
            "target_roles": profile.target_roles if profile else [],
            "experiences": [
                {"employer": e.employer, "job_title": e.job_title, "description": e.description, "achievements": e.achievements}
                for e in experiences
            ],
            "education": [
                {"institution": ed.institution, "qualification": ed.qualification, "field_of_study": ed.field_of_study}
                for ed in education
            ],
            "skills": [{"name": s.name, "category": s.category, "proficiency": s.proficiency} for s in skills],
            "certifications": [{"name": c.name, "issuer": c.issuer} for c in certs],
        },
        "resumes": [
            {"id": str(r.id), "title": r.title, "upload_status": r.upload_status, "parse_status": r.parse_status}
            for r in resumes
        ],
        "resume_versions": [
            {"id": str(v.id), "resume_id": str(v.resume_id), "version_number": v.version_number, "content": v.content}
            for v in versions
        ],
        "job_descriptions": [
            {"id": str(j.id), "company_name": j.company_name, "job_title": j.job_title, "extracted_requirements": j.extracted_requirements}
            for j in jobs
        ],
        "analyses": [
            {"id": str(a.id), "overall_score": float(a.overall_score) if a.overall_score is not None else None, "scoring_version": a.scoring_version}
            for a in analyses
        ],
        "cover_letters": [
            {"id": str(c.id), "title": c.title, "tone": c.tone, "content": c.content}
            for c in letters
        ],
        "applications": [
            {"id": str(a.id), "company_name": a.company_name, "position": a.position, "status": a.status, "notes": a.notes}
            for a in apps
        ],
        "consent_records": [
            {"id": str(c.id), "purpose": c.purpose, "provider": c.provider, "granted": c.granted, "recorded_at": c.recorded_at.isoformat()}
            for c in consents
        ],
    }


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    response: Response,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    """Cascading deletion of user database records AND private object-storage files."""
    resumes = db.execute(select(Resume).where(Resume.user_id == user_id)).scalars().all()
    keys_to_delete = [r.original_file_key for r in resumes if r.original_file_key]

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")

    # Delete dependent records explicitly first to ensure clean cascade across all dialects/FK constraints.
    analyses = db.execute(select(Analysis).where(Analysis.user_id == user_id)).scalars().all()
    for an in analyses:
        db.delete(an)
    db.flush()

    db.delete(user)
    db.commit()

    for key in keys_to_delete:
        delete_object(key)

    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie("career_refresh_token", path="/api/v1/auth")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
