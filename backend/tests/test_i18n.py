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
    "A single unlocalized string",
])
def test_incomplete_or_invalid_localized_text_is_rejected(value):
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


def test_tool_schema_requires_exactly_the_supported_language_keys():
    schema = AskClarificationArguments.model_json_schema()
    translations = schema["$defs"]["LocalizedText"]
    assert set(translations["required"]) == {language.value for language in Language}
    assert set(translations["properties"]) == {language.value for language in Language}
    assert translations["additionalProperties"] is False


def test_state_serializes_translations_as_a_language_dictionary():
    state = EventWorkflowState(question=localized(MessageId.TITLE))
    assert set(state.model_dump(mode="json")["question"]) == {"it", "en"}
    assert state.question.text("en") == "What should this event be called?"


def test_errors_have_stable_codes_and_translated_user_messages():
    error = WorkflowError(MessageId.TOOL_NOT_ALLOWED)
    assert error.code == MessageId.TOOL_NOT_ALLOWED
    assert error.text("it") != error.text("en")


def test_mutating_a_returned_translation_does_not_change_the_catalog():
    result = localized(MessageId.TITLE)
    original = result.text("it")
    result.root[Language.IT] = "Changed"
    assert localized(MessageId.TITLE).text("it") == original
