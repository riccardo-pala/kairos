"""One language contract for catalog messages and model-generated questions."""

import json
from enum import StrEnum
from importlib.resources import files
from typing import Annotated, Self

from pydantic import RootModel, StringConstraints, WithJsonSchema, model_validator


class Language(StrEnum):
    IT = "it"
    EN = "en"


class MessageId(StrEnum):
    TITLE = "question.title"
    STARTS_AT = "question.starts_at"
    TIMEZONE = "question.timezone"
    TIME = "question.time"
    REMINDERS = "question.reminders"
    INVALID_MESSAGE = "error.invalid_message"
    TURN_LIMIT = "error.turn_limit"
    INVALID_TIMEZONE = "error.invalid_timezone"
    TOOL_NOT_ALLOWED = "error.tool_not_allowed"
    INVALID_ARGUMENTS = "error.invalid_arguments"
    MODEL_UNAVAILABLE = "error.model_unavailable"
    INVALID_TOOL_CALL = "error.invalid_tool_call"
    TOOL_COUNT = "error.tool_count"
    SCRIPT_EXHAUSTED = "error.script_exhausted"
    NO_TOOLS = "error.no_tools"
    PROGRESS_START = "progress.start"
    PROGRESS_VALIDATE = "progress.validate"
    CLI_READY = "cli.ready"
    CLI_NEEDS_CLARIFICATION = "cli.needs_clarification"
    CLI_SESSION = "cli.session"
    CLI_DEMO = "cli.demo"
    CLI_ERROR = "cli.error"
    CLI_DESCRIPTION = "cli.description"
    CLI_MODEL_HELP = "cli.model_help"
    CLI_LANGUAGE_HELP = "cli.language_help"
    CLI_TIMEZONE_HELP = "cli.timezone_help"
    DEMO_TITLE = "demo.title"
    DEMO_TASK = "demo.task"
    DEMO_FIRST_MESSAGE = "demo.first_message"
    DEMO_SECOND_MESSAGE = "demo.second_message"


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Translations = Annotated[
    dict[Language, NonEmptyText],
    WithJsonSchema({
        "type": "object",
        "properties": {
            language.value: {"type": "string", "minLength": 1, "maxLength": 1000}
            for language in Language
        },
        "required": [language.value for language in Language],
        "additionalProperties": False,
    }),
]


class LocalizedText(RootModel[Translations]):
    @model_validator(mode="after")
    def require_all_languages(self) -> Self:
        if set(self.root) != set(Language):
            raise ValueError("Text must contain exactly all supported languages.")
        return self

    def text(self, language: Language | str) -> str:
        return self.root[Language(language)]


class MessageCatalog(RootModel[dict[MessageId, LocalizedText]]):
    @model_validator(mode="after")
    def require_all_messages(self) -> Self:
        if set(self.root) != set(MessageId):
            raise ValueError("Catalog must contain exactly all declared message IDs.")
        return self


_catalog = MessageCatalog.model_validate(
    json.loads(files("kairos").joinpath("locales/messages.json").read_text(encoding="utf-8"))
)


def localized(message_id: MessageId) -> LocalizedText:
    return _catalog.root[message_id].model_copy(deep=True)


def translate(message_id: MessageId, language: Language | str) -> str:
    return _catalog.root[message_id].text(language)
