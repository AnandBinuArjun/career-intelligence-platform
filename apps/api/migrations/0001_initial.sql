-- Initial schema. Review and apply with a migration runner.
-- Runtime connections must use a dedicated non-superuser role without BYPASSRLS.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    auth_provider TEXT NOT NULL DEFAULT 'local',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE candidate_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT,
    professional_title TEXT,
    summary TEXT,
    location TEXT,
    contact_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE experiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    employer TEXT,
    job_title TEXT NOT NULL,
    location TEXT,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    source_reference JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE education (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    institution TEXT NOT NULL,
    qualification TEXT,
    field_of_study TEXT,
    start_date DATE,
    end_date DATE,
    source_reference JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    proficiency TEXT,
    years_experience NUMERIC(4,1),
    evidence_reference JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE(user_id, name)
);

CREATE TABLE certifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    issuer TEXT,
    credential_id TEXT,
    issued_on DATE,
    expires_on DATE,
    evidence_reference JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    original_file_key TEXT,
    file_type TEXT,
    file_sha256 CHAR(64),
    parse_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (parse_status IN ('pending','processing','completed','failed')),
    parsed_content JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE resume_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content JSONB NOT NULL,
    source TEXT NOT NULL DEFAULT 'user'
        CHECK (source IN ('user','optimized','imported')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(resume_id, version_number)
);

CREATE TABLE job_descriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_name TEXT,
    job_title TEXT NOT NULL,
    description TEXT NOT NULL,
    extracted_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_version_id UUID NOT NULL REFERENCES resume_versions(id) ON DELETE RESTRICT,
    job_description_id UUID NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued','processing','completed','failed','cancelled')),
    overall_score NUMERIC(5,2) CHECK (overall_score BETWEEN 0 AND 100),
    scoring_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    scoring_version TEXT NOT NULL DEFAULT 'v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    original_text TEXT,
    suggested_text TEXT,
    evidence_reference JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','accepted','rejected','edited')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cover_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_description_id UUID REFERENCES job_descriptions(id) ON DELETE SET NULL,
    resume_version_id UUID REFERENCES resume_versions(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_description_id UUID REFERENCES job_descriptions(id) ON DELETE SET NULL,
    resume_version_id UUID REFERENCES resume_versions(id) ON DELETE SET NULL,
    company_name TEXT,
    position TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','ready','applied','screening','interview','assessment','offer','rejected','withdrawn')),
    applied_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE interview_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    scheduled_at TIMESTAMPTZ,
    interview_type TEXT,
    notes TEXT,
    outcome TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    provider TEXT,
    policy_version TEXT NOT NULL,
    granted BOOLEAN NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    withdrawn_at TIMESTAMPTZ
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_experiences_user ON experiences(user_id);
CREATE INDEX idx_education_user ON education(user_id);
CREATE INDEX idx_skills_user ON skills(user_id);
CREATE INDEX idx_resumes_user ON resumes(user_id);
CREATE INDEX idx_jobs_user ON job_descriptions(user_id);
CREATE INDEX idx_analyses_user ON analyses(user_id);
CREATE INDEX idx_applications_user ON applications(user_id);
CREATE INDEX idx_recommendations_analysis ON recommendations(analysis_id);

-- RLS policy pattern. API must SET LOCAL app.user_id inside each transaction
-- after authenticating the request. Never trust a client-supplied user ID.
DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'candidate_profiles','experiences','education','skills','certifications',
        'resumes','job_descriptions','analyses','cover_letters','applications',
        'consent_records','audit_logs'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format(
            'CREATE POLICY user_isolation ON %I USING (user_id = NULLIF(current_setting(''app.user_id'', true), '''')::uuid) WITH CHECK (user_id = NULLIF(current_setting(''app.user_id'', true), '''')::uuid)',
            table_name
        );
    END LOOP;
END $$;

-- Child records are protected through parent ownership checks in repository queries
-- and must receive equivalent RLS policies or be accessed only through secure
-- SECURITY INVOKER views/functions. Add those policies before production.
ALTER TABLE resume_versions ENABLE ROW LEVEL SECURITY;
CREATE POLICY resume_versions_owner ON resume_versions
USING (
    EXISTS (
        SELECT 1 FROM resumes r
        WHERE r.id = resume_id
          AND r.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM resumes r
        WHERE r.id = resume_id
          AND r.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
    )
);

ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
CREATE POLICY recommendations_owner ON recommendations
USING (
    EXISTS (
        SELECT 1 FROM analyses a
        WHERE a.id = analysis_id
          AND a.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM analyses a
        WHERE a.id = analysis_id
          AND a.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
    )
);

ALTER TABLE interview_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY interview_records_owner ON interview_records
USING (
    EXISTS (
        SELECT 1 FROM applications a
        WHERE a.id = application_id
          AND a.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM applications a
        WHERE a.id = application_id
          AND a.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
    )
);
