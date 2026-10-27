"""Browser-local API adapter using the real workflow and validation contracts."""

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from kairos.contracts import EventWorkflowState, RequestContext, WorkflowError
from kairos.demo.provider import DemoEventProvider
from kairos.demo.scenarios import examples
from kairos.i18n import MessageId, translate
from kairos.models.event import EventDraft
from kairos.models.guidance import build_draft_guidance
from kairos.models.session import ChangeLanguageRequest, CreateSessionRequest, SessionRecord, TurnRequest
from kairos.workflow import EventWorkflow


class DemoAPI:
    """In-memory sessions isolated inside one browser worker; no HTTP or SQL."""

    def __init__(self, delay: float = .8):
        self.sessions: dict[UUID, SessionRecord] = {}
        self.delay = delay

    def create_session(self, payload: dict) -> dict:
        request = CreateSessionRequest.model_validate(payload)
        now = datetime.now(UTC)
        state = EventWorkflowState(draft=EventDraft(timezone=request.timezone))
        record = SessionRecord(
            id=uuid4(), language=request.language, timezone=request.timezone, state=state,
            guidance=build_draft_guidance(state.draft, request.language), created_at=now, updated_at=now,
        )
        self.sessions = {record.id: record}
        result = record.model_dump(mode='json')
        result['demo_examples'] = [
            {'id': item['id'], 'label': item['label'], 'messages': [step['message'] for step in item['steps']]}
            for item in examples(request.language.value)
        ]
        return result

    def change_language(self, session_id: str, payload: dict) -> dict:
        request = ChangeLanguageRequest.model_validate(payload)
        record = self.sessions[UUID(session_id)]
        state = record.state.model_copy(update={'conversation_language': request.language})
        record = record.model_copy(update={
            'language': request.language, 'state': state, 'updated_at': datetime.now(UTC),
            'guidance': build_draft_guidance(state.draft, request.language),
        })
        self.sessions[record.id] = record
        result = record.model_dump(mode='json')
        result['demo_examples'] = [
            {'id': item['id'], 'label': item['label'], 'messages': [step['message'] for step in item['steps']]}
            for item in examples(request.language.value)
        ]
        return result

    async def turn(self, session_id: str, payload: dict, emit):
        record = self.sessions[UUID(session_id)]
        context = RequestContext(now=datetime.now(UTC), language=record.language, timezone=record.timezone)
        request = TurnRequest.model_validate(payload)
        try:
            if request.action is not None:
                emit({'event': 'progress', 'data': {'message': translate(MessageId.PROGRESS_ACTION, record.language)}})
                await asyncio.sleep(self.delay / 3)
                state = EventWorkflow.apply_action(record.state, request.action, context)
                self._complete(record, state, emit)
                return
            workflow = EventWorkflow(DemoEventProvider(self.delay))
            async for event in workflow.stream_advance(record.state, request.message, context, task_id=request.task_id):
                if event.kind == 'completed':
                    self._complete(record, event.state, emit)
                elif event.kind == 'progress':
                    emit({'event': 'progress', 'data': {'message': event.message}})
                    await asyncio.sleep(self.delay / 3)
                else:
                    emit({'event': 'text', 'data': {'text': event.text}})
        except WorkflowError as exc:
            emit({'event': 'error', 'data': {'code': exc.code.value, 'message': exc.text(record.language)}})
        except ValidationError:
            emit({'event': 'error', 'data': {'code': 'error.invalid_arguments', 'message': (
                'I dati inseriti non sono validi. La bozza non è stata modificata.'
                if record.language.value == 'it' else 'Invalid input. The draft was not changed.'
            )}})

    def _complete(self, previous, state, emit):
        record = previous.model_copy(update={
            'state': state, 'updated_at': datetime.now(UTC),
            'guidance': build_draft_guidance(state.draft, state.conversation_language or previous.language),
        })
        self.sessions[record.id] = record
        emit({'event': 'completed', 'data': {'session': record.model_dump(mode='json')}})


api = DemoAPI()


async def handle_json(request_json: str, emit) -> str:
    """JSON-only bridge: user input is data and is never executed as Python."""
    request = json.loads(request_json)
    if request['operation'] == 'create_session':
        return json.dumps(api.create_session(request['payload']))
    if request['operation'] == 'change_language':
        return json.dumps(api.change_language(request['session_id'], request['payload']))
    if request['operation'] == 'turn':
        await api.turn(request['session_id'], request['payload'], lambda event: emit(json.dumps(event)))
        return 'null'
    raise ValueError('Unknown demo operation')
