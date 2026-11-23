import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.models.entities import (
    Application,
    InterviewRecord,
    JobDescription,
    Resume,
    ResumeVersion,
    utcnow,
)
from app.schemas import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationUpdateRequest,
    InterviewCreateRequest,
    InterviewResponse,
)

router = APIRouter(prefix="/applications", tags=["applications"])


def _parse_optional_uuid(raw: str | None, label: str) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label}") from None


def _verify_links(
    db: Session,
    user_id: uuid.UUID,
    jd_id: uuid.UUID | None,
    rv_id: uuid.UUID | None,
) -> None:
    if jd_id is not None:
        job = db.execute(
            select(JobDescription.id).where(JobDescription.id == jd_id, JobDescription.user_id == user_id)
        ).scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=404, detail="Linked job description not found")
    if rv_id is not None:
        rv = db.execute(
            select(ResumeVersion.id)
            .join(Resume, ResumeVersion.resume_id == Resume.id)
            .where(ResumeVersion.id == rv_id, Resume.user_id == user_id)
        ).scalar_one_or_none()
        if rv is None:
            raise HTTPException(status_code=404, detail="Linked resume version not found")


def _serialize_interview(iv: InterviewRecord) -> InterviewResponse:
    return InterviewResponse(
        id=str(iv.id),
        application_id=str(iv.application_id),
        scheduled_at=iv.scheduled_at,
        interview_type=iv.interview_type,
        notes=iv.notes,
        outcome=iv.outcome,
        created_at=iv.created_at,
    )


def _serialize_application(db: Session, app_row: Application) -> ApplicationResponse:
    interviews = db.execute(
        select(InterviewRecord)
        .where(InterviewRecord.application_id == app_row.id)
        .order_by(InterviewRecord.scheduled_at.asc(), InterviewRecord.created_at.asc())
    ).scalars().all()
    return ApplicationResponse(
        id=str(app_row.id),
        company_name=app_row.company_name,
        position=app_row.position,
        job_description_id=str(app_row.job_description_id) if app_row.job_description_id else None,
        resume_version_id=str(app_row.resume_version_id) if app_row.resume_version_id else None,
        status=app_row.status,
        applied_at=app_row.applied_at,
        follow_up_at=app_row.follow_up_at,
        salary_range=app_row.salary_range,
        location=app_row.location,
        notes=app_row.notes,
        interviews=[_serialize_interview(iv) for iv in interviews],
        created_at=app_row.created_at,
        updated_at=app_row.updated_at,
    )


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[ApplicationResponse]:
    rows = db.execute(
        select(Application)
        .where(Application.user_id == user_id)
        .order_by(Application.updated_at.desc())
    ).scalars().all()
    return [_serialize_application(db, row) for row in rows]


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    jd_id = _parse_optional_uuid(payload.job_description_id, "job_description_id")
    rv_id = _parse_optional_uuid(payload.resume_version_id, "resume_version_id")
    _verify_links(db, user_id, jd_id, rv_id)

    app_row = Application(
        user_id=user_id,
        company_name=payload.company_name.strip() if payload.company_name else None,
        position=payload.position.strip(),
        job_description_id=jd_id,
        resume_version_id=rv_id,
        status=payload.status,
        applied_at=payload.applied_at or (utcnow() if payload.status == "applied" else None),
        follow_up_at=payload.follow_up_at,
        salary_range=payload.salary_range,
        location=payload.location,
        notes=payload.notes,
    )
    db.add(app_row)
    record_audit_event(
        db,
        user_id=user_id,
        action="application.create",
        resource_type="application",
        resource_id=app_row.id,
        metadata={"status": payload.status},
    )
    db.commit()
    db.refresh(app_row)
    return _serialize_application(db, app_row)


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    row = db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == user_id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return _serialize_application(db, row)


@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    row = db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == user_id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Application not found")

    jd_id = _parse_optional_uuid(payload.job_description_id, "job_description_id")
    rv_id = _parse_optional_uuid(payload.resume_version_id, "resume_version_id")
    _verify_links(db, user_id, jd_id, rv_id)

    if payload.company_name is not None:
        row.company_name = payload.company_name.strip() or None
    if payload.position is not None:
        row.position = payload.position.strip()
    if payload.job_description_id is not None:
        row.job_description_id = jd_id
    if payload.resume_version_id is not None:
        row.resume_version_id = rv_id
    if payload.status is not None:
        row.status = payload.status
        if payload.status == "applied" and row.applied_at is None and payload.applied_at is None:
            row.applied_at = utcnow()
    if payload.applied_at is not None:
        row.applied_at = payload.applied_at
    if payload.follow_up_at is not None:
        row.follow_up_at = payload.follow_up_at
    if payload.salary_range is not None:
        row.salary_range = payload.salary_range
    if payload.location is not None:
        row.location = payload.location
    if payload.notes is not None:
        row.notes = payload.notes
    row.updated_at = utcnow()
    db.commit()
    db.refresh(row)
    return _serialize_application(db, row)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    row = db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == user_id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(row)
    db.commit()


@router.post("/{application_id}/interviews", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def add_interview(
    application_id: uuid.UUID,
    payload: InterviewCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    app_row = db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == user_id)
    ).scalar_one_or_none()
    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")

    iv = InterviewRecord(
        application_id=app_row.id,
        scheduled_at=payload.scheduled_at,
        interview_type=payload.interview_type,
        notes=payload.notes,
        outcome=payload.outcome,
    )
    db.add(iv)
    db.commit()
    db.refresh(iv)
    return _serialize_interview(iv)


@router.delete("/{application_id}/interviews/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview(
    application_id: uuid.UUID,
    interview_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    app_row = db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == user_id)
    ).scalar_one_or_none()
    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    iv = db.execute(
        select(InterviewRecord).where(
            InterviewRecord.id == interview_id, InterviewRecord.application_id == app_row.id
        )
    ).scalar_one_or_none()
    if iv is None:
        raise HTTPException(status_code=404, detail="Interview record not found")
    db.delete(iv)
    db.commit()
