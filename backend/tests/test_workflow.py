import asyncio
from datetime import datetime
from kairos.contracts import ProviderEvent

import pytest

from kairos.models.event import EventDraft
from kairos.i18n import Language
from kairos.providers import ScriptedEventProvider
from kairos.workflow import EventWorkflow
from kairos.contracts import (
    EventWorkflowState,
    RequestContext,
    ToolCall,
    WorkflowError,
)


def context(language="it"):
    return RequestContext(
        now=datetime.fromisoformat("2026-10-24T12:00:00+02:00"),
        timezone="Europe/Rome",
        language=language,
    )


def call(patch, **kwargs):
    return ToolCall(name="update_event_draft", arguments={"patch": patch, **kwargs})


def advance(workflow, state, message="A user message", language="it"):
    return asyncio.run(workflow.advance(state, message, context(language)))


def event_fields(**overrides):
    return {"title": "Visita", "starts_at": "2026-10-31T14:30:00", **overrides}


def test_followup_preserves_event_and_tasks_and_asks_for_reminders():
    provider = ScriptedEventProvider([
        call(event_fields(tasks=[{"description": "Portare documenti", "timing": "before"}])),
        call({"reminders": [{"minutes_before": 60}, {"minutes_before": 1440}]}),
    ])
    workflow = EventWorkflow(provider)
    first = advance(workflow, EventWorkflowState())
    assert first.status == "collecting"
    assert "promemoria" in first.question
    second = advance(workflow, first, "Un'ora e un giorno prima")
    assert second.status == "ready_for_review"
    assert second.draft.title == "Visita"
    assert second.draft.tasks == first.draft.tasks
    assert [r.minutes_before for r in second.draft.reminders] == [60, 1440]
    assert first.draft.reminders is None


def test_explicit_no_reminders_is_ready():
    state = advance(
        EventWorkflow(ScriptedEventProvider([call(event_fields(reminders=[]))])),
        EventWorkflowState(),
    )
    assert state.status == "ready_for_review"
    assert state.draft.reminders == []


@pytest.mark.parametrize("arguments", [
    {"patch": {"reminders": [{"minutes_before": -1}]}},
    {"patch": {"reminders": [{"minutes_before": True}]}},
    {"patch": {"duration_minutes": 0}},
    {"patch": {"title": "   "}},
    {"patch": {"execute_shell": "something"}},
    {"patch": {}, "save_event": True},
    {"patch": {"tasks": [{"description": "x", "timing": "during"}]}},
])
def test_invalid_arguments_do_not_modify_previous_state(arguments):
    original = EventWorkflowState()
    workflow = EventWorkflow(ScriptedEventProvider([
        ToolCall(name="update_event_draft", arguments=arguments)
    ]))
    with pytest.raises(WorkflowError, match="Invalid tool arguments"):
        advance(workflow, original)
    assert original == EventWorkflowState()


def test_unsupported_language_is_rejected_without_mutating_previous_state():
    original = EventWorkflowState(conversation_language=Language.EN)
    workflow = EventWorkflow(ScriptedEventProvider([
        call({"title": "Meeting"}, conversation_language="fr")
    ]))
    with pytest.raises(WorkflowError):
        advance(workflow, original)
    assert original.conversation_language == Language.EN
    assert original.draft.title is None


def test_unknown_tool_is_never_executed():
    workflow = EventWorkflow(ScriptedEventProvider([
        ToolCall(name="delete_events", arguments={})
    ]))
    with pytest.raises(WorkflowError, match="not allowed"):
        advance(workflow, EventWorkflowState())


def test_ambiguity_blocks_ready_even_when_fields_are_complete():
    workflow = EventWorkflow(ScriptedEventProvider([
        call(event_fields(reminders=[]), clarification="Intendi il 2026 o il 2027?")
    ]))
    state = advance(workflow, EventWorkflowState())
    assert state.status == "collecting"
    assert state.question == "Intendi il 2026 o il 2027?"


@pytest.mark.parametrize("start", [
    "2026-10-25T02:30:00",  # Clock goes back: two possible instants.
    "2027-03-28T02:30:00",  # Clock goes forward: this local time never occurs.
    "2026-10-31T14:30:00+02:00",  # Offset disagrees with Europe/Rome.
])
def test_time_ambiguity_or_offset_mismatch_needs_clarification(start):
    workflow = EventWorkflow(ScriptedEventProvider([
        call(event_fields(starts_at=start, reminders=[]))
    ]))
    assert advance(workflow, EventWorkflowState()).status == "collecting"


def test_explicit_dst_offset_resolves_ambiguity():
    workflow = EventWorkflow(ScriptedEventProvider([
        call(event_fields(starts_at="2026-10-25T02:30:00+01:00", reminders=[]))
    ]))
    assert advance(workflow, EventWorkflowState()).status == "ready_for_review"


def test_invalid_zone_is_not_ready():
    workflow = EventWorkflow(ScriptedEventProvider([
        call(event_fields(timezone="Invalid/Zone", reminders=[]))
    ]))
    state = advance(workflow, EventWorkflowState())
    assert state.status == "collecting"
    assert "fuso" in state.question


def test_language_changes_question_not_time_zone():
    workflow = EventWorkflow(ScriptedEventProvider([call(event_fields())]))
    state = advance(workflow, EventWorkflowState(), language="en")
    assert state.question.startswith("When")
    assert state.conversation_language == Language.EN
    assert state.draft.timezone == "Europe/Rome"


def test_explicit_null_clears_optional_field_but_omitted_fields_remain():
    workflow = EventWorkflow(ScriptedEventProvider([
        call(event_fields(location="Ambulatorio", reminders=[])),
        call({"location": None}),
    ]))
    first = advance(workflow, EventWorkflowState())
    second = advance(workflow, first)
    assert second.draft.location is None
    assert second.draft.title == first.draft.title


def test_turn_limit_prevents_another_model_request():
    workflow = EventWorkflow(ScriptedEventProvider([]), max_turns=2)
    with pytest.raises(WorkflowError, match="limit"):
        advance(workflow, EventWorkflowState(turns=2))


def test_short_answer_has_previous_question_and_draft_available():
    class InspectingProvider:
        async def stream_propose(self, message, state, context, tools):
            assert message == "Un'ora prima"
            assert "promemoria" in state.question
            assert state.draft.title == "Visita"
            yield ProviderEvent(kind="tool_call", tool_call=call({"reminders": [{"minutes_before": 60}]}))

    original = EventWorkflowState(
        draft=EventDraft.model_validate(event_fields()), question="Quando vuoi il promemoria?"
    )
    assert advance(EventWorkflow(InspectingProvider()), original, "Un'ora prima").status == "ready_for_review"


def test_short_reply_keeps_conversation_language_and_context_is_ui_language():
    previous = EventWorkflowState(
        draft=EventDraft.model_validate(event_fields()),
        question="When would you like reminders?",
        conversation_language=Language.EN,
    )
    provider = ScriptedEventProvider([call({"reminders": []})])
    next_state = advance(EventWorkflow(provider), previous, "ok", language="it")
    assert next_state.conversation_language == Language.EN
    assert next_state.question is None


def test_model_can_switch_conversation_language_in_the_same_validated_tool_call():
    provider = ScriptedEventProvider([call({"title": "Meeting"}, conversation_language="en")])
    state = advance(EventWorkflow(provider), EventWorkflowState(), language="it")
    assert state.conversation_language == Language.EN
    assert state.question.startswith("On which date")


def test_stream_reports_real_phases_and_completed_state_only_after_validation():
    async def collect():
        workflow = EventWorkflow(ScriptedEventProvider([call(event_fields())]))
        return [event async for event in workflow.stream_advance(
            EventWorkflowState(), "Create an event", context()
        )]
    events = asyncio.run(collect())
    assert [event.kind for event in events] == ["progress", "progress", "completed"]
    assert events[0].message
    assert events[1].message
    assert events[-1].state.status == "collecting"


def test_invalid_streamed_proposal_never_emits_completed_state():
    original = EventWorkflowState(
        draft=EventDraft.model_validate(event_fields()),
        question="When do you want reminders?",
        conversation_language=Language.EN,
    )
    before = original.model_copy(deep=True)
    emitted = []

    async def collect():
        workflow = EventWorkflow(ScriptedEventProvider([call({"reminders": [{"minutes_before": -1}]})]))
        async for event in workflow.stream_advance(original, "A message", context()):
            emitted.append(event)

    with pytest.raises(WorkflowError):
        asyncio.run(collect())
    assert all(event.kind != "completed" for event in emitted)
    assert [event.kind for event in emitted] == ["progress", "progress"]
    assert original == before
