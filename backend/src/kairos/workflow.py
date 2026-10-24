"""One model proposal per turn; Python owns validation and workflow state."""

from datetime import UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kairos.contracts import EventProvider, EventWorkflowState, RequestContext, WorkflowError
from kairos.i18n import MessageId, localized
from kairos.models.event import EventDraft
from kairos.tools import ToolRegistry, event_tools


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
    def __init__(
        self, provider: EventProvider, max_turns: int = 20, tools: ToolRegistry | None = None
    ):
        self.provider = provider
        self.max_turns = max_turns
        self.tools = tools if tools is not None else event_tools()

    async def advance(
        self, state: EventWorkflowState, message: str, context: RequestContext
    ) -> EventWorkflowState:
        if not message.strip() or len(message) > 8_000:
            raise WorkflowError(MessageId.INVALID_MESSAGE)
        if state.turns >= self.max_turns:
            raise WorkflowError(MessageId.TURN_LIMIT)
        try:
            ZoneInfo(context.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise WorkflowError(MessageId.INVALID_TIMEZONE) from exc

        schemas = self.tools.schemas(state.model_copy(deep=True))
        if not schemas:
            raise WorkflowError(MessageId.NO_TOOLS)
        call = await self.provider.propose(
            message, state.model_copy(deep=True), context, schemas
        )
        result = self.tools.execute(call, state, context)
        candidate = result.draft
        if candidate.timezone is None:
            candidate.timezone = context.timezone
        question = result.clarification
        if question is None:
            missing = self._next_question(candidate)
            if missing:
                question = localized(missing)
        return EventWorkflowState(
            draft=candidate,
            status="collecting" if question else "ready_for_review",
            question=question,
            turns=state.turns + 1,
        )

    @staticmethod
    def _next_question(draft: EventDraft) -> MessageId | None:
        if not draft.title:
            return MessageId.TITLE
        if draft.starts_at is None:
            return MessageId.STARTS_AT
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
