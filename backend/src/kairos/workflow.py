"""One model proposal per turn; Python owns validation and workflow state."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, time, timedelta
import re
import unicodedata
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kairos.contracts import (
    EventProvider,
    EventWorkflowState,
    RequestContext,
    ToolCall,
    WorkflowError,
    WorkflowEvent,
)
from kairos.i18n import Language, MessageId, translate
from kairos.models.actions import (
    AddReminderAction,
    AddTaskAction,
    ClearRemindersAction,
    DraftAction,
    SetDateAction,
    SetDurationAction,
    SetLocationAction,
    SetTimeAction,
    SetTitleAction,
)
from kairos.models.event import EventDraft, EventTask, ReminderDraft
from kairos.tools import ToolRegistry, event_tools, message_requests_removal


_REMINDER_INTERVAL = re.compile(
    r"(?<!\w)(?P<amount>\d+)\s*(?P<unit>minutes?|mins?|minuti|minuto|"
    r"hours?|hrs?|ora|ore|giorno|giorni|days?|settimana|settimane|weeks?)\s*(?:prima|before)\b",
    re.IGNORECASE,
)
_CLOCK_TIME = re.compile(
    r"\b(?:alle?|all'|ore|at|around)\s*\d{1,2}(?::\d{2})?(?:\s*(?:am|pm))?\b|"
    r"\b\d{1,2}:\d{2}\b",
    re.IGNORECASE,
)
_REMINDER_ADD_CUE = re.compile(
    r"\b(?:aggiungi(?:\s+anche)?|add(?:\s+also)?)\b.{0,30}\b(?:promemoria|reminder)\b",
    re.IGNORECASE,
)


def reminder_offsets_from_message(message: str) -> list[tuple[int, tuple[int, int]]]:
    """Read explicit numeric reminder intervals without asking the model to do arithmetic."""
    multipliers = {
        "minute": 1, "minutes": 1, "min": 1, "mins": 1, "minuto": 1, "minuti": 1,
        "hour": 60, "hours": 60, "hr": 60, "hrs": 60, "ora": 60, "ore": 60,
        "day": 1440, "days": 1440, "giorno": 1440, "giorni": 1440,
        "week": 10080, "weeks": 10080, "settimana": 10080, "settimane": 10080,
    }
    matches = []
    for match in _REMINDER_INTERVAL.finditer(message):
        unit = match.group("unit").casefold()
        matches.append((int(match.group("amount")) * multipliers[unit], match.span()))
    return matches


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
        self,
        state: EventWorkflowState,
        message: str,
        context: RequestContext,
        *,
        task_id: UUID | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        self._validate_request(state, message, context)
        if task_id is not None and not state.pending_task_removal:
            raise WorkflowError(MessageId.INVALID_ARGUMENTS)
        pending_tasks = [
            task for task in state.draft.tasks if task.id in state.pending_task_removal
        ]
        if state.pending_task_removal and (
            task_id is not None
            or self._is_cancel_selection(message)
            or self._task_selected_by_message(message, pending_tasks) is not None
        ):
            yield WorkflowEvent(
                kind="completed",
                state=self._resolve_task_removal(state, message, context, task_id),
            )
            return
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
            raise WorkflowError(MessageId.TOOL_COUNT)
        yield WorkflowEvent(
            kind="progress", message=translate(MessageId.PROGRESS_VALIDATE, context.language)
        )
        call = self._prepare_model_call(calls[0], state, context, message)
        turn_context = context.model_copy(update={"current_message": message})
        result = self.tools.execute(call, state, turn_context)
        candidate = result.draft
        if candidate.timezone is None:
            candidate.timezone = context.timezone
        if has_reminder_in_past(candidate, context.now):
            raise WorkflowError(MessageId.REMINDER_IN_PAST)
        language = result.conversation_language or state.conversation_language or context.language
        requested_removal = message_requests_removal(message)
        pending_removal = result.pending_task_removal
        if state.pending_task_removal and not requested_removal:
            pending_removal = state.pending_task_removal
        question = result.clarification or self._draft_validation_question(candidate, language)
        if pending_removal:
            question = self._task_removal_question(candidate, pending_removal, language)
        status = self._draft_status(candidate, question, pending_removal)
        completed = EventWorkflowState(
            draft=candidate,
            status=status,
            question=question,
            conversation_language=language,
            turns=state.turns + 1,
            pending_task_removal=pending_removal,
        )
        yield WorkflowEvent(kind="completed", state=completed)

    @staticmethod
    def apply_action(
        state: EventWorkflowState,
        action: DraftAction,
        context: RequestContext,
        *,
        max_turns: int = 20,
    ) -> EventWorkflowState:
        """Apply a playground template directly, without a model/provider call."""
        if state.turns >= max_turns:
            raise WorkflowError(MessageId.TURN_LIMIT)
        if isinstance(action, SetTitleAction):
            updates = {"title": action.value}
        elif isinstance(action, SetDateAction):
            updates = {"start_date": action.value}
        elif isinstance(action, SetTimeAction):
            updates = {"start_time": action.value}
        elif isinstance(action, SetLocationAction):
            updates = {"location": action.value}
        elif isinstance(action, SetDurationAction):
            updates = {"duration_minutes": action.value}
        elif isinstance(action, AddReminderAction):
            reminders = list(state.draft.reminders or [])
            if not any(item.minutes_before == action.minutes_before for item in reminders):
                reminders.append(ReminderDraft(minutes_before=action.minutes_before))
            updates = {"reminders": reminders}
        elif isinstance(action, AddTaskAction):
            tasks = list(state.draft.tasks)
            if not any(
                item.description.casefold() == action.description.casefold()
                and item.timing == action.timing
                for item in tasks
            ):
                tasks.append(EventTask(description=action.description, timing=action.timing))
            updates = {"tasks": tasks}
        elif isinstance(action, ClearRemindersAction):
            updates = {"reminders": []}
        else:
            raise WorkflowError(MessageId.INVALID_ARGUMENTS)

        candidate = EventDraft.model_validate(state.draft.model_dump() | updates)
        if candidate.timezone is None:
            candidate.timezone = context.timezone
        if has_reminder_in_past(candidate, context.now):
            raise WorkflowError(MessageId.REMINDER_IN_PAST)
        language = state.conversation_language or context.language
        pending_removal = state.pending_task_removal
        question = EventWorkflow._draft_validation_question(candidate, language)
        if pending_removal:
            question = EventWorkflow._task_removal_question(candidate, pending_removal, language)
        return EventWorkflowState(
            draft=candidate,
            status=EventWorkflow._draft_status(candidate, question, pending_removal),
            question=question,
            conversation_language=language,
            turns=state.turns + 1,
            pending_task_removal=pending_removal,
        )

    @staticmethod
    def _draft_status(draft: EventDraft, question: str | None, pending_removal: list[UUID]) -> str:
        return (
            "ready_for_review"
            if EventWorkflow._draft_is_ready(draft) and question is None and not pending_removal
            else "collecting"
        )

    @staticmethod
    def _draft_is_ready(draft: EventDraft) -> bool:
        if not draft.title or draft.start_date is None or draft.start_time is None or not draft.timezone:
            return False
        try:
            ZoneInfo(draft.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            return False
        return not time_needs_clarification(draft)

    @staticmethod
    def _draft_validation_question(draft: EventDraft, language: Language) -> str | None:
        if draft.timezone:
            try:
                ZoneInfo(draft.timezone)
            except (ZoneInfoNotFoundError, ValueError):
                return translate(MessageId.TIMEZONE, language)
        if draft.start_date is not None and draft.start_time is not None:
            if time_needs_clarification(draft):
                return translate(MessageId.TIME, language)
        return None

    async def advance(
        self,
        state: EventWorkflowState,
        message: str,
        context: RequestContext,
        *,
        task_id: UUID | None = None,
    ) -> EventWorkflowState:
        """Compatibility convenience that consumes the same streaming workflow."""
        completed = None
        async for event in self.stream_advance(state, message, context, task_id=task_id):
            if event.kind == "completed":
                completed = event.state
        if completed is None:
            raise WorkflowError(MessageId.INVALID_TOOL_CALL)
        return completed

    @staticmethod
    def _task_removal_question(draft, options, language: Language) -> str:
        descriptions = {task.id: task.description for task in draft.tasks}
        choices = [
            f"{index}. {descriptions[task_id]}"
            for index, task_id in enumerate(options, start=1)
            if task_id in descriptions
        ]
        return f"{translate(MessageId.TASK_REMOVAL_AMBIGUOUS, language)}\n" + "\n".join(choices)

    @staticmethod
    def _resolve_task_removal(
        state: EventWorkflowState,
        message: str,
        context: RequestContext,
        task_id: UUID | None,
    ) -> EventWorkflowState:
        options = [task for task in state.draft.tasks if task.id in state.pending_task_removal]
        selected = next((task for task in options if task.id == task_id), None) if task_id else None
        if task_id is None:
            selected = EventWorkflow._task_selected_by_message(message, options)

        if selected is not None:
            draft = state.draft.model_copy(update={
                "tasks": [task for task in state.draft.tasks if task.id != selected.id]
            })
            language = state.conversation_language or context.language
            question = EventWorkflow._draft_validation_question(draft, language)
            return state.model_copy(update={
                "draft": draft,
                "status": EventWorkflow._draft_status(draft, question, []),
                "question": question,
                "pending_task_removal": [],
                "turns": state.turns + 1,
            })

        if EventWorkflow._is_cancel_selection(message):
            language = state.conversation_language or context.language
            question = EventWorkflow._draft_validation_question(state.draft, language)
            return state.model_copy(update={
                "status": EventWorkflow._draft_status(state.draft, question, []),
                "question": question,
                "pending_task_removal": [],
                "turns": state.turns + 1,
            })

        if not options:
            language = state.conversation_language or context.language
            question = EventWorkflow._draft_validation_question(state.draft, language)
            return state.model_copy(update={
                "status": EventWorkflow._draft_status(state.draft, question, []),
                "question": question,
                "pending_task_removal": [],
                "turns": state.turns + 1,
            })

        raise WorkflowError(MessageId.INVALID_ARGUMENTS)

    @staticmethod
    def _task_selected_by_message(message: str, options):
        normalized = " ".join(unicodedata.normalize("NFKC", message).casefold().split())
        if re.fullmatch(r"(?:#\s*)?([1-9][0-9]*)\.?", normalized):
            index = int(re.fullmatch(r"(?:#\s*)?([1-9][0-9]*)\.?", normalized).group(1))
            return options[index - 1] if index <= len(options) else None
        matches = [
            task for task in options
            if " ".join(unicodedata.normalize("NFKC", task.description).casefold().split()) == normalized
        ]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _is_cancel_selection(message: str) -> bool:
        normalized = " ".join(unicodedata.normalize("NFKC", message).casefold().split())
        return normalized in {"annulla", "annulla scelta", "lascia stare", "non importa", "cancel", "cancel selection"}

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
    def _prepare_model_call(
        call: ToolCall, state: EventWorkflowState, context: RequestContext, message: str
    ) -> ToolCall:
        """Preserve all model-extracted facts and deterministically apply clear intervals."""
        if call.name != "update_event_draft":
            return call
        arguments = call.arguments
        patch = arguments.get("patch")
        if not isinstance(patch, dict):
            return call  # Let the normal tool validation report malformed arguments.

        safe_arguments = dict(arguments)
        safe_patch = dict(patch)
        safe_arguments["patch"] = safe_patch

        intervals = reminder_offsets_from_message(message)
        if intervals:
            offsets = [offset for offset, _ in intervals]
            if _REMINDER_ADD_CUE.search(message) and state.draft.reminders:
                offsets = list(dict.fromkeys(
                    [item.minutes_before for item in state.draft.reminders] + offsets
                ))
            safe_patch["reminders"] = [{"minutes_before": offset} for offset in offsets]
            without_intervals = _REMINDER_INTERVAL.sub(" ", message)
            if not _CLOCK_TIME.search(without_intervals):
                safe_patch.pop("start_time", None)
            return ToolCall(name=call.name, arguments=safe_arguments)

        reminder_time_value = patch.get("start_time")
        legacy_reminder_question = state.question == translate(
            MessageId.REMINDERS, state.conversation_language or context.language
        )
        explicit_reminder_clock = bool(re.search(
            r"\b(?:promemoria|reminder)\b.{0,20}\b(?:alle?|at)\s*\d",
            message,
            re.IGNORECASE,
        ))
        has_clock_time = (
            "start_time" in patch
            and reminder_time_value is not None
            and (legacy_reminder_question or explicit_reminder_clock)
        )
        reminders_supplied = "reminders" in patch
        if has_clock_time:
            try:
                reminder_time = (
                    reminder_time_value
                    if isinstance(reminder_time_value, time)
                    else time.fromisoformat(reminder_time_value)
                )
            except (TypeError, ValueError):
                safe_patch.pop("start_time", None)
                safe_arguments["clarification"] = translate(
                    MessageId.REMINDER_CLOCK_TIME_UNCLEAR,
                    state.conversation_language or context.language,
                )
                return ToolCall(name=call.name, arguments=safe_arguments)

            offset = EventWorkflow._minutes_before_for_clock_time(state.draft, reminder_time)
            if offset is None:
                safe_patch.pop("start_time", None)
                safe_arguments["clarification"] = translate(
                    MessageId.REMINDER_CLOCK_TIME_UNCLEAR,
                    state.conversation_language or context.language,
                )
                return ToolCall(name=call.name, arguments=safe_arguments)
            if reminders_supplied:
                requested = patch["reminders"]
                if requested is None:
                    reminders = []
                elif not isinstance(requested, list):
                    safe_patch["reminders"] = requested
                    return ToolCall(name=call.name, arguments=safe_arguments)
                elif not requested:
                    safe_patch.pop("start_time", None)
                    safe_arguments["clarification"] = translate(
                        MessageId.REMINDER_CLOCK_TIME_UNCLEAR,
                        state.conversation_language or context.language,
                    )
                    return ToolCall(name=call.name, arguments=safe_arguments)
                else:
                    reminders = list(requested)
            else:
                reminders = []
            if not any(
                isinstance(item, dict) and item.get("minutes_before") == offset
                for item in reminders
            ):
                reminders.append({"minutes_before": offset})
            safe_patch["reminders"] = reminders
            safe_patch.pop("start_time", None)

        return ToolCall(name=call.name, arguments=safe_arguments)

    @staticmethod
    def _minutes_before_for_clock_time(draft: EventDraft, reminder_time: time) -> int | None:
        if draft.start_date is None or draft.start_time is None or draft.timezone is None:
            return None
        try:
            zone = ZoneInfo(draft.timezone)
            reminder_draft = EventDraft(
                start_date=draft.start_date,
                start_time=reminder_time,
                timezone=draft.timezone,
            )
            if time_needs_clarification(draft) or time_needs_clarification(reminder_draft):
                return None

            event_local = draft.local_starts_at
            reminder_local = datetime.combine(draft.start_date, reminder_time)
            event_instant = (
                event_local.replace(tzinfo=zone)
                if event_local.tzinfo is None
                else event_local
            ).astimezone(UTC)
            reminder_instant = (
                reminder_local.replace(tzinfo=zone)
                if reminder_local.tzinfo is None
                else reminder_local
            ).astimezone(UTC)
        except (ZoneInfoNotFoundError, ValueError):
            return None

        delta_seconds = (event_instant - reminder_instant).total_seconds()
        if delta_seconds <= 0 or delta_seconds % 60:
            return None
        return int(delta_seconds // 60)
