"""Local HTTP adapter for persisted, multi-turn event drafting sessions."""

import json
import os
import sys
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Annotated, Literal, TypeAlias
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from kairos.contracts import EventWorkflowState, RequestContext, ToolCall, WorkflowError
from kairos.i18n import Language, MessageId, translate
from kairos.provider_store import (
    ProviderProfile,
    ProviderProfileNotFound,
    ProviderProfileStore,
)
from kairos.providers import HuggingFaceEventProvider, OllamaEventProvider, ScriptedEventProvider
from kairos.session_store import (
    SessionConflict,
    SessionNotFound,
    SessionRecord,
    SessionStore,
    apply_migrations,
)
from kairos.workflow import EventWorkflow


DEFAULT_DATABASE_URL = "postgresql://kairos:kairos-local@localhost:5432/kairos"
MAX_API_LOG_BYTES = 8 * 1024
MAX_DIAGNOSTIC_ENTRIES = 500
MAX_DIAGNOSTIC_ENTRY_FIELD_BYTES = 16 * 1024
SENSITIVE_LOG_KEYS = {"authorization", "token", "hf_token", "access_token"}
PACKAGE_STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR = PACKAGE_STATIC_DIR if PACKAGE_STATIC_DIR.is_dir() else Path("/app/static")
DIAGNOSTIC_LOGS: deque[dict] = deque(maxlen=MAX_DIAGNOSTIC_ENTRIES)
DIAGNOSTIC_LOGS_LOCK = Lock()


def _emit_log(event: str, **fields: object) -> None:
    """Write one structured JSON record to container stdout."""
    record = {
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "event": event,
        **fields,
    }
    sanitized = _sanitize_log_data(record)
    buffered = dict(sanitized)
    for key in ("data", "body", "response_body_excerpt"):
        if key in buffered:
            max_bytes = 1_200 if key == "response_body_excerpt" else MAX_DIAGNOSTIC_ENTRY_FIELD_BYTES
            buffered[key] = _bounded_log_data(buffered[key], max_bytes=max_bytes)
    with DIAGNOSTIC_LOGS_LOCK:
        DIAGNOSTIC_LOGS.append(buffered)
    print(json.dumps(sanitized, ensure_ascii=False, default=str), file=sys.stdout, flush=True)


def _sanitize_log_data(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if str(key).lower() in SENSITIVE_LOG_KEYS else _sanitize_log_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_log_data(item) for item in value]
    return value


def _bounded_log_data(value: object, *, max_bytes: int = MAX_API_LOG_BYTES) -> object:
    sanitized = _sanitize_log_data(value)
    encoded = json.dumps(sanitized, ensure_ascii=False, default=str).encode("utf-8")
    if len(encoded) <= max_bytes:
        return sanitized
    return {
        "truncated": True,
        "max_bytes": max_bytes,
        "preview": encoded[:max_bytes].decode("utf-8", errors="ignore"),
    }


def _record_api_request_data(request: Request, data: object) -> None:
    if request.app.state.configuration.debug_api_logs:
        request.state.api_request_data = _bounded_log_data(data)


def _log_api_response_data(request: Request, data: object) -> None:
    if request.app.state.configuration.debug_api_logs:
        _emit_log(
            "api.response_data",
            request_id=request.state.request_id,
            data=_bounded_log_data(data),
        )


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
    task_id: UUID | None = Field(
        default=None,
        description="Stable task ID selected while answering a pending task-removal question.",
    )

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
            profile_store = ProviderProfileStore(pool)
            app.state.provider_profile_store = profile_store
            app.state.ollama_http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
            app.state.hf_http_client = httpx.AsyncClient(
                base_url="https://router.huggingface.co/v1",
                timeout=httpx.Timeout(60.0),
            )
            yield
        finally:
            for client_name in ("ollama_http_client", "hf_http_client"):
                client = getattr(app.state, client_name, None)
                if client is not None:
                    await client.aclose()
            await pool.close()

    app = FastAPI(title="Kairos drafting API", lifespan=lifespan)
    app.state.configuration = configuration
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def playground() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.middleware("http")
    async def request_diagnostics(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        started_at = perf_counter()
        is_health = request.url.path == "/health"
        is_diagnostics_endpoint = request.url.path.startswith("/admin/diagnostics")
        is_static_playground_request = request.url.path == "/" or request.url.path.startswith("/static/")
        omit_api_log = is_diagnostics_endpoint or is_static_playground_request
        try:
            response = await call_next(request)
        except Exception as exc:
            if configuration.debug_api_logs and not is_health and not omit_api_log:
                request_data = getattr(request.state, "api_request_data", None)
                _emit_log(
                    "api.request",
                    request_id=request_id,
                    method=request.method,
                    route=request.url.path,
                    **({"body": request_data} if request_data is not None else {}),
                )
                _emit_log(
                    "api.response",
                    request_id=request_id,
                    method=request.method,
                    route=request.url.path,
                    status=500,
                    elapsed_ms=round((perf_counter() - started_at) * 1000, 2),
                    exception_type=type(exc).__name__,
                )
            raise
        response.headers["X-Request-ID"] = request_id
        if configuration.debug_api_logs and not omit_api_log and (
            not is_health or response.status_code >= 400
        ):
            route = request.scope.get("route")
            request_data = getattr(request.state, "api_request_data", None)
            _emit_log(
                "api.request",
                request_id=request_id,
                method=request.method,
                route=getattr(route, "path", request.url.path),
                **({"body": request_data} if request_data is not None else {}),
            )
            _emit_log(
                "api.response",
                request_id=request_id,
                method=request.method,
                route=getattr(route, "path", request.url.path),
                status=response.status_code,
                elapsed_ms=round((perf_counter() - started_at) * 1000, 2),
            )
        return response

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        try:
            await request.app.state.session_store.ping()
        except Exception as exc:
            if request.app.state.configuration.debug_api_logs:
                _emit_log(
                    "api.health_failure",
                    request_id=getattr(request.state, "request_id", None),
                    exception_type=type(exc).__name__,
                )
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from exc
        return HealthResponse()

    @app.get("/admin/diagnostics", tags=["local-admin"])
    async def read_diagnostics(
        request_id: str | None = Query(default=None, max_length=128),
    ) -> dict[str, object]:
        with DIAGNOSTIC_LOGS_LOCK:
            entries = list(DIAGNOSTIC_LOGS)
        if request_id:
            entries = [entry for entry in entries if entry.get("request_id") == request_id]
        return {"items": list(reversed(entries)), "capacity": MAX_DIAGNOSTIC_ENTRIES}

    @app.delete("/admin/diagnostics", tags=["local-admin"])
    async def clear_diagnostics() -> dict[str, int]:
        with DIAGNOSTIC_LOGS_LOCK:
            cleared = len(DIAGNOSTIC_LOGS)
            DIAGNOSTIC_LOGS.clear()
        return {"cleared": cleared}

    @app.get("/admin/provider-profiles", response_model=list[ProviderProfile], tags=["local-admin"])
    async def list_provider_profiles(request: Request) -> list[ProviderProfile]:
        profiles = await request.app.state.provider_profile_store.list_profiles()
        _log_api_response_data(request, [profile.model_dump(mode="json") for profile in profiles])
        return profiles

    @app.post(
        "/admin/provider-profiles/{profile_id}/activate",
        response_model=ProviderProfile,
        tags=["local-admin"],
    )
    async def activate_provider_profile(profile_id: UUID, request: Request) -> ProviderProfile:
        profile_store: ProviderProfileStore = request.app.state.provider_profile_store
        try:
            profile = await profile_store.get(profile_id)
        except ProviderProfileNotFound as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider profile not found.",
            ) from exc
        configured: APISettings = request.app.state.configuration
        if profile.provider_type == "huggingface" and configured.hf_token is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="HF_TOKEN is not configured for the API.",
            )
        try:
            activated = await profile_store.activate(profile_id)
            _log_api_response_data(request, activated.model_dump(mode="json"))
            return activated
        except ProviderProfileNotFound as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider profile not found.",
            ) from exc

    @app.post(
        "/sessions",
        response_model=SessionRecord,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_session(body: CreateSessionRequest, request: Request) -> SessionRecord:
        _record_api_request_data(request, body.model_dump(mode="json"))
        session = await request.app.state.session_store.create(
            session_id=uuid4(),
            language=body.language,
            timezone=body.timezone,
            state=EventWorkflowState(),
        )
        _log_api_response_data(request, session.model_dump(mode="json"))
        return session

    @app.get("/sessions/{session_id}", response_model=SessionRecord)
    async def get_session(session_id: UUID, request: Request) -> SessionRecord:
        try:
            session = await request.app.state.session_store.get(session_id)
            _log_api_response_data(request, session.model_dump(mode="json"))
            return session
        except SessionNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc

    @app.post("/sessions/{session_id}/turn")
    async def session_turn(
        session_id: UUID, body: TurnRequest, request: Request
    ) -> StreamingResponse:
        _record_api_request_data(request, body.model_dump(mode="json"))
        store: SessionStore = request.app.state.session_store
        try:
            session = await store.get(session_id)
        except SessionNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc

        now = datetime.now(ZoneInfo(session.timezone))
        context = RequestContext(now=now, language=session.language, timezone=session.timezone)
        configured: APISettings = request.app.state.configuration
        profile: ProviderProfile = await request.app.state.provider_profile_store.get_active()
        request_id = request.state.request_id

        def internal_log(event: str, **fields: object) -> None:
            if configured.debug_internal_logs:
                _emit_log(event, request_id=request_id, **fields)

        def api_log(event: str, **fields: object) -> None:
            if configured.debug_api_logs:
                _emit_log(event, **fields)

        def encode_and_log_sse(event: WorkflowSSE) -> str:
            if configured.debug_api_logs:
                _emit_log(
                    "api.response_event",
                    request_id=request_id,
                    sse_event=event.event,
                    data=_bounded_log_data(event.model_dump(mode="json", exclude={"event"})),
                )
            return _encode_sse(event)

        internal_log(
            "internal.provider_selected",
            provider=profile.provider_type,
            model=profile.model,
        )

        def model_io_callback(direction: str, content: str) -> None:
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                payload = content
            _emit_log(
                f"connector.{direction}",
                request_id=request_id,
                provider=profile.provider_type,
                model=profile.model,
                direction=direction,
                data=payload,
            )

        def provider_failure_callback(details: dict) -> None:
            if not configured.debug_connector_logs:
                return
            safe_details = dict(details)
            _emit_log("connector.failure", request_id=request_id, **safe_details)

        model_io = model_io_callback if configured.debug_connector_logs else None
        if profile.provider_type == "ollama":
            provider = OllamaEventProvider(
                profile.model,
                request.app.state.ollama_http_client,
                endpoint_url=profile.endpoint_url,
                model_io_callback=model_io,
                failure_callback=provider_failure_callback,
                debug_connector_logs=configured.debug_connector_logs,
            )
        elif profile.provider_type == "huggingface":
            token = configured.hf_token.get_secret_value() if configured.hf_token else None
            provider = HuggingFaceEventProvider(
                profile.model,
                token,
                request.app.state.hf_http_client,
                model_io_callback=model_io,
                failure_callback=provider_failure_callback,
                debug_connector_logs=configured.debug_connector_logs,
            )
        else:
            provider = _development_provider(session.state, session.language, session.timezone, now)
        workflow = EventWorkflow(provider)

        async def stream() -> AsyncIterator[str]:
            turn_started_at = perf_counter()
            try:
                async for item in workflow.stream_advance(
                    session.state, body.message, context, task_id=body.task_id
                ):
                    if item.kind == "progress":
                        phase = (
                            "validation"
                            if item.message == translate(MessageId.PROGRESS_VALIDATE, context.language)
                            else "model_request"
                        )
                        internal_log("internal.workflow_progress", phase=phase)
                        yield encode_and_log_sse(ProgressSSE(message=item.message))
                    elif item.kind == "text":
                        yield encode_and_log_sse(TextSSE(text=item.text))
                    elif item.kind == "completed":
                        internal_log("internal.validation", outcome="accepted")
                        internal_log("internal.persistence", outcome="saving")
                        try:
                            saved = await store.save_state(
                                session.id,
                                expected_updated_at=session.updated_at,
                                state=item.state,
                            )
                        except SessionConflict:
                            internal_log("internal.persistence", outcome="conflict")
                            api_log(
                                "workflow.terminal",
                                request_id=request_id,
                                outcome="error",
                                code="session_conflict",
                                provider=profile.provider_type,
                                model=profile.model,
                                elapsed_ms=round((perf_counter() - turn_started_at) * 1000, 2),
                            )
                            yield encode_and_log_sse(ErrorSSE(
                                code="session_conflict",
                                message=translate(MessageId.API_SESSION_CONFLICT, session.language),
                            ))
                            return
                        except SessionNotFound:
                            internal_log("internal.persistence", outcome="session_not_found")
                            api_log(
                                "workflow.terminal",
                                request_id=request_id,
                                outcome="error",
                                code="session_not_found",
                                provider=profile.provider_type,
                                model=profile.model,
                                elapsed_ms=round((perf_counter() - turn_started_at) * 1000, 2),
                            )
                            yield encode_and_log_sse(ErrorSSE(
                                code="session_not_found",
                                message=translate(MessageId.API_SESSION_NOT_FOUND, session.language),
                            ))
                            return
                        except Exception as exc:
                            internal_log(
                                "internal.persistence",
                                outcome="failed",
                                exception_type=type(exc).__name__,
                            )
                            raise
                        internal_log("internal.persistence", outcome="committed")
                        api_log(
                            "workflow.terminal",
                            request_id=request_id,
                            outcome="completed",
                            provider=profile.provider_type,
                            model=profile.model,
                            elapsed_ms=round((perf_counter() - turn_started_at) * 1000, 2),
                        )
                        yield encode_and_log_sse(CompletedSSE(session=saved))
            except WorkflowError as exc:
                internal_log("internal.workflow_failure", code=exc.code.value)
                if exc.code in {
                    MessageId.INVALID_ARGUMENTS,
                    MessageId.INVALID_TOOL_CALL,
                    MessageId.REMINDER_IN_PAST,
                    MessageId.REMINDER_TOOL_COUNT,
                    MessageId.TOOL_COUNT,
                    MessageId.TOOL_NOT_ALLOWED,
                }:
                    internal_log("internal.validation", outcome="rejected", code=exc.code.value)
                api_log(
                    "workflow.terminal",
                    request_id=request_id,
                    outcome="error",
                    code=exc.code.value,
                    provider=profile.provider_type,
                    model=profile.model,
                    elapsed_ms=round((perf_counter() - turn_started_at) * 1000, 2),
                )
                yield encode_and_log_sse(ErrorSSE(code=exc.code.value, message=exc.text(session.language)))
            except Exception as exc:
                internal_log(
                    "internal.workflow_failure",
                    code="internal_error",
                    exception_type=type(exc).__name__,
                )
                api_log(
                    "workflow.terminal",
                    request_id=request_id,
                    outcome="error",
                    code="internal_error",
                    exception_type=type(exc).__name__,
                    provider=profile.provider_type,
                    model=profile.model,
                    elapsed_ms=round((perf_counter() - turn_started_at) * 1000, 2),
                )
                yield encode_and_log_sse(ErrorSSE(
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
