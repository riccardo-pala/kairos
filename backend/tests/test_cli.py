import builtins
import sys

import pytest

from kairos.__main__ import main
from kairos.contracts import EventWorkflowState, WorkflowError, WorkflowEvent
from kairos.i18n import MessageId


@pytest.mark.parametrize("language,expected_title,expected_intro", [
    ("it", "Visita medica", "risposte predefinite"),
    ("en", "Medical appointment", "scripted responses"),
])
def test_demo_uses_selected_language_without_contacting_a_model(
    monkeypatch, capsys, language, expected_title, expected_intro
):
    monkeypatch.setattr(sys, "argv", ["kairos", "--language", language])
    main()
    output = capsys.readouterr().out
    assert expected_intro in output
    assert expected_title in output
    assert "pronta per la revisione" in output or "ready for review" in output
    assert '"title"' in output
    assert '"reminders"' in output


def test_interactive_cli_flushes_provisional_text_and_keeps_state_after_late_error(
    monkeypatch, capsys
):
    import kairos.__main__ as cli

    observed = {"intermediate": "", "second_state": None}
    initial = EventWorkflowState()

    class MockWorkflow:
        def __init__(self, provider):
            pass

        async def stream_advance(self, state, message, context):
            if message == "first":
                assert state == initial
                yield WorkflowEvent(kind="progress", message="Preparing")
                yield WorkflowEvent(kind="text", text="Provisional text")
                observed["intermediate"] = capsys.readouterr().out
                raise WorkflowError(MessageId.MODEL_UNAVAILABLE)
            if message == "second":
                observed["second_state"] = state.model_copy(deep=True)
                yield WorkflowEvent(
                    kind="completed",
                    state=EventWorkflowState(question="When?", conversation_language="en"),
                )

    inputs = iter(["first", "second", "/exit"])
    monkeypatch.setattr(sys, "argv", ["kairos", "--model", "test-model"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))
    monkeypatch.setattr(cli, "EventWorkflow", MockWorkflow)
    main()

    assert "Provisional text" in observed["intermediate"]
    assert observed["second_state"] == initial
    output = capsys.readouterr().out
    assert "Il modello non è disponibile" in output
    assert "When?" in output
