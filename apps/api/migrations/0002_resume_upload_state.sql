-- Track object upload lifecycle and expected length independently of parsing.
ALTER TABLE resumes
    ADD COLUMN IF NOT EXISTS expected_size_bytes BIGINT,
    ADD COLUMN IF NOT EXISTS upload_status TEXT NOT NULL DEFAULT 'awaiting_upload'
    CHECK (upload_status IN ('awaiting_upload','uploaded','quarantined','rejected','deleted'));

CREATE INDEX IF NOT EXISTS idx_resumes_upload_status ON resumes(upload_status);
UPDATE resumes SET upload_status = 'uploaded'
WHERE original_file_key IS NOT NULL AND upload_status = 'awaiting_upload';
