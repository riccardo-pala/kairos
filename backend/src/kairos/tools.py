"""Explicit registry of typed handlers exposed to the model for this workflow."""

import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, time
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from kairos.contracts import EventWorkflowState, RequestContext, ToolCall, ToolResult, WorkflowError
from kairos.i18n import Language, MessageId, NonEmptyText, translate
from kairos.models.event import EventDraft, EventTask, ReminderDraft


Arguments = TypeVar("Arguments", bound=BaseModel)


@dataclass(frozen=True)
class ToolDefinition(Generic[Arguments]):
    name: str
    description: str
    arguments_model: type[Arguments]
    handler: Callable[[Arguments, EventWorkflowState, RequestContext], ToolResult]
    available_when: Callable[[EventWorkflowState], bool] = lambda state: True

    def schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.description,
            "parameters": self.arguments_model.model_json_schema(),
        }}

    def execute(self, arguments: dict, state: EventWorkflowState, context: RequestContext) -> ToolResult:
        parsed = self.arguments_model.model_validate(arguments)
        return self.handler(parsed, state, context)


class ToolRegistry:
    def __init__(self, definitions: Sequence[ToolDefinition]):
        self._tools: dict[str, ToolDefinition] = {}
        for tool in definitions:
            if tool.name in self._tools:
                raise ValueError(f"Duplicate tool name: {tool.name}")
            self._tools[tool.name] = tool

    def schemas(self, state: EventWorkflowState) -> list[dict]:
        return [tool.schema() for tool in self._tools.values() if tool.available_when(state)]

    def execute(self, call: ToolCall, state: EventWorkflowState, context: RequestContext) -> ToolResult:
        tool = self._tools.get(call.name)
        if tool is None or not tool.available_when(state):
            raise WorkflowError(MessageId.TOOL_NOT_ALLOWED)
        try:
            return tool.execute(call.arguments, state.model_copy(deep=True), context)
        except ValidationError as exc:
            raise WorkflowError(MessageId.INVALID_ARGUMENTS) from exc


class EventDraftPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: NonEmptyText | None = None
    start_date: date | None = None
    start_time: time | None = Field(
        default=None,
        description="Event's local start time. Reminder intervals belong in patch.reminders.",
    )
    timezone: str | None = None
    location: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0, strict=True)
    reminders: list[ReminderDraft] | None = None


class TaskAddition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: NonEmptyText
    timing: Literal["before", "after"]
    evidence: NonEmptyText = Field(
        description="Exact quote from the current user message containing the action and before/after relation."
    )


class TaskOperations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    add: list[TaskAddition] = Field(
        default_factory=list,
        description=(
            "Explicit new activities only. Each addition must quote exact source evidence "
            "containing both the separate action and its before/after relation."
        ),
    )
    remove: bool = Field(
        default=False,
        strict=True,
        description="True only when the user's message explicitly requests activity removal.",
    )
    remove_evidence: NonEmptyText | None = Field(
        default=None,
        description="Exact quote from the current user message that explicitly requests removal.",
    )


class UpdateEventArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patch: EventDraftPatch
    task_operations: TaskOperations = Field(default_factory=TaskOperations)
    clarification: NonEmptyText | None = None
    conversation_language: Language | None = None


class AskClarificationArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: NonEmptyText
    conversation_language: Language | None = None


def update_event_draft(
    arguments: UpdateEventArguments, state: EventWorkflowState, context: RequestContext
) -> ToolResult:
    patch = arguments.patch.model_dump(exclude_unset=True)
    data = state.draft.model_dump() | patch
    tasks = list(state.draft.tasks)
    pending_removal: list[UUID] = []
    clarification = arguments.clarification
    language = arguments.conversation_language or state.conversation_language or context.language

    if arguments.task_operations.remove:
        if not _is_grounded_removal(arguments.task_operations.remove_evidence, context.current_message):
            if message_requests_removal(context.current_message):
                clarification = clarification or translate(MessageId.TASK_REMOVAL_UNCLEAR, language)
        elif not tasks:
            clarification = clarification or translate(MessageId.TASK_REMOVAL_NONE, language)
        else:
            exact_matches = [task for task in tasks if _contains_quote(context.current_message, task.description)]
            if len(exact_matches) == 1:
                tasks = [task for task in tasks if task.id != exact_matches[0].id]
            elif len(tasks) == 1:
                tasks = []
            else:
                pending_removal = [task.id for task in tasks]

    existing = {(_normalize_quote(task.description), task.timing) for task in tasks}
    for proposal in arguments.task_operations.add:
        if not _is_grounded_addition(proposal, context.current_message, data.get("title")):
            continue
        key = (_normalize_quote(proposal.description), proposal.timing)
        if key not in existing:
            tasks.append(EventTask(description=proposal.description, timing=proposal.timing))
            existing.add(key)

    data["tasks"] = tasks
    candidate = EventDraft.model_validate(data)
    return ToolResult(
        draft=candidate,
        clarification=clarification,
        conversation_language=arguments.conversation_language,
        pending_task_removal=pending_removal,
    )


def _normalize_quote(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def _contains_quote(message: str, quote: str | None) -> bool:
    if not quote:
        return False
    phrase = re.escape(_normalize_quote(quote))
    return bool(re.search(rf"(?<!\w){phrase}(?!\w)", _normalize_quote(message)))


_REMOVAL_CUE = re.compile(
    r"\b(?:togli(?:ere|mi)?|rimuovi(?:re|mi)?|cancell(?:a|are|ami)|elimin(?:a|are|ami)|"
    r"remove|delete|erase)\b",
    re.IGNORECASE,
)
_NEGATED_REMOVAL = re.compile(
    r"\b(?:non|don't|do not|never|not)\b[^.!?]{0,24}\b(?:togli|rimuovi|cancell|elimin|remove|delete|erase)",
    re.IGNORECASE,
)


def _is_grounded_removal(evidence: str | None, message: str) -> bool:
    return (
        _contains_quote(message, evidence)
        and bool(_REMOVAL_CUE.search(evidence or ""))
        and not _NEGATED_REMOVAL.search(evidence or "")
    )


def message_requests_removal(message: str) -> bool:
    return bool(_REMOVAL_CUE.search(message)) and not _NEGATED_REMOVAL.search(message)


_RELATION_CUES = {
    "before": re.compile(
        r"\b(?:prima(?:\s+(?:di|che))?|in\s+anticipo|precedent(?:e|i|emente)|propedeutic[oa]|"
        r"before(?:\s+(?:the|that|i|we|you))?|prior\s+to|ahead\s+of|preparatory|in\s+advance)\b",
        re.IGNORECASE,
    ),
    "after": re.compile(
        r"\b(?:dopo(?:\s+(?:aver|avere|che))?|successiv[oa](?:mente)?|poi|"
        r"after(?:\s+(?:the|that|i|we|you))?|once|afterwards|later|then|subsequent(?:ly)?)\b",
        re.IGNORECASE,
    ),
}


def _is_grounded_addition(proposal: TaskAddition, message: str, title: str | None) -> bool:
    evidence = proposal.evidence
    normalized_description = _normalize_quote(proposal.description)
    normalized_title = _normalize_quote(title or "")
    return (
        _contains_quote(message, evidence)
        and _contains_quote(evidence, proposal.description)
        and normalized_description != normalized_title
        and bool(_RELATION_CUES[proposal.timing].search(evidence))
    )


def ask_event_clarification(
    arguments: AskClarificationArguments, state: EventWorkflowState, context: RequestContext
) -> ToolResult:
    return ToolResult(
        draft=state.draft,
        clarification=arguments.question,
        conversation_language=arguments.conversation_language,
    )


def event_tools() -> ToolRegistry:
    return ToolRegistry([
        ToolDefinition(
            name="update_event_draft",
            description=(
                "Update every explicit event field from the current message in patch; omit unchanged fields. "
                "Use task_operations only for explicit separate before/after activities. Reminder intervals "
                "go in patch.reminders. Never save or schedule an event."
            ),
            arguments_model=UpdateEventArguments,
            handler=update_event_draft,
        ),
        ToolDefinition(
            name="ask_event_clarification",
            description="Ask for clarification when no event field can be safely updated. Leaves the draft unchanged.",
            arguments_model=AskClarificationArguments,
            handler=ask_event_clarification,
        ),
    ])
