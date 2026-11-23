# Contributing to CareerIntel

Thank you for your interest in contributing to **CareerIntel (ATS Optimization & Career Intelligence Platform)**! We welcome bug reports, documentation improvements, test additions, accessibility enhancements, and feature contributions.

## Non-Negotiable Product & Engineering Rules

Before making changes, please review [agent.md](agent.md), [prd.md](prd.md), [architecture.md](architecture.md), and [docs/security/THREAT_MODEL.md](docs/security/THREAT_MODEL.md). Every contribution must uphold these rules:

1. **No fabricated candidate facts:** Never generate or silently insert unverified skills, employers, dates, degrees, or metrics into a candidate's profile or resume.
2. **No deceptive ATS claims:** Keep deterministic scoring (`apps/api/app/services/matching/`) separate from generative AI, and never describe platform compatibility estimates as an official ATS vendor score.
3. **Privacy-first defaults:** External AI providers must remain disabled by default and strictly gated behind explicit recorded consent.
4. **Never log sensitive data:** Do not log CV contents, cover letters, credentials, API keys, or access tokens.
5. **Defense-in-depth authorization:** Scope every query by the authenticated `user_id` and maintain PostgreSQL Row-Level Security policies for any new tables.
6. **Versioned SQL migrations:** Add a new sequentially numbered migration under `apps/api/migrations/` for schema changes. Never edit an already-applied migration.
7. **No real candidate data in commits:** Use synthetic, anonymized fixtures for tests and documentation.

---

## Local Development Setup

### Backend (`apps/api`)

```bash
cd apps/api
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows:     .venv\Scripts\activate
pip install -e ".[dev]"
```

Run checks:

```bash
ruff check app tests
mypy app
pytest -v
```

### Frontend (`apps/web`)

```bash
cd apps/web
npm install
```

Run checks:

```bash
npm run lint
npx tsc --noEmit
npm run build
```

---

## Pull Request Workflow

1. Fork the repository and create a feature branch from `main` (e.g., `feat/docx-table-parser` or `fix/rls-cascade`).
2. Follow **Conventional Commits** (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `security:`).
3. Keep pull requests focused and scoped to a single concern.
4. Add or update automated tests covering:
   - Normal behavior
   - Invalid/edge-case input
   - Authorization boundaries (cross-user isolation) where applicable
5. Update `docs/api/openapi.yaml` and user-facing documentation if an API contract or behavior changes.
6. Ensure all CI checks (`ruff`, `mypy`, `pytest`, `eslint`, `next build`) pass before requesting review.

---

## Code of Conduct

All participants are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
