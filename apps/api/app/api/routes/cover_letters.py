import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.rate_limit import rate_limit
from app.models.entities import CoverLetter, JobDescription, Resume, ResumeVersion, utcnow
from app.schemas import CoverLetterCreateRequest, CoverLetterResponse, CoverLetterUpdateRequest
from app.services.ai.gateway import generate_cover_letter_via_gateway
from app.services.documents.exporter import export_cover_letter_docx, export_cover_letter_pdf
from app.services.documents.validation import safe_filename

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


def _serialize_letter(letter: CoverLetter) -> CoverLetterResponse:
    return CoverLetterResponse(
        id=str(letter.id),
        job_description_id=str(letter.job_description_id) if letter.job_description_id else None,
        resume_version_id=str(letter.resume_version_id) if letter.resume_version_id else None,
        title=letter.title,
        tone=letter.tone,
        content=letter.content,
        evidence_references=list(letter.evidence_references or []),
        model_metadata=letter.model_metadata or {},
        version=letter.version,
        created_at=letter.created_at,
        updated_at=letter.updated_at,
    )


def _parse_uuid(raw: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label}") from None


@router.get("", response_model=list[CoverLetterResponse])
def list_cover_letters(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[CoverLetterResponse]:
    rows = db.execute(
        select(CoverLetter).where(CoverLetter.user_id == user_id).order_by(CoverLetter.updated_at.desc())
    ).scalars().all()
    return [_serialize_letter(row) for row in rows]


async def _create_grounded_letter(
    payload: CoverLetterCreateRequest,
    user_id: uuid.UUID,
    db: Session,
) -> CoverLetterResponse:
    jd_id = _parse_uuid(payload.job_description_id, "job_description_id")
    rv_id = _parse_uuid(payload.resume_version_id, "resume_version_id")

    job = db.execute(
        select(JobDescription).where(JobDescription.id == jd_id, JobDescription.user_id == user_id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job description not found")

    rv_row = db.execute(
        select(ResumeVersion, Resume)
        .join(Resume, ResumeVersion.resume_id == Resume.id)
        .where(ResumeVersion.id == rv_id, Resume.user_id == user_id)
    ).one_or_none()
    if rv_row is None:
        raise HTTPException(status_code=404, detail="Resume version not found")
    resume_version, _resume = rv_row

    content, evidence_refs, model_meta = await generate_cover_letter_via_gateway(
        db,
        user_id=user_id,
        resume_content=resume_version.content or {},
        job_title=job.job_title,
        company_name=job.company_name,
        job_requirements=job.extracted_requirements or {},
        tone=payload.tone,
        length=payload.length,
        custom_notes=payload.custom_notes,
        external_ai_consent_id=payload.external_ai_consent_id,
    )

    title = f"Cover Letter — {job.job_title}" + (f" ({job.company_name})" if job.company_name else "")
    letter = CoverLetter(
        user_id=user_id,
        job_description_id=job.id,
        resume_version_id=resume_version.id,
        title=title,
        tone=payload.tone,
        content=content,
        evidence_references=evidence_refs,
        model_metadata=model_meta,
        version=1,
    )
    db.add(letter)
    record_audit_event(
        db,
        user_id=user_id,
        action="cover_letter.generate",
        resource_type="cover_letter",
        resource_id=letter.id,
        metadata={"tone": payload.tone, "provider": model_meta.get("provider")},
    )
    db.commit()
    db.refresh(letter)
    return _serialize_letter(letter)


@router.post(
    "",
    response_model=CoverLetterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("cover_letter_gen", limit=20, window_seconds=300))],
)
async def create_cover_letter(
    payload: CoverLetterCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CoverLetterResponse:
    return await _create_grounded_letter(payload, user_id, db)


@router.post(
    "/generate",
    response_model=CoverLetterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("cover_letter_gen", limit=20, window_seconds=300))],
)
async def generate_cover_letter(
    payload: CoverLetterCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CoverLetterResponse:
    return await _create_grounded_letter(payload, user_id, db)


@router.get("/{letter_id}", response_model=CoverLetterResponse)
def get_cover_letter(
    letter_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CoverLetterResponse:
    letter = db.execute(
        select(CoverLetter).where(CoverLetter.id == letter_id, CoverLetter.user_id == user_id)
    ).scalar_one_or_none()
    if letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return _serialize_letter(letter)


@router.put("/{letter_id}", response_model=CoverLetterResponse)
def update_cover_letter(
    letter_id: uuid.UUID,
    payload: CoverLetterUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CoverLetterResponse:
    letter = db.execute(
        select(CoverLetter).where(CoverLetter.id == letter_id, CoverLetter.user_id == user_id)
    ).scalar_one_or_none()
    if letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    if payload.title is not None:
        letter.title = payload.title.strip()
    if payload.tone is not None:
        letter.tone = payload.tone
    letter.content = payload.content
    letter.version += 1
    letter.updated_at = utcnow()
    db.commit()
    db.refresh(letter)
    return _serialize_letter(letter)


@router.delete("/{letter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cover_letter(
    letter_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    letter = db.execute(
        select(CoverLetter).where(CoverLetter.id == letter_id, CoverLetter.user_id == user_id)
    ).scalar_one_or_none()
    if letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    db.delete(letter)
    db.commit()


@router.get("/{letter_id}/export")
def export_cover_letter(
    letter_id: uuid.UUID,
    format: str = Query(default="pdf", pattern="^(pdf|docx|txt)$"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Response:
    letter = db.execute(
        select(CoverLetter).where(CoverLetter.id == letter_id, CoverLetter.user_id == user_id)
    ).scalar_one_or_none()
    if letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    title = letter.title or "Cover Letter"
    filename = safe_filename(f"{title}.{format}")
    if format == "txt":
        data = letter.content.encode("utf-8")
        media_type = "text/plain; charset=utf-8"
    elif format == "docx":
        data = export_cover_letter_docx(title, letter.content)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        data = export_cover_letter_pdf(title, letter.content)
        media_type = "application/pdf"

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
