# Changelog

All notable changes to **CareerIntel (ATS Optimization & Career Intelligence Platform)** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-23

### Added
- **Authentication & Session Security:** Registration, login with Argon2id + timing-attack mitigation, JWT access tokens, rotating refresh tokens, logout revocation, and `HttpOnly` cookies with double-submit CSRF protection.
- **Database Schema & Isolation:** Ordered PostgreSQL migrations (`0001`–`0004`), Row-Level Security (RLS) across all user and child tables, restricted `career_app` runtime role, and SQLAlchemy 2.0 ORM models with zero-Docker SQLite local dev/test support.
- **Verified Candidate Profile & Dashboard:** Full CRUD for candidate summary, experiences, education, skills, certifications, and `/api/v1/dashboard/summary`.
- **Resume Intelligence:** Private S3/MinIO + local private storage uploads, PDF/DOCX/TXT signature & zip-bomb validation, structured section & ATS readability parser with source spans, immutable version history + snapshot restore, and clean watermark-free single-column PDF/DOCX exports.
- **Job Intelligence:** Job-description CRUD and deterministic extraction separating required vs. preferred skills, certifications, education, and responsibilities, with user-editable requirements.
- **ATS Compatibility Engine (`v1.0`):** Reproducible deterministic 8-dimension scoring engine with configurable weights, mandatory-qualification penalty cap, requirement-by-requirement evidence matrix, and explicit platform-estimate methodology disclaimers.
- **Hybrid AI Gateway & Evidence Validator:** Local Ollama default adapter, strictly consent-gated external OpenAI-compatible adapter, deterministic evidence-backed fallback, anti-hallucination claim validator (`requires_user_confirmation`), and Optimization Review accept/edit/reject workflow.
- **Cover Letter Studio:** Grounded cover-letter generation with tone/length controls, evidence citations panel, versioned editing, and PDF/DOCX/TXT export.
- **Career Development:** Aggregated skill-gap prioritization, verifiable learning roadmaps, and evidence-grounded STAR interview prep generator.
- **Application Tracker:** 9-status Kanban board & list view plus interview records logging.
- **Privacy & GDPR Controls:** Consent grant/withdrawal history, configurable retention settings, PII-scrubbed security audit logs, portable JSON data export (`/api/v1/account/export`), and cascading account + private file deletion (`/api/v1/account`).
- **Next.js 16 Frontend:** Complete accessible, responsive 8-module dark graphite & electric blue web application.
- **Background Worker & DevOps:** Redis job worker (`apps/api/app/workers/worker.py`), updated `docker-compose.yml`, hardened non-root API Dockerfile, updated CI (`ruff`, `mypy`, `pytest`, `eslint`, `next build`), OpenAPI 3.1 contract, and MIT License.
