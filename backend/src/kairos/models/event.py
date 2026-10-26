from datetime import date, datetime, time
import re
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


_LOCATION_JOINER = re.compile(
    r"\s+(?:in|at)\s+(?=(?:via|viale|piazza|piazzale|corso|largo|vicolo|strada|"
    r"street|road|avenue|boulevard|square)\b)",
    re.IGNORECASE,
)
_STREET_TYPE = re.compile(
    r"\b(?:via|viale|piazza|piazzale|corso|largo|vicolo|strada|street|road|"
    r"avenue|boulevard|square)\b",
    re.IGNORECASE,
)


def normalize_location_label(value: str) -> str:
    """Clean location formatting without looking up or adding address details."""
    normalized = " ".join(value.split()).strip(" ,")
    normalized = _LOCATION_JOINER.sub(", ", normalized)
    parts = [re.sub(r"\s*,\s*", " ", part).strip() for part in normalized.split(",")]
    formatted = []
    for index, part in enumerate(parts):
        if not part:
            continue
        if part.islower():
            part = part.title()
        elif part[0].islower() and not any(character.isupper() for character in part[1:]):
            part = part[0].upper() + part[1:]
        if index == 0 or _STREET_TYPE.search(part):
            part = _STREET_TYPE.sub(lambda match: match.group(0).capitalize(), part)
        formatted.append(part)
    return ", ".join(formatted)


class EventTask(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4)
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

    @field_validator("location", mode="before")
    @classmethod
    def clean_location_label(cls, value):
        if isinstance(value, str):
            return normalize_location_label(value)
        return value

    @property
    def local_starts_at(self) -> datetime | None:
        """Return a derived local datetime only when date and time are both known."""
        if self.start_date is None or self.start_time is None:
            return None
        return datetime.combine(self.start_date, self.start_time)
