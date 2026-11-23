-- Full platform extensions: refresh sessions, retention settings, analysis metadata,
-- cover letter metadata, application reminders, and safe cascading deletion.
-- Apply as database administrator.

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS privacy_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    retention_days INTEGER NOT NULL DEFAULT 365 CHECK (retention_days BETWEEN 7 AND 3650),
    ai_routing_preference TEXT NOT NULL DEFAULT 'local'
        CHECK (ai_routing_preference IN ('local', 'external_with_consent')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE candidate_profiles
    ADD COLUMN IF NOT EXISTS target_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS years_experience NUMERIC(4,1);

ALTER TABLE experiences
    ADD COLUMN IF NOT EXISTS achievements JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS verified BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE analyses
    ADD COLUMN IF NOT EXISTS weights_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS failure_reason TEXT,
    ADD COLUMN IF NOT EXISTS methodology_note TEXT;

ALTER TABLE recommendations
    ADD COLUMN IF NOT EXISTS requires_user_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS rationale TEXT;

ALTER TABLE cover_letters
    ADD COLUMN IF NOT EXISTS title TEXT,
    ADD COLUMN IF NOT EXISTS tone TEXT NOT NULL DEFAULT 'professional',
    ADD COLUMN IF NOT EXISTS evidence_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS model_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE applications
    ADD COLUMN IF NOT EXISTS follow_up_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS salary_range TEXT,
    ADD COLUMN IF NOT EXISTS location TEXT;

-- Allow cascading deletion of users and resumes even when analyses exist.
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_resume_version_id_fkey;
ALTER TABLE analyses
    ADD CONSTRAINT analyses_resume_version_id_fkey
    FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_consent_records_user ON consent_records(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);

-- RLS for new tables
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS user_isolation ON refresh_tokens;
CREATE POLICY user_isolation ON refresh_tokens
    USING (user_id = NULLIF(current_setting('app.user_id', true), '')::uuid)
    WITH CHECK (user_id = NULLIF(current_setting('app.user_id', true), '')::uuid);

ALTER TABLE privacy_settings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS user_isolation ON privacy_settings;
CREATE POLICY user_isolation ON privacy_settings
    USING (user_id = NULLIF(current_setting('app.user_id', true), '')::uuid)
    WITH CHECK (user_id = NULLIF(current_setting('app.user_id', true), '')::uuid);

-- Allow authenticated user to delete their own account record under RLS.
DROP POLICY IF EXISTS users_self_delete ON users;
CREATE POLICY users_self_delete ON users
    FOR DELETE
    USING (id = NULLIF(current_setting('app.user_id', true), '')::uuid);

-- Grant privileges to runtime role if it exists.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'career_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE refresh_tokens, privacy_settings TO career_app;
        GRANT DELETE ON TABLE public.users TO career_app;
    END IF;
END $$;
