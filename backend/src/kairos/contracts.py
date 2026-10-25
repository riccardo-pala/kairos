"""Conversation contracts independent of model adapters and tool handlers."""

from collections.abc import AsyncIterator
from typing import Literal, Protocol

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from kairos.i18n import Language, MessageId, NonEmptyText, translate
from kairos.models.event import EventDraft


class WorkflowError(Exception):
    def __init__(self, code: MessageId):
        self.code = code
        super().__init__(translate(code, Language.EN))

    def text(self, language: Language | str) -> str:
        return translate(self.code, language)


class RequestContext(BaseModel):
    now: AwareDatetime
    language: Language = Language.IT
    timezone: str


class ToolCall(BaseModel):
    name: str
    arguments: dict


class EventWorkflowState(BaseModel):
    draft: EventDraft = Field(default_factory=EventDraft)
    status: Literal["collecting", "ready_for_review"] = "collecting"
    question: NonEmptyText | None = None
    conversation_language: Language | None = None
    turns: int = 0


class ToolResult(BaseModel):
    draft: EventDraft
    clarification: NonEmptyText | None = None
    conversation_language: Language | None = None


class ProviderEvent(BaseModel):
    kind: Literal["text", "tool_call"]
    text: str | None = None
    tool_call: ToolCall | None = None

    @model_validator(mode="after")
    def require_payload_for_kind(self):
        if self.kind == "text" and (not self.text or self.tool_call is not None):
            raise ValueError("Text events require text and cannot carry a tool call.")
        if self.kind == "tool_call" and (self.tool_call is None or self.text is not None):
            raise ValueError("Tool-call events require exactly one tool call.")
        return self


class WorkflowEvent(BaseModel):
    kind: Literal["progress", "text", "completed"]
    message: str | None = None
    text: str | None = None
    state: EventWorkflowState | None = None

    @model_validator(mode="after")
    def require_payload_for_kind(self):
        if self.kind == "progress" and (not self.message or self.text is not None or self.state is not None):
            raise ValueError("Progress events require a message only.")
        if self.kind == "text" and (not self.text or self.message is not None or self.state is not None):
            raise ValueError("Text events require text only.")
        if self.kind == "completed" and (self.state is None or self.message is not None or self.text is not None):
            raise ValueError("Completed events require a state only.")
        return self


class EventProvider(Protocol):
    def stream_propose(
        self, message: str, state: EventWorkflowState, context: RequestContext, tools: list[dict]
    ) -> AsyncIterator[ProviderEvent]: ...
