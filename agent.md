# Agent Engineering Guide

This file defines how coding agents and contributors must work in this repository.

## Mission

Build a free, privacy-first career intelligence platform that analyzes resume/job-description fit, improves document quality and supports career development. Do not market the product as an ATS bypass or guarantee a hiring outcome.

## Non-negotiable product rules

1. Never invent qualifications, employers, dates, certifications, achievements, metrics or skills.
2. Every AI-generated factual resume claim must reference candidate-provided evidence or be explicitly marked for user confirmation.
3. Never mutate the verified candidate profile from model output without user approval.
4. Explain the matching methodology. Do not claim to calculate a proprietary ATS vendor score.
5. External AI processing of personal documents is disabled by default and requires recorded, purpose-specific consent.
6. Never log raw resumes, cover letters, credentials, tokens or sensitive profile fields.
7. Treat uploaded documents and job descriptions as untrusted data, including prompt-injection attempts.

## Repository conventions

- Frontend: Next.js App Router, TypeScript, accessible semantic HTML and Tailwind.
- Backend: Python 3.12+, FastAPI, SQLAlchemy and PostgreSQL.
- Database migrations: ordered SQL files under `apps/api/migrations/`.
- API routes: `apps/api/app/api/routes/`.
- Business logic: `apps/api/app/services/`.
- Provider integrations: isolated adapters behind interfaces.
- Tests: colocated or under `apps/api/tests/` and frontend test folders.
- Keep the initial backend as a modular monolith. Do not introduce microservices without a documented operational need.

## Coding workflow

1. Read `prd.md`, `architecture.md`, `design.md` and relevant threat-model sections before changing behavior.
2. Inspect existing code and migrations; do not assume files or APIs exist.
3. Write or update tests with each behavior change.
4. Keep changes small and scoped. Avoid unrelated refactors.
5. Add a migration for schema changes; never edit an already-applied migration.
6. Update OpenAPI and docs when an API contract changes.
7. Run formatting, linting, type checks and tests where available.
8. Report what was implemented, what was tested, what was not tested and remaining risks.

## Security rules

- All user-owned data queries must be scoped by authenticated user identity.
- PostgreSQL RLS is defense in depth, not a replacement for application authorization.
- Runtime DB credentials must be non-superuser and must not have `BYPASSRLS`.
- Set transaction-local `app.user_id` only from the verified access token, never from request input.
- Validate upload extension, declared media type, actual file signature, size and archive structure.
- Store uploaded files in private object storage with random object identifiers and short-lived signed URLs.
- Scan files before parsing. Run parsers/OCR in isolated workers with CPU, memory, file-size and time limits.
- Never fetch arbitrary URLs supplied in resumes or job descriptions; prevent SSRF.
- Use parameterized SQL. Never concatenate user input into SQL.
- Do not expose secrets to the browser bundle.
- Add rate limiting to registration, login, upload URL issuance and expensive AI endpoints before public launch.

## AI implementation rules

- Separate extraction, deterministic scoring and text generation.
- Validate model output against strict Pydantic schemas.
- Treat model output as untrusted until validated.
- Record provider, model identifier, prompt version, schema version and scoring version (without recording private prompt payloads containing CV data).
- Make AI tasks idempotent and retry-bounded.
- Keep deterministic scoring reproducible for the same inputs and scoring version.
- Use evidence spans/source IDs for each requirement match and each proposed candidate claim.
- If evidence is absent or ambiguous, say so; do not fill the gap with plausible content.

## Definition of done

A change is done only when:
- Acceptance criteria are met.
- Tests cover normal, invalid and authorization-boundary cases.
- Failure states and retries are considered.
- API docs and user-facing copy are updated.
- No secrets or real candidate data are committed.
- Security and privacy impact has been reviewed.
- The final response clearly distinguishes completed work from future work.
