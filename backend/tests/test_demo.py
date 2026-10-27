"""Exercise the browser adapter against shared Python logic, without remote calls."""
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from kairos.demo.runtime import DemoAPI
from kairos.demo.scenarios import examples


def turn(api, session, payload):
    events = []
    asyncio.run(api.turn(session['id'], payload, events.append))
    return events


@pytest.mark.parametrize('language', ['it', 'en'])
@pytest.mark.parametrize('scenario_index', [0, 1, 2])
def test_guided_scenarios_use_validated_workflow_and_do_not_invent_tasks(language, scenario_index):
    api = DemoAPI(delay=0)
    session = api.create_session({'language': language, 'timezone': 'Europe/Rome'})
    scenario = examples(language)[scenario_index]
    first = turn(api, session, {'message': scenario['steps'][0]['message']})
    session = first[-1]['data']['session']
    assert first[-1]['event'] == 'completed'
    assert session['state']['draft']['tasks'] == []
    assert session['state']['draft']['start_time'] is None
    for step in scenario['steps'][1:]:
        result = turn(api, session, {'message': step['message']})
        assert result[-1]['event'] == 'completed', result
        session = result[-1]['data']['session']
    assert session['state']['status'] == 'ready_for_review'
    if scenario_index == 0:
        assert session['state']['draft']['tasks'] == []
        assert session['state']['draft']['reminders'] == [{'minutes_before': 120}]
    elif scenario_index == 1:
        assert session['state']['draft']['duration_minutes'] == 120
        assert session['state']['draft']['reminders'] == []
    else:
        assert session['state']['draft']['tasks'][0]['timing'] == 'after'


def test_unknown_free_text_is_explained_without_fabricating_event_data():
    api = DemoAPI(delay=0)
    session = api.create_session({'timezone': 'Europe/Rome'})
    events = turn(api, session, {'message': 'invented input outside the guided examples'})
    state = events[-1]['data']['session']['state']
    assert state['draft']['title'] is None
    assert state['draft']['tasks'] == []
    assert 'simulate' in state['question']


def test_structured_widgets_use_real_validation_and_preserve_state_after_invalid_reminder():
    api = DemoAPI(delay=0)
    session = api.create_session({'timezone': 'Europe/Rome'})
    result = turn(api, session, {'action': {'type': 'set_duration', 'value': 2880}})
    assert result[-1]['data']['session']['state']['draft']['duration_minutes'] == 2880
    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    turn(api, session, {'action': {'type': 'set_date', 'value': yesterday}})
    turn(api, session, {'action': {'type': 'set_time', 'value': '12:00'}})
    before = api.sessions[UUID(session['id'])].state.model_dump()
    result = turn(api, session, {'action': {'type': 'add_reminder', 'minutes_before': 60}})
    assert result[-1]['event'] == 'error'
    assert api.sessions[UUID(session['id'])].state.model_dump() == before


def test_sessions_are_local_and_restarting_discards_previous_demo_state():
    first, other = DemoAPI(delay=0), DemoAPI(delay=0)
    session = first.create_session({'timezone': 'Europe/Rome'})
    assert other.sessions == {}
    replacement = first.create_session({'timezone': 'UTC'})
    assert list(first.sessions) == [UUID(replacement['id'])]
    assert replacement['id'] != session['id']


def test_changing_language_preserves_draft_and_localizes_following_guidance():
    api = DemoAPI(delay=0)
    session = api.create_session({'language': 'it', 'timezone': 'Europe/Rome'})
    first = examples('it')[0]['steps'][0]['message']
    completed = turn(api, session, {'message': first})[-1]['data']['session']
    changed = api.change_language(session['id'], {'language': 'en'})
    assert changed['id'] == completed['id']
    assert changed['state']['draft'] == completed['state']['draft']
    assert changed['state']['conversation_language'] == 'en'
    assert changed['guidance']['required_missing'][0]['label'] == 'Time'
    assert changed['demo_examples'][0]['label'] == 'At the mechanic'
