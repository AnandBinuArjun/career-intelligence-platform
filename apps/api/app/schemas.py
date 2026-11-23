from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=16, max_length=512)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    csrf_token: str | None = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr


# ---------------------------------------------------------------------------
# Candidate Profile (Verified Source of Truth)
# ---------------------------------------------------------------------------

class CandidateProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    professional_title: str | None = Field(default=None, max_length=160)
    summary: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=160)
    contact_data: dict[str, Any] = Field(default_factory=dict)
    target_roles: list[str] = Field(default_factory=list, max_length=20)
    years_experience: float | None = Field(default=None, ge=0, le=70)


class ExperienceCreate(BaseModel):
    employer: str | None = Field(default=None, max_length=200)
    job_title: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=160)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = Field(default=None, max_length=5000)
    achievements: list[str] = Field(default_factory=list, max_length=30)
    source_reference: dict[str, Any] = Field(default_factory=dict)


class ExperienceResponse(ExperienceCreate):
    id: str
    verified: bool = True


class EducationCreate(BaseModel):
    institution: str = Field(min_length=1, max_length=200)
    qualification: str | None = Field(default=None, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    source_reference: dict[str, Any] = Field(default_factory=dict)


class EducationResponse(EducationCreate):
    id: str


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    proficiency: str | None = Field(default=None, max_length=60)
    years_experience: float | None = Field(default=None, ge=0, le=60)
    evidence_reference: dict[str, Any] = Field(default_factory=dict)


class SkillResponse(SkillCreate):
    id: str


class CertificationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    credential_id: str | None = Field(default=None, max_length=120)
    issued_on: date | None = None
    expires_on: date | None = None
    evidence_reference: dict[str, Any] = Field(default_factory=dict)


class CertificationResponse(CertificationCreate):
    id: str


class FullProfileResponse(BaseModel):
    user_id: str
    email: EmailStr
    full_name: str | None = None
    professional_title: str | None = None
    summary: str | None = None
    location: str | None = None
    contact_data: dict[str, Any] = Field(default_factory=dict)
    target_roles: list[str] = Field(default_factory=list)
    years_experience: float | None = None
    experiences: list[ExperienceResponse] = Field(default_factory=list)
    education: list[EducationResponse] = Field(default_factory=list)
    skills: list[SkillResponse] = Field(default_factory=list)
    certifications: list[CertificationResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Resumes & Versions
# ---------------------------------------------------------------------------

class ResumeUploadRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str
    size_bytes: int = Field(gt=0)


class ResumeUploadUrlResponse(BaseModel):
    resume_id: str
    upload_url: str
    method: str = "PUT"
    expires_in: int
    required_headers: dict[str, str]


class ResumeUploadCompleteResponse(BaseModel):
    resume_id: str
    status: str
    message: str


class ResumeCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: dict[str, Any] = Field(default_factory=dict)
    source: Literal["user", "optimized", "imported"] = "user"


class ResumeUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)


class ResumeVersionCreate(BaseModel):
    content: dict[str, Any]
    source: Literal["user", "optimized", "imported"] = "user"


class ResumeVersionResponse(BaseModel):
    id: str
    resume_id: str
    version_number: int
    content: dict[str, Any]
    source: str
    created_at: datetime


class ResumeSummaryResponse(BaseModel):
    id: str
    title: str
    file_type: str | None = None
    upload_status: str
    parse_status: str
    latest_version_id: str | None = None
    latest_version_number: int = 0
    created_at: datetime
    updated_at: datetime


class ResumeDetailResponse(ResumeSummaryResponse):
    file_sha256: str | None = None
    parsed_content: dict[str, Any] = Field(default_factory=dict)
    versions: list[ResumeVersionResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Job Intelligence
# ---------------------------------------------------------------------------

class JobCreateRequest(BaseModel):
    company_name: str | None = Field(default=None, max_length=200)
    job_title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=20, max_length=50000)


class JobUpdateRequest(BaseModel):
    company_name: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=20, max_length=50000)
    extracted_requirements: dict[str, Any] | None = None


class JobResponse(BaseModel):
    id: str
    company_name: str | None = None
    job_title: str
    description: str
    extracted_requirements: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# ---------------------------------------------------------------------------
# ATS Compatibility Analysis & Recommendations
# ---------------------------------------------------------------------------

class ScoringWeights(BaseModel):
    skills_relevance: float = Field(default=0.30, ge=0.0, le=1.0)
    experience_relevance: float = Field(default=0.25, ge=0.0, le=1.0)
    keyword_coverage: float = Field(default=0.15, ge=0.0, le=1.0)
    education_certification: float = Field(default=0.10, ge=0.0, le=1.0)
    achievement_evidence: float = Field(default=0.10, ge=0.0, le=1.0)
    document_readability: float = Field(default=0.10, ge=0.0, le=1.0)


class AnalysisCreateRequest(BaseModel):
    resume_version_id: str
    job_description_id: str
    weights: ScoringWeights | None = None
    external_ai_consent_id: str | None = None


class RecommendationResponse(BaseModel):
    id: str
    analysis_id: str
    category: str
    original_text: str | None = None
    suggested_text: str | None = None
    rationale: str | None = None
    evidence_reference: dict[str, Any] = Field(default_factory=dict)
    requires_user_confirmation: bool = False
    status: str
    created_at: datetime


class RecommendationUpdateRequest(BaseModel):
    status: Literal["pending", "accepted", "rejected", "edited"]
    suggested_text: str | None = Field(default=None, max_length=4000)


class AnalysisResponse(BaseModel):
    id: str
    resume_version_id: str
    job_description_id: str
    job_title: str | None = None
    company_name: str | None = None
    resume_title: str | None = None
    status: str
    overall_score: float | None = None
    scoring_data: dict[str, Any] = Field(default_factory=dict)
    weights_config: dict[str, Any] = Field(default_factory=dict)
    model_metadata: dict[str, Any] = Field(default_factory=dict)
    scoring_version: str
    methodology_note: str | None = None
    failure_reason: str | None = None
    recommendations: list[RecommendationResponse] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Cover Letters
# ---------------------------------------------------------------------------

class CoverLetterCreateRequest(BaseModel):
    job_description_id: str
    resume_version_id: str
    tone: Literal["professional", "concise", "formal", "executive"] = "professional"
    length: Literal["short", "medium", "detailed"] = "medium"
    custom_notes: str | None = Field(default=None, max_length=1500)
    external_ai_consent_id: str | None = None


class CoverLetterUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    tone: Literal["professional", "concise", "formal", "executive"] | None = None
    content: str = Field(min_length=20, max_length=20000)


class CoverLetterResponse(BaseModel):
    id: str
    job_description_id: str | None = None
    resume_version_id: str | None = None
    title: str | None = None
    tone: str
    content: str
    evidence_references: list[dict[str, Any]] = Field(default_factory=list)
    model_metadata: dict[str, Any] = Field(default_factory=dict)
    version: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Application Tracker & Interviews
# ---------------------------------------------------------------------------

ApplicationStatus = Literal[
    "draft",
    "ready",
    "applied",
    "screening",
    "interview",
    "assessment",
    "offer",
    "rejected",
    "withdrawn",
]


class ApplicationCreateRequest(BaseModel):
    company_name: str | None = Field(default=None, max_length=200)
    position: str = Field(min_length=1, max_length=200)
    job_description_id: str | None = None
    resume_version_id: str | None = None
    status: ApplicationStatus = "draft"
    applied_at: datetime | None = None
    follow_up_at: datetime | None = None
    salary_range: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=5000)


class ApplicationUpdateRequest(BaseModel):
    company_name: str | None = Field(default=None, max_length=200)
    position: str | None = Field(default=None, min_length=1, max_length=200)
    job_description_id: str | None = None
    resume_version_id: str | None = None
    status: ApplicationStatus | None = None
    applied_at: datetime | None = None
    follow_up_at: datetime | None = None
    salary_range: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=5000)


class InterviewCreateRequest(BaseModel):
    scheduled_at: datetime | None = None
    interview_type: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=5000)
    outcome: str | None = Field(default=None, max_length=120)


class InterviewResponse(InterviewCreateRequest):
    id: str
    application_id: str
    created_at: datetime


class ApplicationResponse(BaseModel):
    id: str
    company_name: str | None = None
    position: str
    job_description_id: str | None = None
    resume_version_id: str | None = None
    status: str
    applied_at: datetime | None = None
    follow_up_at: datetime | None = None
    salary_range: str | None = None
    location: str | None = None
    notes: str | None = None
    interviews: list[InterviewResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Career Development
# ---------------------------------------------------------------------------

class InterviewPrepRequest(BaseModel):
    job_description_id: str | None = None
    resume_version_id: str | None = None
    focus_role: str | None = Field(default=None, max_length=200)


class CareerOverviewResponse(BaseModel):
    target_roles: list[str]
    verified_skills_count: int
    analyzed_jobs_count: int
    top_skill_gaps: list[dict[str, Any]]
    learning_plan: list[dict[str, Any]]
    interview_questions: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Privacy, Consent & Dashboard
# ---------------------------------------------------------------------------

class ConsentCreateRequest(BaseModel):
    purpose: str = Field(min_length=3, max_length=120)
    provider: str | None = Field(default=None, max_length=120)
    policy_version: str = Field(default="1.0", max_length=40)
    granted: bool


class ConsentResponse(BaseModel):
    id: str
    purpose: str
    provider: str | None = None
    policy_version: str
    granted: bool
    recorded_at: datetime
    withdrawn_at: datetime | None = None


class PrivacySettingsUpdate(BaseModel):
    retention_days: int = Field(ge=7, le=3650)
    ai_routing_preference: Literal["local", "external_with_consent"]


class PrivacySettingsResponse(BaseModel):
    retention_days: int
    ai_routing_preference: str
    external_ai_server_enabled: bool
    active_provider: str
    updated_at: datetime


class AuditLogResponse(BaseModel):
    id: str
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DashboardSummaryResponse(BaseModel):
    profile_completeness_pct: int
    resumes_count: int
    jobs_count: int
    analyses_count: int
    cover_letters_count: int
    active_applications_count: int
    upcoming_interviews_count: int
    application_pipeline: dict[str, int]
    recent_analyses: list[dict[str, Any]]
    ai_routing_status: dict[str, Any]
