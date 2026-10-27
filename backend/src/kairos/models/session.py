"""Session records and turn contracts shared by HTTP and browser demo adapters."""

from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from kairos.contracts import EventWorkflowState
from kairos.i18n import Language
from kairos.models.actions import DraftAction
from kairos.models.guidance import DraftGuidance


class SessionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    language: Language
    timezone: str
    state: EventWorkflowState
    guidance: DraftGuidance
    created_at: AwareDatetime
    updated_at: AwareDatetime


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




class ChangeLanguageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language
