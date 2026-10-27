"""Response guidance: required fields and optional structured input templates."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kairos.i18n import Language, MessageId, translate
from kairos.models.event import EventDraft


class GuidanceField(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: Literal["title", "start_date", "start_time"]
    label: str


class GuidanceOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: str
    label: str
    minutes: int | None = None


class DraftSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: Literal[
        "set_title", "set_date", "set_time", "set_location", "set_duration", "add_reminder", "add_task"
    ]
    label: str
    input_type: Literal["text", "date", "time", "duration", "reminder", "task"]
    placeholder: str
    submit_label: str
    clear_label: str | None = None
    units: list[GuidanceOption] = Field(default_factory=list)
    timings: list[GuidanceOption] = Field(default_factory=list)


class DraftGuidance(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_title: str
    required_missing: list[GuidanceField]
    suggestions: list[DraftSuggestion]


def build_draft_guidance(draft: EventDraft, language: Language) -> DraftGuidance:
    has_event_detail = any((
        draft.title,
        draft.start_date,
        draft.start_time,
        draft.location,
        draft.duration_minutes,
        draft.tasks,
        draft.reminders is not None,
    ))
    if not has_event_detail:
        return DraftGuidance(
            required_title=translate(MessageId.GUIDANCE_REQUIRED, language),
            required_missing=[],
            suggestions=[],
        )

    required_fields = []
    suggestions = []

    templates = {
        "title": ("set_title", "text", MessageId.GUIDANCE_FIELD_TITLE, MessageId.GUIDANCE_PLACEHOLDER_TITLE),
        "start_date": ("set_date", "date", MessageId.GUIDANCE_FIELD_DATE, MessageId.GUIDANCE_PLACEHOLDER_DATE),
        "start_time": ("set_time", "time", MessageId.GUIDANCE_FIELD_TIME, MessageId.GUIDANCE_PLACEHOLDER_TIME),
    }
    values = {"title": draft.title, "start_date": draft.start_date, "start_time": draft.start_time}
    for field, (action_id, input_type, label_id, placeholder_id) in templates.items():
        if values[field] is None:
            required_fields.append(GuidanceField(id=field, label=translate(label_id, language)))
            suggestions.append(DraftSuggestion(
                id=action_id,
                label=translate(label_id, language),
                input_type=input_type,
                placeholder=translate(placeholder_id, language),
                submit_label=translate(MessageId.GUIDANCE_SAVE, language),
            ))

    if draft.title or draft.start_date or draft.start_time:
        time_units = [
            GuidanceOption(value="minutes", label=translate(MessageId.GUIDANCE_MINUTES, language), minutes=1),
            GuidanceOption(value="hours", label=translate(MessageId.GUIDANCE_HOURS, language), minutes=60),
            GuidanceOption(value="days", label=translate(MessageId.GUIDANCE_DAYS, language), minutes=1440),
        ]
        suggestions.append(DraftSuggestion(
            id="add_task",
            label=translate(MessageId.GUIDANCE_ACTIVITY, language),
            input_type="task",
            placeholder=translate(MessageId.GUIDANCE_PLACEHOLDER_ACTIVITY, language),
            submit_label=translate(MessageId.GUIDANCE_SAVE, language),
            timings=[
                GuidanceOption(
                    value="before",
                    label=translate(MessageId.GUIDANCE_BEFORE, language),
                ),
                GuidanceOption(
                    value="after",
                    label=translate(MessageId.GUIDANCE_AFTER, language),
                ),
            ],
        ))
        if not draft.location:
            suggestions.append(DraftSuggestion(
                id="set_location",
                label=translate(MessageId.GUIDANCE_LOCATION, language),
                input_type="text",
                placeholder=translate(MessageId.GUIDANCE_PLACEHOLDER_LOCATION, language),
                submit_label=translate(MessageId.GUIDANCE_SAVE, language),
            ))
        if draft.duration_minutes is None:
            suggestions.append(DraftSuggestion(
                id="set_duration",
                label=translate(MessageId.GUIDANCE_DURATION, language),
                input_type="duration",
                placeholder=translate(MessageId.GUIDANCE_PLACEHOLDER_DURATION, language),
                submit_label=translate(MessageId.GUIDANCE_SAVE, language),
                units=time_units,
            ))
        suggestions.append(DraftSuggestion(
            id="add_reminder",
            label=translate(MessageId.GUIDANCE_REMINDER, language),
            input_type="reminder",
            placeholder=translate(MessageId.GUIDANCE_PLACEHOLDER_REMINDER, language),
            submit_label=translate(MessageId.GUIDANCE_SAVE, language),
            clear_label=translate(MessageId.GUIDANCE_NO_REMINDERS, language),
            units=time_units,
        ))

    return DraftGuidance(
        required_title=translate(MessageId.GUIDANCE_REQUIRED, language),
        required_missing=required_fields,
        suggestions=suggestions,
    )
