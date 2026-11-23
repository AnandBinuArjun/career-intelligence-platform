import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.models.entities import JobDescription
from app.schemas import JobCreateRequest, JobResponse, JobUpdateRequest
from app.services.matching.job_parser import parse_job_description

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _serialize_job(job: JobDescription) -> JobResponse:
    return JobResponse(
        id=str(job.id),
        company_name=job.company_name,
        job_title=job.job_title,
        description=job.description,
        extracted_requirements=job.extracted_requirements or {},
        created_at=job.created_at,
    )


@router.get("", response_model=list[JobResponse])
def list_jobs(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    rows = db.execute(
        select(JobDescription)
        .where(JobDescription.user_id == user_id)
        .order_by(JobDescription.created_at.desc())
    ).scalars().all()
    return [_serialize_job(j) for j in rows]


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JobResponse:
    extracted = parse_job_description(payload.job_title, payload.description, payload.company_name)
    job = JobDescription(
        user_id=user_id,
        company_name=payload.company_name.strip() if payload.company_name else None,
        job_title=payload.job_title.strip(),
        description=payload.description.strip(),
        extracted_requirements=extracted,
    )
    db.add(job)
    record_audit_event(db, user_id=user_id, action="job.create", resource_type="job_description", resource_id=job.id)
    db.commit()
    db.refresh(job)
    return _serialize_job(job)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = db.execute(
        select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user_id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job description not found")
    return _serialize_job(job)


@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = db.execute(
        select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user_id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job description not found")

    if payload.company_name is not None:
        job.company_name = payload.company_name.strip() or None
    if payload.job_title is not None:
        job.job_title = payload.job_title.strip()
    if payload.description is not None:
        job.description = payload.description.strip()
    if payload.extracted_requirements is not None:
        # Allow users to correct extracted requirements before running ATS analysis.
        job.extracted_requirements = payload.extracted_requirements
    elif payload.description is not None or payload.job_title is not None:
        job.extracted_requirements = parse_job_description(job.job_title, job.description, job.company_name)

    db.commit()
    db.refresh(job)
    return _serialize_job(job)


@router.post("/{job_id}/analyze", response_model=JobResponse)
def analyze_job_requirements(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = db.execute(
        select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user_id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job description not found")
    job.extracted_requirements = parse_job_description(job.job_title, job.description, job.company_name)
    db.commit()
    db.refresh(job)
    return _serialize_job(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    job = db.execute(
        select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user_id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job description not found")
    db.delete(job)
    db.commit()
