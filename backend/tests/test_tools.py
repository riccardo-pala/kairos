import asyncio
from datetime import datetime

import pytest
from pydantic import BaseModel, ConfigDict

from kairos.contracts import EventWorkflowState, RequestContext, ToolCall, ToolResult, WorkflowError
from kairos.i18n import MessageId
from kairos.demo.provider import ScriptedEventProvider
from kairos.tools import ToolDefinition, ToolRegistry, event_tools
from kairos.workflow import EventWorkflow


def context():
    return RequestContext(now=datetime.fromisoformat("2026-10-24T12:00:00+02:00"), timezone="Europe/Rome")


def test_model_can_choose_clarification_instead_of_updating_the_draft():
    original = EventWorkflowState()
    call = ToolCall(name="ask_event_clarification", arguments={"question": "Quale venerdì intendi?"})
    workflow = EventWorkflow(ScriptedEventProvider([call]))
    state = asyncio.run(workflow.advance(original, "Venerdì ho una visita", context()))
    assert state.question == "Quale venerdì intendi?"
    assert state.conversation_language.value == "it"
    assert state.status == "collecting"
    assert original == EventWorkflowState()
    assert state.draft.title is None


@pytest.mark.parametrize("name,arguments", [
    ("ask_event_clarification", {"question": "  "}),
    ("update_event_draft", {"patch": {}, "clarification": "  "}),
])
def test_invalid_question_text_leaves_state_unchanged(name, arguments):
    original = EventWorkflowState()
    workflow = EventWorkflow(ScriptedEventProvider([ToolCall(name=name, arguments=arguments)]))
    with pytest.raises(WorkflowError) as error:
        asyncio.run(workflow.advance(original, "Venerdì", context()))
    assert error.value.code == MessageId.INVALID_ARGUMENTS
    assert original == EventWorkflowState()


class EmptyArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


def test_registered_but_unavailable_tool_is_neither_advertised_nor_executed():
    executed = []

    def handler(arguments, state, context):
        executed.append(True)
        return ToolResult(draft=state.draft)

    tool = ToolDefinition(
        name="review_only", description="Test-only tool", arguments_model=EmptyArguments,
        handler=handler, available_when=lambda state: state.status == "ready_for_review",
    )
    registry = ToolRegistry([tool])
    assert registry.schemas(EventWorkflowState()) == []
    with pytest.raises(WorkflowError) as error:
        registry.execute(ToolCall(name="review_only", arguments={}), EventWorkflowState(), context())
    assert error.value.code == MessageId.TOOL_NOT_ALLOWED
    assert executed == []
    ready = EventWorkflowState(status="ready_for_review")
    assert registry.schemas(ready)[0]["function"]["name"] == "review_only"
    registry.execute(ToolCall(name="review_only", arguments={}), ready, context())
    assert executed == [True]


def test_argument_validation_happens_before_the_handler():
    executed = []

    def handler(arguments, state, context):
        executed.append(True)
        return ToolResult(draft=state.draft)

    registry = ToolRegistry([ToolDefinition(
        name="test_tool", description="Test-only tool", arguments_model=EmptyArguments, handler=handler
    )])
    with pytest.raises(WorkflowError):
        registry.execute(ToolCall(name="test_tool", arguments={"unexpected": True}), EventWorkflowState(), context())
    assert executed == []


def test_duplicate_names_are_rejected_instead_of_overwriting_handlers():
    tool = ToolDefinition(
        name="same_name", description="Test-only tool", arguments_model=EmptyArguments,
        handler=lambda arguments, state, context: ToolResult(draft=state.draft),
    )
    with pytest.raises(ValueError, match="Duplicate"):
        ToolRegistry([tool, tool])


def test_no_available_tools_prevents_a_model_request():
    workflow = EventWorkflow(ScriptedEventProvider([]), tools=ToolRegistry([]))
    with pytest.raises(WorkflowError) as error:
        asyncio.run(workflow.advance(EventWorkflowState(), "Una visita", context()))
    assert error.value.code == MessageId.NO_TOOLS


def test_production_registry_exposes_both_event_capabilities():
    names = {schema["function"]["name"] for schema in event_tools().schemas(EventWorkflowState())}
    assert names == {"update_event_draft", "ask_event_clarification"}
