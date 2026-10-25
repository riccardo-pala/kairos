"""Minimal stateless HTTP adapter for one event-drafting turn."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta
from typing import Annotated, Literal, TypeAlias
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from kairos.contracts import EventWorkflowState, RequestContext, ToolCall, WorkflowError
from kairos.i18n import Language, MessageId, translate
from kairos.providers import OllamaEventProvider, ScriptedEventProvider
from kairos.workflow import EventWorkflow


logger = logging.getLogger(__name__)


class APISettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    ollama_model: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    @classmethod
    def from_env(cls) -> "APISettings":
        model = os.getenv("KAIROS_OLLAMA_MODEL", "").strip() or None
        base_url = os.getenv("KAIROS_OLLAMA_BASE_URL", "").strip() or "http://localhost:11434"
        return cls(ollama_model=model, ollama_base_url=base_url)


class WorkflowTurnRequest(BaseModel):
    """One client-supplied message and its latest in-memory workflow state."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=8_000)
    state: EventWorkflowState | None = None
    language: Language = Language.IT
    timezone: str = Field(min_length=1, max_length=128)

    @field_validator("message")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must not be blank.")
        return value

    @field_validator("timezone")
    @classmethod
    def require_iana_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Timezone must be a valid IANA name.") from exc
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
    state: EventWorkflowState


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


def _development_provider(state: EventWorkflowState, context: RequestContext) -> ScriptedEventProvider:
    """Return a per-request scripted provider; it stores no session state."""
    draft = state.draft
    patch = {}
    if not draft.title:
        patch["title"] = translate(MessageId.DEMO_TITLE, context.language)
    if draft.start_date is None:
        patch["start_date"] = (context.now + timedelta(days=7)).date().isoformat()
    if draft.start_time is None:
        patch["start_time"] = time(12, 0).isoformat(timespec="minutes")
    if not draft.timezone:
        patch["timezone"] = context.timezone

    if patch:
        return ScriptedEventProvider([
            ToolCall(name="update_event_draft", arguments={"patch": patch})
        ])
    if draft.reminders is None:
        return ScriptedEventProvider([
            ToolCall(name="update_event_draft", arguments={
                "patch": {"reminders": [{"minutes_before": 60}]}
            })
        ])
    return ScriptedEventProvider([
        ToolCall(name="ask_event_clarification", arguments={
            "question": translate(MessageId.API_DEMO_LIMIT, context.language)
        })
    ])


def create_app(settings: APISettings | None = None) -> FastAPI:
    configuration = settings or APISettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.http_client = None
        if configuration.ollama_model:
            app.state.http_client = httpx.AsyncClient(
                base_url=configuration.ollama_base_url,
                timeout=httpx.Timeout(60.0),
            )
        try:
            yield
        finally:
            client = app.state.http_client
            if client is not None:
                await client.aclose()

    app = FastAPI(title="Kairos drafting API", lifespan=lifespan)
    app.state.configuration = configuration

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/workflow/turn")
    async def workflow_turn(body: WorkflowTurnRequest, request: Request) -> StreamingResponse:
        state = body.state or EventWorkflowState()
        now = datetime.now(ZoneInfo(body.timezone))
        context = RequestContext(now=now, language=body.language, timezone=body.timezone)
        configured = request.app.state.configuration
        if configured.ollama_model:
            provider = OllamaEventProvider(
                configured.ollama_model,
                request.app.state.http_client,
            )
        else:
            provider = _development_provider(state, context)
        workflow = EventWorkflow(provider)

        async def stream() -> AsyncIterator[str]:
            try:
                async for item in workflow.stream_advance(state, body.message, context):
                    if item.kind == "progress":
                        yield _encode_sse(ProgressSSE(message=item.message))
                    elif item.kind == "text":
                        yield _encode_sse(TextSSE(text=item.text))
                    elif item.kind == "completed":
                        yield _encode_sse(CompletedSSE(state=item.state))
            except WorkflowError as exc:
                yield _encode_sse(ErrorSSE(code=exc.code.value, message=exc.text(body.language)))
            except Exception as exc:
                logger.error(
                    "Unhandled error while streaming a workflow turn (%s)",
                    type(exc).__name__,
                )
                yield _encode_sse(ErrorSSE(
                    code="internal_error",
                    message=translate(MessageId.API_INTERNAL_ERROR, body.language),
                ))

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
