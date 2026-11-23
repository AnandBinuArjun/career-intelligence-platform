"""Redis-backed background worker for long-running document parsing & analysis tasks.

Run with:
    python -m app.workers.worker
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

import redis
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.dependencies import set_rls_user_context
from app.models.entities import Resume, ResumeVersion, utcnow
from app.services.documents.parser import parse_resume_bytes
from app.services.storage.s3 import read_uploaded_object

logger = logging.getLogger("career.worker")
QUEUE_KEY = "career:jobs:default"
MAX_RETRIES = 3


def enqueue_job(job_type: str, payload: dict[str, Any]) -> bool:
    """Push an idempotent job payload to Redis. Returns False if Redis is unavailable."""
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        envelope = {
            "job_id": str(uuid.uuid4()),
            "job_type": job_type,
            "payload": payload,
            "attempt": 1,
        }
        client.rpush(QUEUE_KEY, json.dumps(envelope))
        return True
    except Exception:
        logger.warning("Redis unavailable; caller should handle job inline or retry later.")
        return False


def process_job(envelope: dict[str, Any]) -> None:
    job_type = envelope.get("job_type")
    payload = envelope.get("payload") or {}
    if job_type == "parse_resume":
        user_id = uuid.UUID(payload["user_id"])
        resume_id = uuid.UUID(payload["resume_id"])
        with SessionLocal() as db:
            set_rls_user_context(db, user_id)
            resume = db.execute(
                select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
            ).scalar_one_or_none()
            if resume is None or not resume.original_file_key or not resume.file_type:
                return
            resume.parse_status = "processing"
            db.commit()
            try:
                raw_bytes = read_uploaded_object(resume.original_file_key)
                parsed = parse_resume_bytes(raw_bytes, resume.file_type)
                resume.parsed_content = parsed
                resume.parse_status = "completed"
                resume.updated_at = utcnow()
                existing_versions = db.execute(
                    select(ResumeVersion).where(ResumeVersion.resume_id == resume.id)
                ).scalars().all()
                db.add(
                    ResumeVersion(
                        resume_id=resume.id,
                        version_number=len(existing_versions) + 1,
                        content=parsed,
                        source="imported",
                    )
                )
                db.commit()
            except Exception:
                resume.parse_status = "failed"
                resume.updated_at = utcnow()
                db.commit()
                raise


def run_worker_loop() -> None:
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    client = redis.Redis.from_url(settings.redis_url)
    logger.info("Career Intelligence worker started on queue %s", QUEUE_KEY)
    while True:
        item: Any = client.blpop([QUEUE_KEY], timeout=5)
        if not item:
            continue
        _, raw_payload = item
        envelope = json.loads(raw_payload)
        try:
            process_job(envelope)
        except Exception:
            attempt = int(envelope.get("attempt", 1))
            if attempt < MAX_RETRIES:
                envelope["attempt"] = attempt + 1
                time.sleep(min(attempt * 2, 10))
                client.rpush(QUEUE_KEY, json.dumps(envelope))
            else:
                logger.error("Job %s failed permanently after %d attempts", envelope.get("job_id"), attempt)


if __name__ == "__main__":
    run_worker_loop()
