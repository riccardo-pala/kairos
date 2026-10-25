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
    assert "Dati della bozza:" in output or "Draft details:" in output
    assert '"title"' not in output
    assert '"reminders"' not in output


@pytest.mark.parametrize("language,expected_debug_help", [
    ("it", "Mostra anche lo stato JSON"),
    ("en", "Also print the draft state as JSON"),
])
def test_debug_flag_prints_json_and_help_is_localized(
    monkeypatch, capsys, language, expected_debug_help
):
    monkeypatch.setattr(sys, "argv", ["kairos", "--language", language, "--debug"])
    main()
    output = capsys.readouterr().out
    assert '"title"' in output
    assert '"reminders"' in output

    monkeypatch.setattr(sys, "argv", ["kairos", "--language", language, "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert expected_debug_help in capsys.readouterr().out


@pytest.mark.parametrize("language,think_flag,expected_think,expected_help", [
    ("it", [], False, "Abilita il ragionamento interno"),
    ("en", ["--think"], True, "Enable model reasoning generation"),
])
def test_interactive_cli_sets_thinking_only_from_flag_and_localizes_help(
    monkeypatch, capsys, language, think_flag, expected_think, expected_help
):
    import kairos.__main__ as cli

    observed = []

    class ProviderSpy:
        def __init__(self, model, client, *, think):
            observed.append(think)

    class WorkflowStub:
        def __init__(self, provider):
            pass

    monkeypatch.setattr(sys, "argv", ["kairos", "--model", "test-model", "--language", language, *think_flag])
    monkeypatch.setattr(builtins, "input", lambda prompt="": "/exit")
    monkeypatch.setattr(cli, "OllamaEventProvider", ProviderSpy)
    monkeypatch.setattr(cli, "EventWorkflow", WorkflowStub)
    main()
    assert observed == [expected_think]

    monkeypatch.setattr(sys, "argv", ["kairos", "--language", language, "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert expected_help in capsys.readouterr().out


@pytest.mark.parametrize("debug", [False, True])
def test_interactive_cli_hides_model_text_unless_debug_and_keeps_state_after_late_error(
    monkeypatch, capsys, debug
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
                raise WorkflowError(MessageId.TOOL_COUNT)
            if message == "second":
                observed["second_state"] = state.model_copy(deep=True)
                yield WorkflowEvent(
                    kind="completed",
                    state=EventWorkflowState(
                        draft={"title": "Motorcycle service"},
                        question="When?",
                        conversation_language="en",
                    ),
                )

    inputs = iter(["first", "second", "/exit"])
    args = ["kairos", "--model", "test-model"] + (["--debug"] if debug else [])
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))
    monkeypatch.setattr(cli, "EventWorkflow", MockWorkflow)
    main()

    assert ("Provisional text" in observed["intermediate"]) is debug
    assert observed["second_state"] == initial
    output = capsys.readouterr().out
    assert "esattamente una chiamata" in output
    assert "When?" in output
    assert "Dati della bozza:" in output
    assert "Motorcycle service" in output
    assert ('"title"' in output) is debug
    assert "thinking" not in output
