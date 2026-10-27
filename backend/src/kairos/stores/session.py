"""PostgreSQL persistence for the current draft only; no chat transcript is stored."""

from pathlib import Path
import os
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool
from pydantic import AwareDatetime

from kairos.contracts import EventWorkflowState
from kairos.i18n import Language
from kairos.models.guidance import build_draft_guidance
from kairos.models.session import SessionRecord


class SessionNotFound(Exception):
    pass


class SessionConflict(Exception):
    """The session changed after the client turn began."""


class SessionStore:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def ping(self) -> None:
        async with self.pool.connection() as connection:
            cursor = await connection.execute("SELECT 1")
            await cursor.fetchone()

    async def create(
        self, session_id: UUID, language: Language, timezone: str, state: EventWorkflowState
    ) -> SessionRecord:
        async with self.pool.connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    INSERT INTO sessions (id, language, timezone, state)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, language, timezone, state, created_at, updated_at
                    """,
                    (session_id, language.value, timezone, Jsonb(state.model_dump(mode="json"))),
                )
                row = await cursor.fetchone()
        return self._record(row)

    async def get(self, session_id: UUID) -> SessionRecord:
        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT id, language, timezone, state, created_at, updated_at
                FROM sessions WHERE id = %s
                """,
                (session_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise SessionNotFound
        return self._record(row)

    async def change_language(self, session_id: UUID, language: Language) -> SessionRecord:
        """Atomically update language without replacing any draft field."""
        async with self.pool.connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    UPDATE sessions
                    SET language = %s,
                        state = jsonb_set(state, '{conversation_language}', to_jsonb(%s::text)),
                        updated_at = GREATEST(clock_timestamp(), updated_at + INTERVAL '1 microsecond')
                    WHERE id = %s
                    RETURNING id, language, timezone, state, created_at, updated_at
                    """,
                    (language.value, language.value, session_id),
                )
                row = await cursor.fetchone()
        if row is None:
            raise SessionNotFound
        return self._record(row)

    async def save_state(
        self,
        session_id: UUID,
        expected_updated_at: AwareDatetime,
        state: EventWorkflowState,
    ) -> SessionRecord:
        """Atomically replace state only if the session has not changed meanwhile."""
        async with self.pool.connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    UPDATE sessions
                    SET state = %s,
                        updated_at = GREATEST(clock_timestamp(), updated_at + INTERVAL '1 microsecond')
                    WHERE id = %s AND updated_at = %s
                    RETURNING id, language, timezone, state, created_at, updated_at
                    """,
                    (Jsonb(state.model_dump(mode="json")), session_id, expected_updated_at),
                )
                row = await cursor.fetchone()
                if row is None:
                    exists = await connection.execute(
                        "SELECT 1 FROM sessions WHERE id = %s", (session_id,)
                    )
                    if await exists.fetchone() is None:
                        raise SessionNotFound
                    raise SessionConflict
        return self._record(row)

    @staticmethod
    def _record(row: dict) -> SessionRecord:
        values = dict(row)
        values["state"] = EventWorkflowState.model_validate(values["state"])
        values["guidance"] = build_draft_guidance(
            values["state"].draft,
            Language(values["language"]),
        )
        return SessionRecord.model_validate(values)


async def apply_migrations(pool: AsyncConnectionPool) -> None:
    """Apply each checked-in SQL migration once, recording it transactionally."""
    configured_dir = os.getenv("MIGRATIONS_DIR")
    migration_dir = (
        Path(configured_dir)
        if configured_dir
        else Path(__file__).resolve().parents[3] / "migrations"
    )
    migrations = sorted(migration_dir.glob("*.sql"))
    if not migrations:
        raise RuntimeError(f"No SQL migrations found in {migration_dir}")
    async with pool.connection() as connection:
        async with connection.transaction():
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
                )
                """
            )

    for migration in migrations:
        async with pool.connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = %s",
                    (migration.stem,),
                )
                if await cursor.fetchone() is not None:
                    continue
                await connection.execute(migration.read_text(encoding="utf-8"), prepare=False)
                await connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (migration.stem,),
                )
