"""Typed actions submitted by playground controls without involving the model."""

from datetime import date, time
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class _Action(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SetTitleAction(_Action):
    type: Literal["set_title"]
    value: NonEmptyText


class SetDateAction(_Action):
    type: Literal["set_date"]
    value: date


class SetTimeAction(_Action):
    type: Literal["set_time"]
    value: time


class SetLocationAction(_Action):
    type: Literal["set_location"]
    value: NonEmptyText


class SetDurationAction(_Action):
    type: Literal["set_duration"]
    value: int = Field(gt=0, strict=True, description="Duration in minutes.")


class AddReminderAction(_Action):
    type: Literal["add_reminder"]
    minutes_before: int = Field(ge=0, strict=True)


class AddTaskAction(_Action):
    type: Literal["add_task"]
    description: NonEmptyText
    timing: Literal["before", "after"]


class ClearRemindersAction(_Action):
    type: Literal["clear_reminders"]


DraftAction: TypeAlias = Annotated[
    SetTitleAction
    | SetDateAction
    | SetTimeAction
    | SetLocationAction
    | SetDurationAction
    | AddReminderAction
    | AddTaskAction
    | ClearRemindersAction,
    Field(discriminator="type"),
]
