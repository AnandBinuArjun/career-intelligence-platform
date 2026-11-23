-- Apply as the database administrator, not as the runtime application role.
-- Runtime role must be NOSUPERUSER and NOBYPASSRLS.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_self_select ON users
    FOR SELECT
    USING (id = NULLIF(current_setting('app.user_id', true), '')::uuid);
CREATE POLICY users_register_insert ON users
    FOR INSERT
    WITH CHECK (true);

-- Login is performed through a narrowly scoped SECURITY DEFINER function so
-- the runtime role does not receive blanket SELECT access to password hashes.
CREATE OR REPLACE FUNCTION public.auth_lookup_user(p_email text)
RETURNS TABLE(id uuid, password_hash text, is_active boolean)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT u.id, u.password_hash, u.is_active
    FROM public.users AS u
    WHERE u.email = lower(trim(p_email))
    LIMIT 1;
$$;
REVOKE ALL ON FUNCTION public.auth_lookup_user(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.auth_lookup_user(text) TO career_app;

-- Grant normal application access to domain tables, then restrict users separately.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO career_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO career_app;
REVOKE ALL ON TABLE public.users FROM career_app;
GRANT SELECT (id, email, is_active) ON public.users TO career_app;
GRANT INSERT (id, email, password_hash) ON public.users TO career_app;

-- Future tables created by the migration owner receive runtime CRUD privileges.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO career_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO career_app;
