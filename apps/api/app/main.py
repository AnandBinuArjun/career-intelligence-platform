import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analyses import router as analyses_router
from app.api.routes.applications import router as applications_router
from app.api.routes.auth import router as auth_router
from app.api.routes.career import router as career_router
from app.api.routes.cover_letters import router as cover_letters_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.privacy import router as privacy_router
from app.api.routes.profile import router as profile_router
from app.api.routes.resumes import router as resumes_router
from app.core.config import settings
from app.core.database import engine
from app.models.entities import Base


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Only auto-create schema for SQLite local development/tests.
    # PostgreSQL migrations MUST be applied explicitly via apps/api/migrations/.
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Free, privacy-first ATS optimization and career intelligence API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
)


@app.middleware("http")
async def security_and_request_id_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers.setdefault("Cache-Control", "no-store")
    return response


API_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(profile_router, prefix=API_PREFIX)
app.include_router(resumes_router, prefix=API_PREFIX)
app.include_router(jobs_router, prefix=API_PREFIX)
app.include_router(analyses_router, prefix=API_PREFIX)
app.include_router(cover_letters_router, prefix=API_PREFIX)
app.include_router(applications_router, prefix=API_PREFIX)
app.include_router(career_router, prefix=API_PREFIX)
app.include_router(privacy_router, prefix=API_PREFIX)


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }
