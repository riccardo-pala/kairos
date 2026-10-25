"""One model proposal per turn; Python owns validation and workflow state."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kairos.contracts import (
    EventProvider,
    EventWorkflowState,
    RequestContext,
    WorkflowError,
    WorkflowEvent,
)
from kairos.i18n import MessageId, translate
from kairos.models.event import EventDraft
from kairos.tools import ToolRegistry, event_tools


def time_needs_clarification(draft: EventDraft) -> bool:
    """Reject nonexistent/ambiguous local times and offset/zone mismatches."""
    start = draft.local_starts_at
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


def has_reminder_in_past(draft: EventDraft, now: datetime) -> bool:
    """Whether any proposed reminder instant has already elapsed."""
    start = draft.local_starts_at
    if start is None or not draft.timezone or not draft.reminders:
        return False
    try:
        zone = ZoneInfo(draft.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return False  # The normal workflow will ask for a valid time zone.
    if time_needs_clarification(draft):
        return False  # Resolve DST/offset ambiguity before judging reminder times.
    if start.tzinfo is not None:
        event_instant = start.astimezone(UTC)
    else:
        event_instant = start.replace(tzinfo=zone).astimezone(UTC)
    now_instant = now.astimezone(UTC)
    return any(
        event_instant - timedelta(minutes=reminder.minutes_before) < now_instant
        for reminder in draft.reminders
    )


class EventWorkflow:
    def __init__(
        self, provider: EventProvider, max_turns: int = 20, tools: ToolRegistry | None = None
    ):
        self.provider = provider
        self.max_turns = max_turns
        self.tools = tools if tools is not None else event_tools()

    async def stream_advance(
        self, state: EventWorkflowState, message: str, context: RequestContext
    ) -> AsyncIterator[WorkflowEvent]:
        self._validate_request(state, message, context)
        yield WorkflowEvent(
            kind="progress", message=translate(MessageId.PROGRESS_START, context.language)
        )
        schemas = self.tools.schemas(state.model_copy(deep=True))
        if not schemas:
            raise WorkflowError(MessageId.NO_TOOLS)

        calls = []
        async for event in self.provider.stream_propose(
            message, state.model_copy(deep=True), context, schemas
        ):
            if event.kind == "text" and event.text:
                yield WorkflowEvent(kind="text", text=event.text)
            elif event.kind == "tool_call" and event.tool_call is not None:
                calls.append(event.tool_call)

        if len(calls) != 1:
            if state.draft.reminders is None and self._next_question(state.draft) == MessageId.REMINDERS:
                raise WorkflowError(MessageId.REMINDER_TOOL_COUNT)
            raise WorkflowError(MessageId.TOOL_COUNT)
        yield WorkflowEvent(
            kind="progress", message=translate(MessageId.PROGRESS_VALIDATE, context.language)
        )
        result = self.tools.execute(calls[0], state, context)
        candidate = result.draft
        if candidate.timezone is None:
            candidate.timezone = context.timezone
        if has_reminder_in_past(candidate, context.now):
            raise WorkflowError(MessageId.REMINDER_IN_PAST)
        language = result.conversation_language or state.conversation_language or context.language
        question = result.clarification
        if question is None:
            missing = self._next_question(candidate)
            if missing:
                question = translate(missing, language)
        completed = EventWorkflowState(
            draft=candidate,
            status="collecting" if question else "ready_for_review",
            question=question,
            conversation_language=language,
            turns=state.turns + 1,
        )
        yield WorkflowEvent(kind="completed", state=completed)

    async def advance(
        self, state: EventWorkflowState, message: str, context: RequestContext
    ) -> EventWorkflowState:
        """Compatibility convenience that consumes the same streaming workflow."""
        completed = None
        async for event in self.stream_advance(state, message, context):
            if event.kind == "completed":
                completed = event.state
        if completed is None:
            raise WorkflowError(MessageId.INVALID_TOOL_CALL)
        return completed

    def _validate_request(self, state: EventWorkflowState, message: str, context: RequestContext) -> None:
        if not message.strip() or len(message) > 8_000:
            raise WorkflowError(MessageId.INVALID_MESSAGE)
        if state.turns >= self.max_turns:
            raise WorkflowError(MessageId.TURN_LIMIT)
        try:
            ZoneInfo(context.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise WorkflowError(MessageId.INVALID_TIMEZONE) from exc

    @staticmethod
    def _next_question(draft: EventDraft) -> MessageId | None:
        if not draft.title:
            return MessageId.TITLE
        if draft.start_date is None:
            return MessageId.START_DATE
        if draft.start_time is None:
            return MessageId.START_TIME
        if draft.timezone is None:
            return MessageId.TIMEZONE
        try:
            ZoneInfo(draft.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            return MessageId.TIMEZONE
        if time_needs_clarification(draft):
            return MessageId.TIME
        if draft.reminders is None:
            return MessageId.REMINDERS
        return None
