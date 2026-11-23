import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.rate_limit import rate_limit
from app.models.entities import (
    Analysis,
    JobDescription,
    Recommendation,
    Resume,
    ResumeVersion,
    Skill,
    utcnow,
)
from app.schemas import (
    AnalysisCreateRequest,
    AnalysisResponse,
    RecommendationResponse,
    RecommendationUpdateRequest,
)
from app.services.ai.gateway import generate_recommendations_via_gateway
from app.services.matching.job_parser import parse_job_description
from app.services.matching.scorer import SCORING_VERSION, evaluate_compatibility

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _serialize_rec(rec: Recommendation) -> RecommendationResponse:
    return RecommendationResponse(
        id=str(rec.id),
        analysis_id=str(rec.analysis_id),
        category=rec.category,
        original_text=rec.original_text,
        suggested_text=rec.suggested_text,
        rationale=rec.rationale,
        evidence_reference=rec.evidence_reference or {},
        requires_user_confirmation=rec.requires_user_confirmation,
        status=rec.status,
        created_at=rec.created_at,
    )


def _serialize_analysis(db: Session, analysis: Analysis) -> AnalysisResponse:
    recs = db.execute(
        select(Recommendation)
        .where(Recommendation.analysis_id == analysis.id)
        .order_by(Recommendation.created_at.asc())
    ).scalars().all()
    job = db.execute(select(JobDescription).where(JobDescription.id == analysis.job_description_id)).scalar_one_or_none()
    rv = db.execute(select(ResumeVersion).where(ResumeVersion.id == analysis.resume_version_id)).scalar_one_or_none()
    resume = (
        db.execute(select(Resume).where(Resume.id == rv.resume_id)).scalar_one_or_none()
        if rv is not None
        else None
    )

    return AnalysisResponse(
        id=str(analysis.id),
        resume_version_id=str(analysis.resume_version_id),
        job_description_id=str(analysis.job_description_id),
        job_title=job.job_title if job else None,
        company_name=job.company_name if job else None,
        resume_title=resume.title if resume else None,
        status=analysis.status,
        overall_score=float(analysis.overall_score) if analysis.overall_score is not None else None,
        scoring_data=analysis.scoring_data or {},
        weights_config=analysis.weights_config or {},
        model_metadata=analysis.model_metadata or {},
        scoring_version=analysis.scoring_version,
        methodology_note=analysis.methodology_note,
        failure_reason=analysis.failure_reason,
        recommendations=[_serialize_rec(r) for r in recs],
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )


def _parse_uuid(raw: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label} identifier") from None


@router.get("", response_model=list[AnalysisResponse])
def list_analyses(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[AnalysisResponse]:
    rows = db.execute(
        select(Analysis).where(Analysis.user_id == user_id).order_by(Analysis.created_at.desc())
    ).scalars().all()
    return [_serialize_analysis(db, row) for row in rows]


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("analyses_create", limit=30, window_seconds=300))],
)
async def create_analysis(
    payload: AnalysisCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    rv_id = _parse_uuid(payload.resume_version_id, "resume_version_id")
    jd_id = _parse_uuid(payload.job_description_id, "job_description_id")

    # Enforce strict ownership on both resume version and job description.
    rv_row = db.execute(
        select(ResumeVersion, Resume)
        .join(Resume, ResumeVersion.resume_id == Resume.id)
        .where(ResumeVersion.id == rv_id, Resume.user_id == user_id)
    ).one_or_none()
    if rv_row is None:
        raise HTTPException(status_code=404, detail="Resume version not found")
    resume_version, _resume = rv_row

    job = db.execute(
        select(JobDescription).where(JobDescription.id == jd_id, JobDescription.user_id == user_id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job description not found")

    job_reqs = job.extracted_requirements or parse_job_description(
        job.job_title, job.description, job.company_name
    )
    user_skills = [
        s.name
        for s in db.execute(select(Skill).where(Skill.user_id == user_id)).scalars().all()
    ]
    custom_weights = payload.weights.model_dump() if payload.weights else None

    scoring_result = evaluate_compatibility(
        resume_content=resume_version.content or {},
        job_requirements=job_reqs,
        job_description_text=job.description,
        weights=custom_weights,
        profile_context={"skills": user_skills},
    )

    recs_data, model_meta = await generate_recommendations_via_gateway(
        db,
        user_id=user_id,
        resume_content=resume_version.content or {},
        scoring_data=scoring_result,
        job_title=job.job_title,
        profile_data={"skills": user_skills},
        external_ai_consent_id=payload.external_ai_consent_id,
    )

    now = utcnow()
    analysis = Analysis(
        user_id=user_id,
        resume_version_id=resume_version.id,
        job_description_id=job.id,
        status="completed",
        overall_score=Decimal(str(scoring_result["overall_score"])),
        scoring_data=scoring_result,
        weights_config=scoring_result["weights_used"],
        model_metadata=model_meta,
        scoring_version=SCORING_VERSION,
        methodology_note=scoring_result["methodology_note"],
        completed_at=now,
    )
    db.add(analysis)
    db.flush()

    for rec_item in recs_data:
        db.add(
            Recommendation(
                analysis_id=analysis.id,
                category=rec_item["category"],
                original_text=rec_item.get("original_text"),
                suggested_text=rec_item.get("suggested_text"),
                rationale=rec_item.get("rationale"),
                evidence_reference=rec_item.get("evidence_reference") or {},
                requires_user_confirmation=bool(rec_item.get("requires_user_confirmation", False)),
                status="pending",
            )
        )

    record_audit_event(
        db,
        user_id=user_id,
        action="analysis.create",
        resource_type="analysis",
        resource_id=analysis.id,
        metadata={"scoring_version": SCORING_VERSION, "provider": model_meta.get("provider")},
    )
    db.commit()
    db.refresh(analysis)
    return _serialize_analysis(db, analysis)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    analysis = db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    ).scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _serialize_analysis(db, analysis)


@router.get("/{analysis_id}/recommendations", response_model=list[RecommendationResponse])
def list_recommendations(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[RecommendationResponse]:
    analysis = db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    ).scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    recs = db.execute(
        select(Recommendation).where(Recommendation.analysis_id == analysis.id)
    ).scalars().all()
    return [_serialize_rec(r) for r in recs]


@router.post("/{analysis_id}/optimize", response_model=AnalysisResponse)
async def regenerate_recommendations(
    analysis_id: uuid.UUID,
    external_ai_consent_id: str | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    analysis = db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    ).scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    rv = db.execute(select(ResumeVersion).where(ResumeVersion.id == analysis.resume_version_id)).scalar_one()
    job = db.execute(select(JobDescription).where(JobDescription.id == analysis.job_description_id)).scalar_one()
    user_skills = [
        s.name
        for s in db.execute(select(Skill).where(Skill.user_id == user_id)).scalars().all()
    ]

    recs_data, model_meta = await generate_recommendations_via_gateway(
        db,
        user_id=user_id,
        resume_content=rv.content or {},
        scoring_data=analysis.scoring_data or {},
        job_title=job.job_title,
        profile_data={"skills": user_skills},
        external_ai_consent_id=external_ai_consent_id,
    )

    existing = db.execute(
        select(Recommendation).where(Recommendation.analysis_id == analysis.id)
    ).scalars().all()
    for row in existing:
        db.delete(row)

    for rec_item in recs_data:
        db.add(
            Recommendation(
                analysis_id=analysis.id,
                category=rec_item["category"],
                original_text=rec_item.get("original_text"),
                suggested_text=rec_item.get("suggested_text"),
                rationale=rec_item.get("rationale"),
                evidence_reference=rec_item.get("evidence_reference") or {},
                requires_user_confirmation=bool(rec_item.get("requires_user_confirmation", False)),
                status="pending",
            )
        )
    analysis.model_metadata = model_meta
    db.commit()
    return _serialize_analysis(db, analysis)


@router.patch("/{analysis_id}/recommendations/{rec_id}", response_model=RecommendationResponse)
def update_recommendation_status(
    analysis_id: uuid.UUID,
    rec_id: uuid.UUID,
    payload: RecommendationUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    analysis = db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    ).scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    rec = db.execute(
        select(Recommendation).where(
            Recommendation.id == rec_id, Recommendation.analysis_id == analysis.id
        )
    ).scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.status = payload.status
    if payload.suggested_text is not None:
        rec.suggested_text = payload.suggested_text
    db.commit()
    db.refresh(rec)
    return _serialize_rec(rec)
