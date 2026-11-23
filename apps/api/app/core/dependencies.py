from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db, is_postgresql
from app.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

ACCESS_COOKIE_NAME = "career_access_token"
CSRF_COOKIE_NAME = "career_csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def set_rls_user_context(db: Session, user_id: UUID) -> None:
    """Set transaction-local app.user_id on PostgreSQL for Row-Level Security."""
    if is_postgresql(db):
        db.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": str(user_id)},
        )


def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UUID:
    token: str | None = None
    using_cookie = False

    if credentials is not None:
        token = credentials.credentials
    else:
        cookie_token = request.cookies.get(ACCESS_COOKIE_NAME)
        if cookie_token:
            token = cookie_token
            using_cookie = True

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Double-submit CSRF check when authenticating via browser cookies on state-changing requests.
    if using_cookie and request.method.upper() not in _SAFE_METHODS:
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        csrf_header = request.headers.get(CSRF_HEADER_NAME)
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF verification failed",
            )

    try:
        user_id = decode_access_token(token)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from None

    # Transaction-local value used by PostgreSQL RLS policies. Never accept this from a client.
    set_rls_user_context(db, user_id)

    exists = db.execute(
        text("SELECT id FROM users WHERE id = :user_id AND is_active = TRUE"),
        {"user_id": str(user_id) if not is_postgresql(db) else user_id},
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is unavailable",
        )
    return user_id
