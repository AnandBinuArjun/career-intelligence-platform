from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import AuditLog

# Keys that must never be stored in audit metadata to avoid leaking PII or secrets.
_FORBIDDEN_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "raw_text",
    "cv_text",
    "cover_letter",
    "content",
    "description",
    "api_key",
}


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        if key.lower() in _FORBIDDEN_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean[key] = value
        elif isinstance(value, list):
            clean[key] = [v for v in value[:20] if isinstance(v, (str, int, float, bool))]
    return clean


def record_audit_event(
    db: Session,
    *,
    user_id: UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=sanitize_metadata(metadata),
    )
    db.add(entry)
