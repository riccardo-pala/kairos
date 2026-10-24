from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EventTask(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1)
    timing: Literal["before", "after"]


class ReminderDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minutes_before: int = Field(ge=0, strict=True)


class EventDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1)
    starts_at: datetime | None = None
    timezone: str | None = None
    location: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0, strict=True)
    tasks: list[EventTask] = Field(default_factory=list)
    reminders: list[ReminderDraft] | None = None
