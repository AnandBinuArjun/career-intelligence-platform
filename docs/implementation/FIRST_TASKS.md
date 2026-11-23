# First implementation tasks

## Sprint 0 — local foundation
- [ ] Create public GitHub repository and add chosen open-source license.
- [ ] Protect `main`; require pull requests and CI checks.
- [ ] Create development, test and production environment templates.
- [ ] Add secret scanning, dependency scanning and code scanning.
- [ ] Build and run the web and API scaffold.
- [ ] Add health checks for PostgreSQL, Redis and object storage.
- [ ] Add CI for frontend lint/build and backend lint/type/test.

## Sprint 1 — identity and data isolation
- [ ] Implement registration, email verification, login, logout and refresh.
- [ ] Use Argon2id password hashing and secure HttpOnly cookies.
- [ ] Add CSRF protections where cookie-based auth is used.
- [ ] Implement authenticated-user context in API dependencies.
- [ ] Implement transaction-scoped `SET LOCAL app.user_id`.
- [ ] Add non-superuser runtime database role and test RLS.
- [ ] Add cross-user authorization regression tests.

## Sprint 2 — secure document ingestion
- [ ] Add signed upload URL flow for private object storage.
- [ ] Validate magic bytes, file size, page count and content type.
- [ ] Add malware scanning and quarantine.
- [ ] Run parsers in isolated worker containers with CPU/memory/time limits.
- [ ] Extract PDF/DOCX text and section structure.
- [ ] Store extraction confidence and source spans.
- [ ] Add retention and deletion workflows.

## Sprint 3 — job analysis and deterministic matching
- [ ] Parse job descriptions into required/preferred requirements.
- [ ] Create normalized skills taxonomy and synonym map.
- [ ] Implement exact and semantic matching separately.
- [ ] Implement versioned scoring configuration.
- [ ] Add evidence traceability to each match.
- [ ] Build report endpoint and frontend result view.

## Sprint 4 — controlled AI generation
- [ ] Implement provider gateway and Ollama adapter.
- [ ] Add external provider adapter behind explicit consent.
- [ ] Add prompt-injection test corpus.
- [ ] Validate model outputs with strict schemas.
- [ ] Add evidence validation and user approval workflow.
- [ ] Add cover letter generation and export tests.

## Definition of done
A task is complete only when code, tests, documentation, security implications and failure handling are included. Do not put real candidate documents into development fixtures.
