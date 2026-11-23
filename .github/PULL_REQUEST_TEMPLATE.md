## Summary

<!-- Briefly describe what this PR changes and why. -->

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Security or privacy hardening
- [ ] Documentation / configuration update
- [ ] Database migration (new SQL file under `apps/api/migrations/`)

## Security & Product Integrity Checklist

- [ ] No fabricated candidate facts or silent mutations of verified profile data
- [ ] Deterministic scoring remains separate from generative AI
- [ ] All user-owned queries are scoped by authenticated `user_id` (and RLS updated for any new tables)
- [ ] No raw CV text, cover letters, credentials, or secrets are logged or committed
- [ ] No real personal documents were added to test fixtures

## Verification

- [ ] Backend: `ruff check app tests`, `mypy app`, `pytest -v`
- [ ] Frontend: `npm run lint`, `npx tsc --noEmit`, `npm run build`
- [ ] Updated `docs/api/openapi.yaml` and docs if contracts changed
