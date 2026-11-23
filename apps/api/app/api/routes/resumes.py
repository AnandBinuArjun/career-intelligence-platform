import hashlib
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.rate_limit import rate_limit
from app.models.entities import Resume, ResumeVersion, utcnow
from app.schemas import (
    ResumeCreateRequest,
    ResumeDetailResponse,
    ResumeSummaryResponse,
    ResumeUpdateRequest,
    ResumeUploadCompleteResponse,
    ResumeUploadRequest,
    ResumeUploadUrlResponse,
    ResumeVersionCreate,
    ResumeVersionResponse,
)
from app.services.documents.exporter import export_resume_docx, export_resume_pdf
from app.services.documents.parser import parse_resume_bytes
from app.services.documents.validation import safe_filename, validate_document, validate_extension
from app.services.storage.s3 import (
    create_upload_url,
    delete_object,
    put_validated_object,
    read_uploaded_object,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _reject_upload(db: Session, resume: Resume, object_key: str) -> None:
    delete_object(object_key)
    resume.upload_status = "rejected"
    resume.updated_at = utcnow()
    db.commit()


def _serialize_version(v: ResumeVersion) -> ResumeVersionResponse:
    return ResumeVersionResponse(
        id=str(v.id),
        resume_id=str(v.resume_id),
        version_number=v.version_number,
        content=v.content or {},
        source=v.source,
        created_at=v.created_at,
    )


def _serialize_resume_summary(db: Session, resume: Resume) -> ResumeSummaryResponse:
    latest = db.execute(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume.id)
        .order_by(ResumeVersion.version_number.desc())
        .limit(1)
    ).scalar_one_or_none()
    return ResumeSummaryResponse(
        id=str(resume.id),
        title=resume.title,
        file_type=resume.file_type,
        upload_status=resume.upload_status,
        parse_status=resume.parse_status,
        latest_version_id=str(latest.id) if latest else None,
        latest_version_number=latest.version_number if latest else 0,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


def _serialize_resume_detail(db: Session, resume: Resume) -> ResumeDetailResponse:
    versions = db.execute(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume.id)
        .order_by(ResumeVersion.version_number.desc())
    ).scalars().all()
    latest = versions[0] if versions else None
    return ResumeDetailResponse(
        id=str(resume.id),
        title=resume.title,
        file_type=resume.file_type,
        upload_status=resume.upload_status,
        parse_status=resume.parse_status,
        latest_version_id=str(latest.id) if latest else None,
        latest_version_number=latest.version_number if latest else 0,
        file_sha256=resume.file_sha256,
        parsed_content=resume.parsed_content or {},
        versions=[_serialize_version(v) for v in versions],
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


def _next_version_number(db: Session, resume_id: uuid.UUID) -> int:
    current_max = db.execute(
        select(func.coalesce(func.max(ResumeVersion.version_number), 0)).where(
            ResumeVersion.resume_id == resume_id
        )
    ).scalar_one()
    return int(current_max) + 1


@router.get("", response_model=list[ResumeSummaryResponse])
def list_resumes(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[ResumeSummaryResponse]:
    rows = db.execute(
        select(Resume).where(Resume.user_id == user_id).order_by(Resume.updated_at.desc())
    ).scalars().all()
    return [_serialize_resume_summary(db, r) for r in rows]


@router.post("", response_model=ResumeDetailResponse, status_code=status.HTTP_201_CREATED)
def create_resume(
    payload: ResumeCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    resume = Resume(
        user_id=user_id,
        title=payload.title.strip(),
        upload_status="uploaded",
        parse_status="completed" if payload.content else "pending",
        parsed_content=payload.content or {},
    )
    db.add(resume)
    db.flush()
    version = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        content=payload.content or {"full_name": "", "summary": "", "experiences": [], "education": [], "skills": [], "certifications": []},
        source=payload.source,
    )
    db.add(version)
    record_audit_event(db, user_id=user_id, action="resume.create", resource_type="resume", resource_id=resume.id)
    db.commit()
    db.refresh(resume)
    return _serialize_resume_detail(db, resume)


@router.post(
    "/upload-url",
    response_model=ResumeUploadUrlResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("resume_upload_url", limit=30, window_seconds=300))],
)
def create_resume_upload(
    payload: ResumeUploadRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResumeUploadUrlResponse:
    filename = safe_filename(payload.file_name)
    if payload.content_type not in settings.allowed_upload_type_list:
        raise HTTPException(status_code=415, detail="Unsupported content type")
    validate_extension(filename, payload.content_type)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if payload.size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")

    resume_id = uuid.uuid4()
    object_key = f"users/{user_id}/resumes/{resume_id}/{filename}"
    url = create_upload_url(object_key, payload.content_type)
    resume = Resume(
        id=resume_id,
        user_id=user_id,
        title=payload.title.strip(),
        original_file_key=object_key,
        file_type=payload.content_type,
        expected_size_bytes=payload.size_bytes,
        upload_status="awaiting_upload",
        parse_status="pending",
    )
    db.add(resume)
    db.commit()
    return ResumeUploadUrlResponse(
        resume_id=str(resume_id),
        upload_url=url,
        expires_in=settings.presigned_upload_ttl_seconds,
        required_headers={"Content-Type": payload.content_type},
    )


@router.post(
    "/upload",
    response_model=ResumeDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("resume_upload", limit=20, window_seconds=300))],
)
async def upload_and_parse_resume(
    title: str = Form(..., min_length=1, max_length=120),
    auto_parse: bool = Form(default=True),
    file: UploadFile = File(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    """Direct authenticated upload with identical validation, SHA-256 hashing, private storage, and optional parsing."""
    filename = safe_filename(file.filename or "resume.txt")
    content_type = file.content_type or "application/octet-stream"
    if content_type not in settings.allowed_upload_type_list:
        raise HTTPException(status_code=415, detail="Unsupported content type")
    validate_extension(filename, content_type)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if not data or len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File is empty or exceeds {settings.max_upload_mb} MB limit")

    validate_document(data, content_type)
    digest = hashlib.sha256(data).hexdigest()

    resume_id = uuid.uuid4()
    final_key = f"users/{user_id}/resumes/{resume_id}/original"
    put_validated_object(final_key, data, content_type)

    parsed_content: dict = {}
    parse_status = "pending"
    if auto_parse:
        try:
            parsed_content = parse_resume_bytes(data, content_type)
            parse_status = "completed"
        except Exception:
            parse_status = "failed"

    resume = Resume(
        id=resume_id,
        user_id=user_id,
        title=title.strip(),
        original_file_key=final_key,
        file_type=content_type,
        file_sha256=digest,
        expected_size_bytes=len(data),
        upload_status="uploaded",
        parse_status=parse_status,
        parsed_content=parsed_content,
    )
    db.add(resume)
    db.flush()

    if parse_status == "completed":
        db.add(
            ResumeVersion(
                resume_id=resume.id,
                version_number=1,
                content=parsed_content,
                source="imported",
            )
        )
    record_audit_event(
        db,
        user_id=user_id,
        action="resume.upload",
        resource_type="resume",
        resource_id=resume.id,
        metadata={"file_type": content_type, "parse_status": parse_status},
    )
    db.commit()
    db.refresh(resume)
    return _serialize_resume_detail(db, resume)


@router.post("/{resume_id}/complete", response_model=ResumeUploadCompleteResponse)
def complete_resume_upload(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResumeUploadCompleteResponse:
    resume = db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    if resume.upload_status == "uploaded":
        return ResumeUploadCompleteResponse(
            resume_id=str(resume_id),
            status="uploaded_pending_scan",
            message="Upload was already validated and is ready for scanning/parsing.",
        )
    if resume.upload_status != "awaiting_upload":
        raise HTTPException(
            status_code=409,
            detail=f"Upload cannot be completed from state '{resume.upload_status}'",
        )

    object_key = resume.original_file_key or ""
    try:
        data = read_uploaded_object(object_key)
    except Exception:
        raise HTTPException(status_code=400, detail="Uploaded object could not be retrieved") from None

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if not data or len(data) > max_bytes:
        _reject_upload(db, resume, object_key)
        raise HTTPException(status_code=413, detail="Uploaded file is empty or exceeds size limit")
    if resume.expected_size_bytes is not None and len(data) != resume.expected_size_bytes:
        _reject_upload(db, resume, object_key)
        raise HTTPException(status_code=400, detail="Uploaded file size does not match the declared size")
    try:
        validate_document(data, resume.file_type or "")
    except HTTPException:
        _reject_upload(db, resume, object_key)
        raise

    digest = hashlib.sha256(data).hexdigest()
    # Write the exact validated bytes to a new server-controlled key to prevent TOCTOU tampering.
    final_key = f"users/{user_id}/resumes/{resume_id}/original"
    put_validated_object(final_key, data, resume.file_type or "application/octet-stream")
    resume.original_file_key = final_key
    resume.file_sha256 = digest
    resume.upload_status = "uploaded"
    resume.parse_status = "pending"
    resume.updated_at = utcnow()
    db.commit()
    delete_object(object_key)
    return ResumeUploadCompleteResponse(
        resume_id=str(resume_id),
        status="uploaded_pending_scan",
        message="Upload validated and promoted to immutable private storage.",
    )


@router.post("/{resume_id}/parse", response_model=ResumeDetailResponse)
def parse_resume(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    resume = db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    if resume.upload_status != "uploaded" or not resume.original_file_key or not resume.file_type:
        raise HTTPException(status_code=400, detail="Resume has no validated uploaded file to parse")

    try:
        data = read_uploaded_object(resume.original_file_key)
        parsed = parse_resume_bytes(data, resume.file_type)
    except Exception:
        resume.parse_status = "failed"
        resume.updated_at = utcnow()
        db.commit()
        raise HTTPException(status_code=422, detail="Failed to extract content from uploaded document") from None

    resume.parsed_content = parsed
    resume.parse_status = "completed"
    resume.updated_at = utcnow()

    next_ver = _next_version_number(db, resume.id)
    db.add(
        ResumeVersion(
            resume_id=resume.id,
            version_number=next_ver,
            content=parsed,
            source="imported",
        )
    )
    db.commit()
    db.refresh(resume)
    return _serialize_resume_detail(db, resume)


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
def get_resume(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    resume = db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return _serialize_resume_detail(db, resume)


@router.put("/{resume_id}", response_model=ResumeDetailResponse)
def update_resume(
    resume_id: uuid.UUID,
    payload: ResumeUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    resume = db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    if payload.title is not None:
        resume.title = payload.title.strip()
    resume.updated_at = utcnow()
    db.commit()
    db.refresh(resume)
    return _serialize_resume_detail(db, resume)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    resume = db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    if resume.original_file_key:
        delete_object(resume.original_file_key)
    db.delete(resume)
    record_audit_event(db, user_id=user_id, action="resume.delete", resource_type="resume", resource_id=resume_id)
    db.commit()


@router.get("/{resume_id}/versions", response_model=list[ResumeVersionResponse])
def list_resume_versions(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[ResumeVersionResponse]:
    resume = db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    versions = db.execute(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume.id)
        .order_by(ResumeVersion.version_number.desc())
    ).scalars().all()
    return [_serialize_version(v) for v in versions]


@router.post("/{resume_id}/versions", response_model=ResumeVersionResponse, status_code=status.HTTP_201_CREATED)
def create_resume_version(
    resume_id: uuid.UUID,
    payload: ResumeVersionCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResumeVersionResponse:
    resume = db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    version = ResumeVersion(
        resume_id=resume.id,
        version_number=_next_version_number(db, resume.id),
        content=payload.content,
        source=payload.source,
    )
    resume.updated_at = utcnow()
    db.add(version)
    db.commit()
    db.refresh(version)
    return _serialize_version(version)


@router.post("/{resume_id}/versions/{version_id}/restore", response_model=ResumeVersionResponse, status_code=status.HTTP_201_CREATED)
def restore_resume_version(
    resume_id: uuid.UUID,
    version_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResumeVersionResponse:
    resume = db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    source_ver = db.execute(
        select(ResumeVersion).where(
            ResumeVersion.id == version_id, ResumeVersion.resume_id == resume.id
        )
    ).scalar_one_or_none()
    if source_ver is None:
        raise HTTPException(status_code=404, detail="Resume version not found")

    restored = ResumeVersion(
        resume_id=resume.id,
        version_number=_next_version_number(db, resume.id),
        content=dict(source_ver.content or {}),
        source="user",
    )
    resume.updated_at = utcnow()
    db.add(restored)
    db.commit()
    db.refresh(restored)
    return _serialize_version(restored)


@router.get("/{resume_id}/export")
def export_resume(
    resume_id: uuid.UUID,
    format: str = Query(default="pdf", pattern="^(pdf|docx)$"),
    template: str = Query(default="classic", pattern="^(classic|modern|compact)$"),
    version_id: uuid.UUID | None = Query(default=None),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Response:
    resume = db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    ).scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    if version_id is not None:
        version = db.execute(
            select(ResumeVersion).where(
                ResumeVersion.id == version_id, ResumeVersion.resume_id == resume.id
            )
        ).scalar_one_or_none()
        if version is None:
            raise HTTPException(status_code=404, detail="Resume version not found")
        content = version.content or {}
    else:
        latest = db.execute(
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == resume.id)
            .order_by(ResumeVersion.version_number.desc())
            .limit(1)
        ).scalar_one_or_none()
        content = (latest.content if latest else resume.parsed_content) or {}

    base_name = safe_filename(f"{resume.title}.{format}")
    if format == "docx":
        payload = export_resume_docx(resume.title, content)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        payload = export_resume_pdf(resume.title, content, template=template)
        media_type = "application/pdf"

    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{base_name}"'},
    )
