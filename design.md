# Product Design Specification

## 1. Product identity

**Name:** ATS Optimization & Career Intelligence Platform  
**Short name:** CareerIntel  
**Promise:** Help candidates understand job requirements, improve the clarity and relevance of their application documents, and make informed career decisions.

The product does not promise to bypass applicant tracking systems, guarantee interviews, or reproduce the proprietary scoring of any ATS vendor. It provides transparent compatibility estimates and document-quality guidance.

## 2. Design principles

1. **Clarity over decoration:** show the next useful action, not ornamental dashboards.
2. **Evidence over invented claims:** generated statements must be traceable to user-provided evidence.
3. **Explainability:** every match, gap and recommendation must have a reason.
4. **Privacy is visible:** communicate when documents stay local and when data may leave the deployment.
5. **Candidate control:** AI suggestions are drafts; the candidate accepts, edits or rejects them.
6. **Accessible by default:** keyboard operation, semantic structure, visible focus, reduced motion and WCAG 2.2 AA target.

## 3. Visual system

### Theme

- Canvas: `#0B0F19` (graphite)
- Surface: `#121A2A`
- Elevated surface: `#182338`
- Primary accent: `#5B8CFF` (electric blue)
- Primary text: `#F4F7FB`
- Secondary text: `#9AA8BD`
- Success: `#35C98A`
- Warning: `#F5B94C`
- Danger: `#F16B76`
- Border: `rgba(255,255,255,0.10)`

Use color semantically. Do not communicate status by color alone. Avoid excessive gradients, neon glows, glassmorphism and high-density charts.

### Typography

Use a modern sans-serif system stack initially. Establish a clear hierarchy: page title, section heading, card title, body, metadata. Body copy should remain comfortable at 14–16px; avoid tiny low-contrast labels.

### Layout

- Desktop: persistent left navigation (240–256px), content area with max width around 1200px.
- Tablet: collapsible navigation.
- Mobile: compact top bar and bottom/slide-out navigation; all workflows remain usable without horizontal scrolling.
- Use consistent 8px spacing rhythm, 12–16px card radius and restrained shadows.

## 4. Information architecture

1. Overview
2. My Resumes
3. ATS Analyzer
4. Job Intelligence
5. Cover Letters
6. Career Development
7. Applications
8. Settings & Privacy

## 5. Key page specifications

### Overview

- Primary CTA: Analyze a job.
- Resume status and recent documents.
- Recent analysis summaries with score explanation, not just a percentage.
- Application pipeline snapshot.
- Privacy state and provider-routing indicator.
- Empty state guides first-time users through profile → resume → job description.

### Resume workspace

- Left: resume section navigation.
- Center: structured editor for summary, experience, education, skills and certifications.
- Right: evidence panel showing source text and provenance for imported/generated content.
- Version history with named snapshots and restore action.
- Preview and export controls.

### Job intelligence

- Job description input/paste/import.
- Parsed role title, seniority, responsibilities and qualifications.
- Clearly separate required from preferred criteria.
- Let users correct extraction before analysis.

### ATS analysis

- Overall compatibility estimate with scoring methodology/version visible.
- Category breakdown: required skills, preferred skills, experience, education/certifications, evidence quality and document structure.
- Requirement-by-requirement matrix: requirement, evidence found, match state, source reference and suggested action.
- Distinguish missing evidence from missing capability. Never imply the candidate has a skill merely because a keyword can be inserted.
- Explain that scores are platform estimates, not an ATS vendor's internal score.

### Optimization review

- Side-by-side original and suggested text.
- Highlight changed claims and show evidence links.
- Accept/edit/reject each recommendation.
- Block unsupported claims from one-click insertion into the verified profile.

### Cover letter editor

- Draft tied to a selected job and resume version.
- Tone and length controls.
- Evidence panel for factual claims.
- Editable output and export.

### Applications

- Kanban/list view with draft, ready, applied, screening, interview, assessment, offer, rejected and withdrawn states.
- Notes and interview history.
- User-entered dates and reminders; no automatic external job-site scraping in v1.

### Settings & privacy

- AI routing: local-only by default.
- Explain the data shared with external AI before asking consent.
- Consent history and withdrawal.
- Export account data and delete account/documents.
- Retention and storage information.

## 6. Interaction patterns

- Use progressive disclosure for advanced scoring details.
- Long-running analysis uses visible queued/processing/completed/failed states.
- Preserve drafts and warn before discarding unsaved edits.
- Provide actionable error messages with retry guidance.
- Never show a fabricated score while analysis is pending.

## 7. Accessibility requirements

- WCAG 2.2 AA target.
- Full keyboard navigation and visible focus ring.
- Semantic headings, labels and landmarks.
- Form errors announced accessibly and associated with inputs.
- Contrast ratio 4.5:1 for normal text and 3:1 for large text/UI components.
- Reduced-motion support.
- Charts have text summaries and data tables.

## 8. Design acceptance criteria

- A first-time user can identify the primary action within five seconds.
- Every recommendation can be traced to a job requirement and candidate evidence.
- The user can correct extracted job requirements before scoring.
- No important action is color-only or hover-only.
- All core workflows work at 360px viewport width and with keyboard-only navigation.
