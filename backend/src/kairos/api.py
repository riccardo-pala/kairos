"""Local HTTP adapter for persisted, multi-turn event drafting sessions."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Literal, TypeAlias
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, ConfigDict, Field, field_validator

from kairos.contracts import EventWorkflowState, RequestContext, ToolCall, WorkflowError
from kairos.i18n import Language, MessageId, translate
from kairos.providers import OllamaEventProvider, ScriptedEventProvider
from kairos.session_store import (
    SessionConflict,
    SessionNotFound,
    SessionRecord,
    SessionStore,
    apply_migrations,
)
from kairos.workflow import EventWorkflow


logger = logging.getLogger(__name__)
DEFAULT_DATABASE_URL = "postgresql://kairos:kairos-local@localhost:5432/kairos"


class APISettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    database_url: str
    ollama_model: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    @classmethod
    def from_env(cls) -> "APISettings":
        model = os.getenv("KAIROS_OLLAMA_MODEL", "").strip() or None
        base_url = os.getenv("KAIROS_OLLAMA_BASE_URL", "").strip() or "http://localhost:11434"
        database_url = os.getenv("KAIROS_DATABASE_URL", "").strip() or DEFAULT_DATABASE_URL
        return cls(
            database_url=database_url,
            ollama_model=model,
            ollama_base_url=base_url,
        )


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Language = Language.IT
    timezone: str = Field(min_length=1, max_length=128)

    @field_validator("timezone")
    @classmethod
    def require_iana_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Timezone must be a valid IANA name.") from exc
        return value


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=8_000)

    @field_validator("message")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must not be blank.")
        return value


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ProgressSSE(BaseModel):
    event: Literal["progress"] = "progress"
    message: str


class TextSSE(BaseModel):
    event: Literal["text"] = "text"
    text: str


class CompletedSSE(BaseModel):
    event: Literal["completed"] = "completed"
    session: SessionRecord


class ErrorSSE(BaseModel):
    event: Literal["error"] = "error"
    code: str
    message: str


WorkflowSSE: TypeAlias = Annotated[
    ProgressSSE | TextSSE | CompletedSSE | ErrorSSE,
    Field(discriminator="event"),
]


def _encode_sse(event: WorkflowSSE) -> str:
    return f"event: {event.event}\ndata: {event.model_dump_json(exclude={'event'})}\n\n"


def _development_provider(state: EventWorkflowState, language: Language, timezone: str, now: datetime):
    """Create a fresh scripted demo provider for this turn; it keeps no session state."""
    draft = state.draft
    patch = {}
    if not draft.title:
        patch["title"] = translate(MessageId.DEMO_TITLE, language)
    if draft.start_date is None:
        patch["start_date"] = (now.astimezone(ZoneInfo(timezone)).date()).isoformat()
    if draft.start_time is None:
        patch["start_time"] = "12:00"
    if not draft.timezone:
        patch["timezone"] = timezone
    if patch:
        call = ToolCall(name="update_event_draft", arguments={"patch": patch})
    elif draft.reminders is None:
        call = ToolCall(name="update_event_draft", arguments={
            "patch": {"reminders": [{"minutes_before": 60}]}
        })
    else:
        call = ToolCall(name="ask_event_clarification", arguments={
            "question": translate(MessageId.API_DEMO_LIMIT, language)
        })
    return ScriptedEventProvider([call])


def create_app(settings: APISettings | None = None) -> FastAPI:
    configuration = settings or APISettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        pool = AsyncConnectionPool(
            conninfo=configuration.database_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        app.state.db_pool = pool
        try:
            await pool.open()
            await pool.wait(timeout=10)
            await apply_migrations(pool)
            app.state.session_store = SessionStore(pool)
            if configuration.ollama_model:
                app.state.http_client = httpx.AsyncClient(
                    base_url=configuration.ollama_base_url,
                    timeout=httpx.Timeout(60.0),
                )
            else:
                app.state.http_client = None
            yield
        finally:
            client = getattr(app.state, "http_client", None)
            if client is not None:
                await client.aclose()
            await pool.close()

    app = FastAPI(title="Kairos drafting API", lifespan=lifespan)
    app.state.configuration = configuration

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        try:
            await request.app.state.session_store.ping()
        except Exception as exc:
            logger.error("Database health check failed (%s)", type(exc).__name__)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from exc
        return HealthResponse()

    @app.post(
        "/sessions",
        response_model=SessionRecord,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_session(body: CreateSessionRequest, request: Request) -> SessionRecord:
        return await request.app.state.session_store.create(
            session_id=uuid4(),
            language=body.language,
            timezone=body.timezone,
            state=EventWorkflowState(),
        )

    @app.get("/sessions/{session_id}", response_model=SessionRecord)
    async def get_session(session_id: UUID, request: Request) -> SessionRecord:
        try:
            return await request.app.state.session_store.get(session_id)
        except SessionNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc

    @app.post("/sessions/{session_id}/turn")
    async def session_turn(
        session_id: UUID, body: TurnRequest, request: Request
    ) -> StreamingResponse:
        store: SessionStore = request.app.state.session_store
        try:
            session = await store.get(session_id)
        except SessionNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc

        now = datetime.now(ZoneInfo(session.timezone))
        context = RequestContext(now=now, language=session.language, timezone=session.timezone)
        configured: APISettings = request.app.state.configuration
        if configured.ollama_model:
            provider = OllamaEventProvider(
                configured.ollama_model,
                request.app.state.http_client,
            )
        else:
            provider = _development_provider(session.state, session.language, session.timezone, now)
        workflow = EventWorkflow(provider)

        async def stream() -> AsyncIterator[str]:
            try:
                async for item in workflow.stream_advance(session.state, body.message, context):
                    if item.kind == "progress":
                        yield _encode_sse(ProgressSSE(message=item.message))
                    elif item.kind == "text":
                        yield _encode_sse(TextSSE(text=item.text))
                    elif item.kind == "completed":
                        try:
                            saved = await store.save_state(
                                session.id,
                                expected_updated_at=session.updated_at,
                                state=item.state,
                            )
                        except SessionConflict:
                            yield _encode_sse(ErrorSSE(
                                code="session_conflict",
                                message=translate(MessageId.API_SESSION_CONFLICT, session.language),
                            ))
                            return
                        except SessionNotFound:
                            yield _encode_sse(ErrorSSE(
                                code="session_not_found",
                                message=translate(MessageId.API_SESSION_NOT_FOUND, session.language),
                            ))
                            return
                        yield _encode_sse(CompletedSSE(session=saved))
            except WorkflowError as exc:
                yield _encode_sse(ErrorSSE(code=exc.code.value, message=exc.text(session.language)))
            except Exception as exc:
                logger.error("Unhandled error while streaming a session turn (%s)", type(exc).__name__)
                yield _encode_sse(ErrorSSE(
                    code="internal_error",
                    message=translate(MessageId.API_INTERNAL_ERROR, session.language),
                ))

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
