-- Preserve an existing real selection; otherwise use local Ollama.
DELETE FROM provider_profiles WHERE provider_type = 'demo';

UPDATE provider_profiles
SET is_active = TRUE
WHERE provider_type = 'ollama'
  AND NOT EXISTS (SELECT 1 FROM provider_profiles WHERE is_active = TRUE);

ALTER TABLE provider_profiles DROP CONSTRAINT provider_profiles_provider_type_check;
ALTER TABLE provider_profiles ADD CONSTRAINT provider_profiles_provider_type_check
    CHECK (provider_type IN ('ollama', 'huggingface'));

ALTER TABLE provider_profiles DROP CONSTRAINT provider_profiles_check;
ALTER TABLE provider_profiles ADD CONSTRAINT provider_profiles_check
    CHECK (
        (provider_type = 'ollama' AND model IS NOT NULL AND endpoint_url IS NOT NULL)
        OR (provider_type = 'huggingface' AND model IS NOT NULL AND endpoint_url IS NULL)
    );
