from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EventTask(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1)
    timing: Literal["before", "after"]


class ReminderDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minutes_before: int = Field(
        ge=0,
        strict=True,
        description="Minutes before the event start; two days before is 2880 minutes.",
    )


class EventDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1)
    start_date: date | None = None
    start_time: time | None = None
    timezone: str | None = None
    location: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0, strict=True)
    tasks: list[EventTask] = Field(default_factory=list)
    reminders: list[ReminderDraft] | None = None

    @property
    def local_starts_at(self) -> datetime | None:
        """Return a derived local datetime only when date and time are both known."""
        if self.start_date is None or self.start_time is None:
            return None
        return datetime.combine(self.start_date, self.start_time)
