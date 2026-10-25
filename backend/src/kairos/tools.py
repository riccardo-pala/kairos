"""Explicit registry of typed handlers exposed to the model for this workflow."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, time
from typing import Generic, TypeVar

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
            arguments = call.arguments
            if call.name == "update_event_draft":
                arguments = self._adapt_legacy_task_list(arguments, state, context)
            return tool.execute(arguments, state.model_copy(deep=True), context)
        except ValidationError as exc:
            raise WorkflowError(MessageId.INVALID_ARGUMENTS) from exc

    @staticmethod
    def _adapt_legacy_task_list(arguments: dict, state: EventWorkflowState, context: RequestContext) -> dict:
        """Adapt old full-list proposals to safe explicit operations."""
        patch = arguments.get("patch")
        if not isinstance(patch, dict) or not isinstance(patch.get("tasks"), list):
            return arguments

        proposed = [EventTask.model_validate(item) for item in patch["tasks"]]
        current = list(state.draft.tasks)
        new_tasks = []
        for proposed_task in proposed:
            key = ToolRegistry._task_key(proposed_task)
            match = next((i for i, task in enumerate(current) if ToolRegistry._task_key(task) == key), None)
            if match is None:
                new_tasks.append(proposed_task)
            else:
                current.pop(match)

        normalized_patch = {key: value for key, value in patch.items() if key != "tasks"}
        normalized = arguments.copy()
        normalized["patch"] = normalized_patch
        raw_operations = arguments.get("task_operations") or {}
        if not isinstance(raw_operations, dict):
            return arguments  # Preserve the malformed value for normal schema validation.
        operations = raw_operations.copy()
        raw_additions = operations.get("add", [])
        explicit_removals = operations.get("remove", [])
        if not isinstance(raw_additions, list) or not isinstance(explicit_removals, list):
            return arguments
        additions = list(raw_additions)
        existing_additions = {
            ToolRegistry._task_key(EventTask.model_validate(item)) for item in additions
        }
        removed_descriptions = {
            " ".join(item.split()).casefold()
            for item in explicit_removals
            if isinstance(item, str)
        }
        for task in new_tasks:
            key = ToolRegistry._task_key(task)
            if key not in existing_additions and key[0] not in removed_descriptions:
                additions.append(task.model_dump())
                existing_additions.add(key)
        operations["add"] = additions
        normalized["task_operations"] = operations

        has_explicit_remove = bool(explicit_removals)
        if current and not new_tasks and not has_explicit_remove and not normalized.get("clarification"):
            try:
                language = Language(arguments.get("conversation_language"))
            except (TypeError, ValueError):
                language = state.conversation_language or context.language
            normalized["clarification"] = translate(MessageId.TASK_REMOVAL_AMBIGUOUS, language)
        return normalized

    @staticmethod
    def _task_key(task: EventTask) -> tuple[str, str]:
        return (" ".join(task.description.split()).casefold(), task.timing)


class EventDraftPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: NonEmptyText | None = None
    start_date: date | None = None
    start_time: time | None = None
    timezone: str | None = None
    location: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0, strict=True)
    reminders: list[ReminderDraft] | None = None


class TaskOperations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    add: list[EventTask] = Field(
        default_factory=list,
        description="Explicit new activities only; existing activities are preserved.",
    )
    remove: list[NonEmptyText] = Field(
        default_factory=list,
        description="Exact descriptions of uniquely identified existing activities to remove.",
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
    removal_is_ambiguous = False
    for requested in arguments.task_operations.remove:
        key = " ".join(requested.split()).casefold()
        matches = [index for index, task in enumerate(tasks)
                   if " ".join(task.description.split()).casefold() == key]
        if len(matches) != 1:
            removal_is_ambiguous = True
            break
        tasks.pop(matches[0])
    if removal_is_ambiguous:
        tasks = list(state.draft.tasks)
    else:
        existing = {
            (" ".join(task.description.split()).casefold(), task.timing)
            for task in tasks
        }
        for task in arguments.task_operations.add:
            key = (" ".join(task.description.split()).casefold(), task.timing)
            if key not in existing:
                tasks.append(task)
                existing.add(key)
    data["tasks"] = tasks
    candidate = EventDraft.model_validate(data)
    language = arguments.conversation_language or state.conversation_language or context.language
    return ToolResult(
        draft=candidate,
        clarification=(
            arguments.clarification
            or (translate(MessageId.TASK_REMOVAL_AMBIGUOUS, language) if removal_is_ambiguous else None)
        ),
        conversation_language=arguments.conversation_language,
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
                "Update explicit non-task event fields in patch; change activities only with "
                "top-level task_operations.add/remove. Omit unchanged fields. Never save or schedule an event."
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
