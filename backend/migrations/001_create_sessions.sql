CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('it', 'en')),
    timezone TEXT NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
