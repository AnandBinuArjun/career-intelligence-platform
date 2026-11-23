# Architecture decisions

## ADR-001: Modular monolith
Keep one API codebase with clear domain modules and a separate worker process. Microservices add operational cost before there is evidence they are needed.

## ADR-002: PostgreSQL as system of record
Use PostgreSQL for users, profiles, resumes, versions, jobs, analyses, recommendations and applications. Use pgvector only where semantic retrieval is justified.

## ADR-003: Hybrid AI with explicit routing
Local Ollama is the default. External inference is disabled by default. Any external processing of personal documents requires explicit, recorded consent and clear disclosure of the provider/data transfer.

## ADR-004: Hybrid deployment
Support a self-hosted Docker Compose profile and a cloud deployment using managed equivalents. Keep secrets and deployment configuration external to source code.

## ADR-005: Explainable compatibility estimates
The scoring engine is deterministic and versioned. LLMs may extract or explain information, but do not directly decide the score. Reports must state that no universal ATS score or bypass guarantee exists.

## ADR-006: Evidence-backed generation
Generated resume claims must cite candidate profile facts or source-document spans. Unsupported claims are flagged for user confirmation and are never silently inserted into verified profile data.

## ADR-007: Private-by-default files
Original documents are stored in private object storage. Access uses short-lived signed URLs. File scanning and content validation happen before parsing.
