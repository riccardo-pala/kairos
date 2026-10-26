"""Environment-backed configuration for the local API."""

import os

from pydantic import BaseModel, ConfigDict, SecretStr


DEFAULT_DATABASE_URL = "postgresql://kairos:kairos-local@localhost:5432/kairos"


class APISettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    database_url: str
    hf_token: SecretStr | None = None
    debug_api_logs: bool = False
    debug_connector_logs: bool = False
    debug_internal_logs: bool = False

    @staticmethod
    def _env_enabled(name: str) -> bool:
        return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def from_env(cls) -> "APISettings":
        database_url = os.getenv("DATABASE_URL", "").strip() or DEFAULT_DATABASE_URL
        token = os.getenv("HF_TOKEN", "").strip()
        return cls(
            database_url=database_url,
            hf_token=SecretStr(token) if token else None,
            debug_api_logs=cls._env_enabled("PLAYGROUND_DEBUG_API_LOGS"),
            debug_connector_logs=cls._env_enabled("PLAYGROUND_DEBUG_CONNECTOR_LOGS"),
            debug_internal_logs=cls._env_enabled("PLAYGROUND_DEBUG_INTERNAL_LOGS"),
        )
