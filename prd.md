# Product Requirements Document (PRD)

## 1. Product summary

**Product:** ATS Optimization & Career Intelligence Platform  
**Short name:** CareerIntel  
**Owner:** Personal project  
**Business model:** Free; no paid feature tiers  
**Deployment:** Hybrid hosted and self-hosted  
**AI:** Hybrid local and external providers, with external processing disabled by default  
**Interface:** Dark graphite and electric-blue design

CareerIntel helps job seekers understand a job description, assess how well their existing evidence aligns with its requirements, improve resume clarity and relevance, generate grounded cover letters, and manage applications.

It does not guarantee ATS passage, promise to bypass hiring systems, or claim to reproduce proprietary vendor scoring algorithms.

## 2. Problem statement

Candidates often submit generic resumes that do not clearly demonstrate the requirements of a specific role. Existing tools may provide opaque scores or generate persuasive but inaccurate claims. Candidates also lack one place to manage resume versions, job-specific analysis, cover letters and application progress.

## 3. Goals

- Help candidates identify relevant evidence for each job requirement.
- Explain strengths, gaps and uncertainty in a transparent way.
- Improve document structure, readability and job relevance without fabricating facts.
- Generate editable cover-letter drafts grounded in candidate evidence.
- Provide a free, privacy-conscious career workspace.
- Support both hosted and self-hosted deployments.

## 4. Non-goals

- Guaranteeing interviews or job offers.
- Bypassing or manipulating ATS controls.
- Claiming compatibility with every ATS vendor or a proprietary ATS score.
- Automatically applying to jobs or impersonating candidates.
- Scraping job boards in v1.
- Inventing experience, credentials, skills or achievement metrics.
- Selling candidate data or monetizing personal documents.

## 5. Target users

- Active job seekers tailoring applications.
- Graduates and early-career candidates.
- Experienced professionals changing roles or industries.
- Career advisers and mentors supporting candidates (future multi-user collaboration).

## 6. Core user journeys

### Journey A: First resume
1. Create account.
2. Complete basic candidate profile.
3. Upload PDF/DOCX/TXT resume.
4. Review extracted content and correct errors.
5. Save a structured resume version.

### Journey B: Analyze a job
1. Paste or enter job description.
2. Review extracted role and requirements.
3. Select resume version.
4. Run analysis.
5. Review requirement matches, evidence, gaps and score breakdown.

### Journey C: Optimize resume
1. Select recommendation.
2. Compare original and suggested text.
3. Review source evidence.
4. Accept, edit or reject.
5. Save as a new resume version and export.

### Journey D: Cover letter
1. Select job and resume version.
2. Generate draft using approved evidence.
3. Edit and approve content.
4. Export document.

### Journey E: Track application
1. Create application from analyzed job.
2. Select resume version used.
3. Update status and dates.
4. Record interviews, notes and outcomes.

## 7. Functional requirements

### P0 — Foundation
- Account registration and login.
- Candidate profile.
- Secure private resume upload.
- Resume metadata and version records.
- User data isolation.

### P1 — Resume intelligence
- PDF/DOCX/TXT extraction.
- Structured sections: summary, experience, education, skills, certifications.
- Source spans and extraction confidence.
- Editable structured resume and version history.
- PDF/DOCX export with selectable text.

### P1 — Job intelligence and matching
- Job description ingestion.
- Required/preferred requirement classification.
- Skills normalization and synonyms.
- Deterministic matching and explainable score breakdown.
- Evidence reference for each match.

### P1 — AI optimization
- Evidence-grounded rewrite suggestions.
- Claim validation and user approval.
- Tailored cover-letter draft.
- Explicit external-provider consent and provider metadata.

### P2 — Career intelligence
- Skill gap analysis.
- Interview question generation based on role requirements and candidate evidence.
- Learning recommendations.

### P2 — Application management
- Application status board.
- Resume/job linkage.
- Interview notes and history.
- User-controlled reminders.

### P2 — Privacy controls
- Export personal data.
- Delete documents and account.
- View and withdraw AI processing consent.
- Configurable retention policy.

## 8. Non-functional requirements

- Security: OWASP ASVS-informed controls; threat model and penetration test before public launch.
- Privacy: data minimization, purpose limitation, retention and deletion workflows; assess UK GDPR obligations for deployment and audience.
- Performance: API p95 target under 500ms for ordinary non-AI CRUD under expected initial load; AI and parsing tasks are asynchronous.
- Reliability: durable task state, bounded retries and idempotent workers.
- Accessibility: WCAG 2.2 AA target.
- Portability: Docker-based self-hosted profile and documented cloud deployment.
- Maintainability: typed API contracts, migrations, automated tests and CI.

## 9. Success metrics

- Resume import completion rate.
- Parsing correction rate and extraction quality.
- Requirement extraction precision/recall on a curated evaluation set.
- Match evidence precision and false-positive rate.
- Percentage of generated claims with valid evidence links.
- Recommendation acceptance/edit/rejection rate.
- Analysis completion and failure rate.
- User-reported usefulness, not raw score inflation.
- Account/document deletion completion time.

## 10. Acceptance criteria

- User A cannot access User B's resume, analysis, cover letter or application by changing an identifier.
- Invalid, oversized and content-type-spoofed uploads are rejected.
- Original files remain private and are never served from a public directory.
- A report shows evidence and uncertainty for each matched requirement.
- Unsupported candidate claims cannot be silently added to the verified profile.
- External model calls cannot occur without the required consent.
- Analysis score is reproducible for the same inputs and scoring version.
- Core user workflows are keyboard accessible and responsive.

## 11. Release plan

1. Foundation: auth, database isolation and private upload.
2. Resume intelligence: parsing, editor and versions.
3. Job intelligence: parsing and normalized requirements.
4. Matching: deterministic scoring and explainable reports.
5. AI: provider gateway, consent, grounded optimization and cover letters.
6. Career tools and application tracker.
7. Security, privacy, accessibility, performance and public launch readiness.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| ATS score misrepresented | Label as platform estimate and publish methodology |
| Hallucinated candidate facts | Evidence links, schema validation and user approval |
| CV data exposure | Private storage, encryption, RLS and explicit provider consent |
| Malicious files | Signature checks, malware scan and sandboxed parsing |
| AI cost | Local-first routing, quotas and asynchronous queues |
| Bias in matching | Evaluate by role/experience cohorts; expose evidence and uncertainty |
| Overbuilt scope | Modular monolith and phased delivery |
