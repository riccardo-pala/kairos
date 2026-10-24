"""One model proposal per turn; Python owns validation and workflow state."""

from datetime import UTC
from typing import Literal, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from kairos.models.event import EventDraft


class WorkflowError(Exception):
    """A turn failed. The caller retains the previous, unmodified state."""


class RequestContext(BaseModel):
    now: AwareDatetime
    language: Literal["it", "en"] = "it"
    timezone: str


class ToolCall(BaseModel):
    name: str
    arguments: dict


class UpdateEventArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patch: EventDraft
    clarification: str | None = Field(default=None, min_length=1, max_length=500)


class EventWorkflowState(BaseModel):
    draft: EventDraft = Field(default_factory=EventDraft)
    status: Literal["collecting", "ready_for_review"] = "collecting"
    question: str | None = None
    turns: int = 0


class EventProvider(Protocol):
    async def propose(
        self, message: str, state: EventWorkflowState, context: RequestContext
    ) -> ToolCall: ...


EVENT_TOOL = {
    "type": "function",
    "function": {
        "name": "update_event_draft",
        "description": "Propose changes to an event draft. Never save or schedule an event.",
        "parameters": UpdateEventArguments.model_json_schema(),
    },
}


QUESTIONS = {
    "title": ("Come vuoi chiamare l'impegno?", "What should this event be called?"),
    "starts_at": ("In quale data e a che ora?", "On which date and at what time?"),
    "timezone": ("Quale fuso orario devo usare?", "Which time zone should I use?"),
    "time": (
        "L'orario è ambiguo o non valido nel fuso indicato. Puoi precisarlo?",
        "The time is ambiguous or invalid in this time zone. Could you clarify it?",
    ),
    "reminders": (
        "Quando vuoi i promemoria? Puoi sceglierne più di uno, oppure nessuno.",
        "When would you like reminders? You can choose several, or none.",
    ),
}


def time_needs_clarification(draft: EventDraft) -> bool:
    """Reject nonexistent/ambiguous local times and offset/zone mismatches."""
    start = draft.starts_at
    if start is None or draft.timezone is None:
        return True
    zone = ZoneInfo(draft.timezone)
    if start.tzinfo is not None:
        local = start.astimezone(zone)
        return start.utcoffset() != local.utcoffset()
    candidates = set()
    for fold in (0, 1):
        instant = start.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None) == start:
            candidates.add(instant)
    return len(candidates) != 1


class EventWorkflow:
    def __init__(self, provider: EventProvider, max_turns: int = 20):
        self.provider = provider
        self.max_turns = max_turns

    async def advance(
        self, state: EventWorkflowState, message: str, context: RequestContext
    ) -> EventWorkflowState:
        if not message.strip() or len(message) > 8_000:
            raise WorkflowError("Message must contain between 1 and 8000 characters.")
        if state.turns >= self.max_turns:
            raise WorkflowError("Conversation turn limit reached; start a new draft.")
        try:
            ZoneInfo(context.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise WorkflowError("Invalid request time zone.") from exc

        # The provider receives a copy and cannot mutate the caller's state.
        call = await self.provider.propose(message, state.model_copy(deep=True), context)
        if call.name != "update_event_draft":
            raise WorkflowError("Tool is not allowed.")
        try:
            arguments = UpdateEventArguments.model_validate(call.arguments)
            # Missing fields are preserved; explicit null clears optional fields.
            patch = arguments.patch.model_dump(exclude_unset=True)
            candidate = EventDraft.model_validate(state.draft.model_dump() | patch)
        except ValidationError as exc:
            raise WorkflowError("Invalid tool arguments; the draft was not changed.") from exc

        if candidate.timezone is None:
            candidate.timezone = context.timezone
        question = arguments.clarification
        if question is None:
            missing = self._next_question(candidate)
            if missing:
                question = QUESTIONS[missing][0 if context.language == "it" else 1]
        return EventWorkflowState(
            draft=candidate,
            status="collecting" if question else "ready_for_review",
            question=question,
            turns=state.turns + 1,
        )

    @staticmethod
    def _next_question(draft: EventDraft) -> str | None:
        if not draft.title:
            return "title"
        if draft.starts_at is None:
            return "starts_at"
        if draft.timezone is None:
            return "timezone"
        try:
            ZoneInfo(draft.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            return "timezone"
        if time_needs_clarification(draft):
            return "time"
        if draft.reminders is None:
            return "reminders"
        return None
