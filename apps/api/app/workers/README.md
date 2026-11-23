# Background workers

Long-running parsing, OCR, AI analysis and document export must run outside request handlers.

Recommended next step: add a Celery or Dramatiq worker backed by Redis. Persist job state in PostgreSQL, make tasks idempotent, enforce per-user quotas, and support cancellation and retry limits.
