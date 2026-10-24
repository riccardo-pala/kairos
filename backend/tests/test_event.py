from kairos.models.event import EventDraft


def test_event_draft_can_be_incomplete():
    event = EventDraft(title="Visita medica")

    assert event.title == "Visita medica"
    assert event.starts_at is None
    assert event.tasks == []
    assert event.reminders is None