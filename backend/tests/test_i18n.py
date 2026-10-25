import json
from importlib.resources import files

import pytest
from pydantic import ValidationError

from kairos.contracts import EventWorkflowState, WorkflowError
from kairos.i18n import Language, LocalizedText, MessageCatalog, MessageId, localized
from kairos.tools import AskClarificationArguments


def catalog_data():
    return json.loads(files("kairos").joinpath("locales/messages.json").read_text())


def test_every_catalog_message_has_every_supported_language():
    catalog = MessageCatalog.model_validate(catalog_data())
    assert set(catalog.root) == set(MessageId)
    for translations in catalog.root.values():
        assert set(translations.root) == set(Language)


@pytest.mark.parametrize("value", [
    {"it": "Domanda"},
    {"en": "Question"},
    {"it": " ", "en": "Question"},
    {"it": "Domanda", "en": "Question", "fr": "Question"},
    {},
])
def test_static_localized_text_rejects_missing_empty_or_unsupported_languages(value):
    with pytest.raises(ValidationError):
        LocalizedText.model_validate(value)


def test_catalog_rejects_a_missing_message():
    data = catalog_data()
    del data[MessageId.TITLE]
    with pytest.raises(ValidationError):
        MessageCatalog.model_validate(data)


def test_catalog_rejects_an_unknown_message():
    data = catalog_data()
    data["unknown.message"] = {"it": "Testo", "en": "Text"}
    with pytest.raises(ValidationError):
        MessageCatalog.model_validate(data)


def test_tool_schema_uses_a_single_question_and_validated_language_choice():
    schema = AskClarificationArguments.model_json_schema()
    assert schema["properties"]["question"]["type"] == "string"
    assert schema["$defs"]["Language"]["enum"] == ["it", "en"]


def test_state_stores_one_question_and_conversation_language():
    state = EventWorkflowState(question="Quando?", conversation_language=Language.EN)
    assert state.model_dump(mode="json")["question"] == "Quando?"
    assert state.conversation_language == Language.EN


@pytest.mark.parametrize("event", [
    {"kind": "completed"},
    {"kind": "text"},
    {"kind": "progress"},
])
def test_workflow_events_require_the_payload_for_their_kind(event):
    from kairos.contracts import WorkflowEvent

    with pytest.raises(ValidationError):
        WorkflowEvent.model_validate(event)


@pytest.mark.parametrize("event", [
    {"kind": "text"},
    {"kind": "tool_call"},
])
def test_provider_events_require_the_payload_for_their_kind(event):
    from kairos.contracts import ProviderEvent

    with pytest.raises(ValidationError):
        ProviderEvent.model_validate(event)


def test_errors_have_stable_codes_and_translated_user_messages():
    error = WorkflowError(MessageId.TOOL_NOT_ALLOWED)
    assert error.code == MessageId.TOOL_NOT_ALLOWED
    assert error.text("it") != error.text("en")


def test_mutating_a_returned_translation_does_not_change_the_catalog():
    result = localized(MessageId.TITLE)
    original = result.text("it")
    result.root[Language.IT] = "Changed"
    assert localized(MessageId.TITLE).text("it") == original
