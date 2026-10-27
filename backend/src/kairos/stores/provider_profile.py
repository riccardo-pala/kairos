"""Persistence for model-provider profiles and their active state."""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict
from psycopg_pool import AsyncConnectionPool


ProviderType = Literal["ollama", "huggingface"]


class ProviderProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    provider_type: ProviderType
    model: str | None
    endpoint_url: str | None
    active: bool
    created_at: AwareDatetime


class ProviderProfileNotFound(Exception):
    pass


class ProviderProfileStore:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def list_profiles(self) -> list[ProviderProfile]:
        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT p.id, p.name, p.provider_type, p.model, p.endpoint_url,
                       p.created_at, p.is_active AS active
                FROM provider_profiles p
                ORDER BY p.created_at, p.name
                """
            )
            rows = await cursor.fetchall()
        return [ProviderProfile.model_validate(row) for row in rows]

    async def get_active(self) -> ProviderProfile:
        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT p.id, p.name, p.provider_type, p.model, p.endpoint_url,
                       p.created_at, p.is_active AS active
                FROM provider_profiles p
                WHERE p.is_active = TRUE
                """
            )
            row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("No active provider profile is configured")
        return ProviderProfile.model_validate(row)

    async def get(self, profile_id: UUID) -> ProviderProfile:
        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT p.id, p.name, p.provider_type, p.model, p.endpoint_url,
                       p.created_at, p.is_active AS active
                FROM provider_profiles p
                WHERE p.id = %s
                """,
                (profile_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise ProviderProfileNotFound
        return ProviderProfile.model_validate(row)

    async def activate(self, profile_id: UUID) -> ProviderProfile:
        async with self.pool.connection() as connection:
            async with connection.transaction():
                await connection.execute("LOCK TABLE provider_profiles IN EXCLUSIVE MODE")
                exists = await connection.execute(
                    "SELECT 1 FROM provider_profiles WHERE id = %s", (profile_id,)
                )
                if await exists.fetchone() is None:
                    raise ProviderProfileNotFound
                await connection.execute(
                    "UPDATE provider_profiles SET is_active = FALSE WHERE is_active = TRUE"
                )
                cursor = await connection.execute(
                    """
                    UPDATE provider_profiles
                    SET is_active = TRUE
                    WHERE id = %s
                    RETURNING id, name, provider_type, model, endpoint_url, created_at,
                              is_active AS active
                    """,
                    (profile_id,),
                )
                row = await cursor.fetchone()
        return ProviderProfile.model_validate(row)
