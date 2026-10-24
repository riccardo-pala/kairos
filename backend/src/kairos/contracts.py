"""Conversation contracts independent of model adapters and tool handlers."""

from typing import Literal, Protocol

from pydantic import AwareDatetime, BaseModel, Field

from kairos.i18n import Language, LocalizedText, MessageId, translate
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
    question: LocalizedText | None = None
    turns: int = 0


class ToolResult(BaseModel):
    draft: EventDraft
    clarification: LocalizedText | None = None


class EventProvider(Protocol):
    async def propose(
        self, message: str, state: EventWorkflowState, context: RequestContext, tools: list[dict]
    ) -> ToolCall: ...
