CREATE TABLE provider_profiles (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    provider_type TEXT NOT NULL CHECK (provider_type IN ('demo', 'ollama', 'huggingface')),
    model TEXT,
    endpoint_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (
        (provider_type = 'demo' AND model IS NULL AND endpoint_url IS NULL)
        OR (provider_type = 'ollama' AND model IS NOT NULL AND endpoint_url IS NOT NULL)
        OR (provider_type = 'huggingface' AND model IS NOT NULL AND endpoint_url IS NULL)
    )
);

CREATE UNIQUE INDEX provider_profiles_single_active_idx
    ON provider_profiles (is_active)
    WHERE is_active = TRUE;

INSERT INTO provider_profiles
    (id, name, provider_type, model, endpoint_url, is_active)
VALUES
    ('00000000-0000-4000-8000-000000000001', 'Demo', 'demo', NULL, NULL, TRUE),
    ('00000000-0000-4000-8000-000000000002', 'Local Ollama (Qwen 3 8B)', 'ollama',
     'qwen3:8b', 'http://host.docker.internal:11434', FALSE),
    ('00000000-0000-4000-8000-000000000003', 'Hugging Face (Qwen3 8B)', 'huggingface',
     'Qwen/Qwen3-8B', NULL, FALSE);
