# Initial threat model

## Assets
- CVs, cover letters, job application history
- Contact information, employment and education history
- Authentication credentials and session tokens
- AI provider credentials
- Analysis outputs and audit records

## Trust boundaries
- Browser to API
- API to database
- API/worker to object storage
- Worker to document parsers/OCR
- AI gateway to local or external model providers

## Threats and controls
| Threat | Required controls |
|---|---|
| Cross-user object access / BOLA | Ownership checks on every object; PostgreSQL RLS; authorization tests |
| Malicious documents | File signature validation, size/page limits, malware scanning, parser isolation |
| Prompt injection in CV/JD | Treat contents as untrusted data; no tool execution from document text |
| External provider data leakage | External AI disabled by default; explicit consent; provider disclosure |
| Hallucinated candidate facts | Evidence references; user confirmation; no silent profile mutation |
| SSRF | Do not fetch arbitrary user-supplied URLs; strict egress controls |
| XSS | Output encoding, sanitization and restrictive CSP |
| API abuse | Rate limits, quotas, request size limits |
| Secret exposure | Secret manager, rotation, no secrets in logs or client bundles |
| Data retention failure | Defined retention schedules and verified deletion workflows |

## Production release gates
- Runtime DB role is not superuser and does not have BYPASSRLS.
- RLS policies are enabled and tested using separate users.
- Uploads are private and scanned before processing.
- Backups are encrypted and restore-tested.
- Account deletion removes database records and associated objects according to the retention policy.
- Security headers, TLS, rate limiting and monitoring are enabled.
- A privacy impact assessment screening and privacy notice are completed.


## Implemented controls in the current milestone
- Passwords are hashed with Argon2id; bearer access tokens expire after 15 minutes.
- PostgreSQL runtime role is provisioned as `NOSUPERUSER` and `NOBYPASSRLS`.
- `users` has row-level self-select policy; the runtime role cannot directly select password hashes. Login uses a restricted `SECURITY DEFINER` function with a fixed search path.
- Uploads use short-lived presigned PUT URLs to a private bucket, with allowed media types, filename extension checks, expected-size checks, format checks and SHA-256 integrity metadata. Production bucket encryption at rest must be configured and verified separately; local MinIO is development-only.
- Validated bytes are promoted to a separate server-controlled storage key; the mutable staging key is deleted after commit.

## Remaining release blockers
- Email verification, password reset, session refresh/revocation and login rate limiting.
- Malware scanning and parser sandboxing before any document extraction.
- Browser authentication via secure HttpOnly cookies and CSRF protection, or a carefully reviewed token-storage strategy.
- Storage encryption and lifecycle policies validated in the target cloud provider.
- Full integration tests against PostgreSQL using the actual restricted runtime role and two distinct users.
