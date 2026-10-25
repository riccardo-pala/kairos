from kairos.models.event import EventDraft


def test_event_draft_can_be_incomplete():
    event = EventDraft(title="Visita medica")

    assert event.title == "Visita medica"
    assert event.start_date is None
    assert event.start_time is None
    assert event.local_starts_at is None
    assert event.tasks == []
    assert event.reminders is None


def test_local_datetime_is_derived_only_when_both_parts_are_present():
    event = EventDraft(start_date="2026-10-26")
    assert event.local_starts_at is None

    event = EventDraft(start_date="2026-10-26", start_time="00:00")
    assert event.local_starts_at.isoformat() == "2026-10-26T00:00:00"


def test_event_schema_exposes_date_and_time_as_separate_fields():
    schema = EventDraft.model_json_schema()["properties"]

    def formats(field: str) -> set[str]:
        property_schema = schema[field]
        branches = property_schema.get("anyOf", [property_schema])
        return {branch["format"] for branch in branches if "format" in branch}

    assert formats("start_date") == {"date"}
    assert formats("start_time") == {"time"}
    assert "starts_at" not in schema


def test_explicit_offset_can_be_derived_with_date_without_becoming_a_second_field():
    event = EventDraft(start_date="2026-10-25", start_time="02:30+01:00")

    assert event.local_starts_at.isoformat() == "2026-10-25T02:30:00+01:00"
