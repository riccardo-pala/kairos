"""HTTP request, response and server-sent event schemas."""

from typing import Annotated, Literal, TypeAlias
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kairos.i18n import Language
from kairos.models.actions import DraftAction
from kairos.stores.session import SessionRecord


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Language = Language.IT
    timezone: str = Field(min_length=1, max_length=128)

    @field_validator("timezone")
    @classmethod
    def require_iana_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Timezone must be a valid IANA name.") from exc
        return value


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str | None = Field(default=None, min_length=1, max_length=8_000)
    action: DraftAction | None = None
    task_id: UUID | None = Field(
        default=None,
        description="Stable task ID selected while answering a pending task-removal question.",
    )

    @field_validator("message")
    @classmethod
    def require_non_whitespace(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Message must not be blank.")
        return value

    @model_validator(mode="after")
    def require_one_turn_input(self):
        if (self.message is None) == (self.action is None):
            raise ValueError("Provide exactly one of message or action.")
        if self.task_id is not None and self.message is None:
            raise ValueError("A task selection must accompany a message.")
        return self


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ProgressSSE(BaseModel):
    event: Literal["progress"] = "progress"
    message: str


class TextSSE(BaseModel):
    event: Literal["text"] = "text"
    text: str


class CompletedSSE(BaseModel):
    event: Literal["completed"] = "completed"
    session: SessionRecord


class ErrorSSE(BaseModel):
    event: Literal["error"] = "error"
    code: str
    message: str


WorkflowSSE: TypeAlias = Annotated[
    ProgressSSE | TextSSE | CompletedSSE | ErrorSSE,
    Field(discriminator="event"),
]
