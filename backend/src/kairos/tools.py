"""Explicit registry of typed handlers exposed to the model for this workflow."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from kairos.contracts import EventWorkflowState, RequestContext, ToolCall, ToolResult, WorkflowError
from kairos.i18n import LocalizedText, MessageId
from kairos.models.event import EventDraft


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


class UpdateEventArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patch: EventDraft
    clarification: LocalizedText | None = None


class AskClarificationArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: LocalizedText


def update_event_draft(
    arguments: UpdateEventArguments, state: EventWorkflowState, context: RequestContext
) -> ToolResult:
    patch = arguments.patch.model_dump(exclude_unset=True)
    candidate = EventDraft.model_validate(state.draft.model_dump() | patch)
    return ToolResult(draft=candidate, clarification=arguments.clarification)


def ask_event_clarification(
    arguments: AskClarificationArguments, state: EventWorkflowState, context: RequestContext
) -> ToolResult:
    return ToolResult(draft=state.draft, clarification=arguments.question)


def event_tools() -> ToolRegistry:
    return ToolRegistry([
        ToolDefinition(
            name="update_event_draft",
            description="Update explicit event fields. Omit unchanged fields. Never save or schedule an event.",
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
