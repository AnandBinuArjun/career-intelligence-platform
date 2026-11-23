import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.config import settings
from app.core.database import get_db, is_postgresql
from app.core.dependencies import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    get_current_user_id,
    set_rls_user_context,
)
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_access_token,
    dummy_verify_password,
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.entities import CandidateProfile, PrivacySettings, RefreshToken, User
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])

REFRESH_COOKIE_NAME = "career_refresh_token"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_ttl_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 86400,
        path="/api/v1/auth",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 86400,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth_register", limit=15, window_seconds=300))],
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    email = str(payload.email).strip().lower()
    user_id = uuid.uuid4()
    pw_hash = hash_password(payload.password)

    try:
        # Set transaction-local RLS identity to server-generated UUID so INSERT ... RETURNING
        # and initial profile/privacy rows see only the newly created account.
        set_rls_user_context(db, user_id)
        if is_postgresql(db):
            result = db.execute(
                text(
                    "INSERT INTO users (id, email, password_hash) "
                    "VALUES (:id, :email, :password_hash) RETURNING id, email"
                ),
                {"id": user_id, "email": email, "password_hash": pw_hash},
            ).mappings().one()
            created_id = result["id"]
            created_email = result["email"]
        else:
            user = User(id=user_id, email=email, password_hash=pw_hash)
            db.add(user)
            db.flush()
            created_id = user.id
            created_email = user.email

        db.add(CandidateProfile(user_id=created_id, full_name=payload.full_name))
        db.add(PrivacySettings(user_id=created_id))
        record_audit_event(db, user_id=created_id, action="auth.register", resource_type="user", resource_id=created_id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None

    return UserResponse(id=str(created_id), email=created_email)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_login", limit=20, window_seconds=300))],
)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    email = str(payload.email).strip().lower()

    if is_postgresql(db):
        user_row = db.execute(
            text("SELECT id, password_hash, is_active FROM public.auth_lookup_user(:email)"),
            {"email": email},
        ).mappings().one_or_none()
        user_id = user_row["id"] if user_row else None
        password_hash = user_row["password_hash"] if user_row else None
        is_active = bool(user_row["is_active"]) if user_row else False
    else:
        user_obj = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        user_id = user_obj.id if user_obj else None
        password_hash = user_obj.password_hash if user_obj else None
        is_active = bool(user_obj.is_active) if user_obj else False

    if user_id is None or not password_hash:
        dummy_verify_password(payload.password)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not is_active or not verify_password(payload.password, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    set_rls_user_context(db, user_id)
    access_token = create_access_token(user_id)
    raw_refresh, refresh_hash, expires_at = generate_refresh_token()
    csrf_token = generate_csrf_token()

    db.add(RefreshToken(user_id=user_id, token_hash=refresh_hash, expires_at=expires_at))
    record_audit_event(db, user_id=user_id, action="auth.login", resource_type="user", resource_id=user_id)
    db.commit()

    _set_auth_cookies(response, access_token, raw_refresh, csrf_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_ttl_minutes * 60,
        csrf_token=csrf_token,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_refresh", limit=30, window_seconds=300))],
)
def refresh_session(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> TokenResponse:
    raw_token = (payload.refresh_token if payload and payload.refresh_token else None) or request.cookies.get(
        REFRESH_COOKIE_NAME
    )
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")

    token_hash = hash_refresh_token(raw_token)
    # Note: on PostgreSQL production with RLS on refresh_tokens, rotating via bearer/session lookup
    # should use a SECURITY DEFINER helper if unauthenticated; this supports both local & authenticated flows.
    stored = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if stored is None or stored.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    exp = stored.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    if exp <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user_id = stored.user_id
    set_rls_user_context(db, user_id)

    # Rotate refresh token on use.
    stored.revoked_at = now
    new_access = create_access_token(user_id)
    new_raw_refresh, new_hash, new_exp = generate_refresh_token()
    csrf_token = generate_csrf_token()
    db.add(RefreshToken(user_id=user_id, token_hash=new_hash, expires_at=new_exp))
    db.commit()

    _set_auth_cookies(response, new_access, new_raw_refresh, csrf_token)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_raw_refresh,
        expires_in=settings.access_token_ttl_minutes * 60,
        csrf_token=csrf_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh:
        token_hash = hash_refresh_token(raw_refresh)
        stored = db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash, RefreshToken.user_id == user_id
            )
        ).scalar_one_or_none()
        if stored is not None:
            stored.revoked_at = datetime.now(UTC)
    record_audit_event(db, user_id=user_id, action="auth.logout", resource_type="user", resource_id=user_id)
    db.commit()
    _clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
def me(user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)) -> UserResponse:
    if is_postgresql(db):
        row = db.execute(
            text("SELECT id, email FROM users WHERE id = :id"), {"id": user_id}
        ).mappings().one()
        return UserResponse(id=str(row["id"]), email=row["email"])
    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    return UserResponse(id=str(user.id), email=user.email)
