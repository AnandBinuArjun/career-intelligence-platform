# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| `1.0.x` (main) | Yes |

## Reporting a Vulnerability

Because CareerIntel handles sensitive personal documents (CVs, employment history, contact details, cover letters), we take security vulnerabilities seriously.

**Please do NOT report security vulnerabilities in public GitHub issues.**

Instead, please report them privately using one of the following methods:
1. **GitHub Private Vulnerability Reporting** via the repository's **Security → Advisories → Report a vulnerability** tab.
2. Direct private contact with the repository maintainer: [Anand B Arjun (@AnandBinuArjun)](https://github.com/AnandBinuArjun) · [abarjun.online](https://abarjun.online).

Please include:
- A clear description of the vulnerability and affected component/endpoint
- Steps to reproduce or proof-of-concept (using synthetic test data only — never real candidate CVs)
- Potential impact and any suggested remediation

### Response Targets
- **Acknowledgement:** Within 48 hours
- **Initial triage & severity assessment:** Within 5 business days
- **Fix & coordinated disclosure:** Prioritized based on severity

---

## Built-In Security Controls

- **Authentication:** Argon2id password hashing, constant-time timing mitigation on login, short-lived JWT access tokens, rotating refresh tokens, and `HttpOnly` cookies with double-submit CSRF protection.
- **Database Isolation:** Ownership filtering in API queries plus PostgreSQL Row-Level Security (`SET LOCAL app.user_id`) under a restricted `career_app` runtime role (`NOSUPERUSER`, `NOBYPASSRLS`) and a `SECURITY DEFINER` login lookup function.
- **File Upload Safety:** MIME & extension allowlisting, PDF signature checks, DOCX archive & zip-bomb uncompressed size limits, SHA-256 hashing, and TOCTOU-safe promotion to immutable private storage keys.
- **AI Safety:** Untrusted-data prompt framing, strict Pydantic output validation, anti-hallucination evidence checks, and explicit consent gating (`403` when external AI consent is absent).
- **HTTP Hardening:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Cache-Control: no-store` on API responses, and `X-Request-ID` tracing.

## Pre-Launch Production Checklist

Before deploying a publicly accessible hosted instance with real user CVs, operators must also complete the release gates documented in [docs/security/THREAT_MODEL.md](docs/security/THREAT_MODEL.md):

- [ ] Replace all secrets in `.env` (`JWT_SECRET_KEY`, DB passwords, S3 keys) via a secret manager
- [ ] Enable HTTPS/TLS termination and `COOKIE_SECURE=true`
- [ ] Configure S3/object storage encryption at rest (SSE-KMS/SSE-S3) and block all public access
- [ ] Add antivirus/malware scanning (e.g., ClamAV) and sandboxed document/OCR workers
- [ ] Enable email verification, password reset, and distributed Redis-backed rate limiting
- [ ] Configure encrypted PostgreSQL backups and verify restore drills
- [ ] Complete a UK GDPR / data-protection impact assessment (DPIA) and publish a privacy notice
