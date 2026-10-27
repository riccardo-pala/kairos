"""Fixed provider responses for demos and deterministic workflows."""

from collections.abc import AsyncIterator

from kairos.contracts import EventWorkflowState, ProviderEvent, RequestContext, ToolCall, WorkflowError
from kairos.i18n import MessageId, translate


class ScriptedEventProvider:
    """Fixed tool calls for demonstrations and tests; no language understanding."""

    def __init__(self, calls: list[ToolCall]):
        self.calls = iter(calls)

    async def stream_propose(
        self, message: str, state: EventWorkflowState, context: RequestContext, tools: list[dict]
    ) -> AsyncIterator[ProviderEvent]:
        try:
            call = next(self.calls)
        except StopIteration as exc:
            raise WorkflowError(MessageId.SCRIPT_EXHAUSTED) from exc
        yield ProviderEvent(kind="tool_call", tool_call=call)


class DemoEventProvider:
    """Select an explicit example proposal; shared Python code validates it."""

    def __init__(self, delay: float = .8):
        self.delay = delay

    async def stream_propose(self, message, state, context, tools):
        import asyncio
        from datetime import timedelta
        from zoneinfo import ZoneInfo
        from kairos.demo.scenarios import examples

        await asyncio.sleep(self.delay)
        normalized = ' '.join(message.casefold().split())
        step = next((
            step for scenario in examples(context.language.value) for step in scenario['steps']
            if ' '.join(step['message'].casefold().split()) == normalized
        ), None)
        if step is None:
            question = translate(MessageId.DEMO_GUIDANCE, context.language)
            call = ToolCall(name='ask_event_clarification', arguments={'question': question})
        else:
            proposal = dict(step['proposal'])
            patch = {}
            operations = {}
            if 'day_offset' in proposal:
                patch['start_date'] = (context.now.astimezone(ZoneInfo(context.timezone)).date()
                                       + timedelta(days=proposal.pop('day_offset'))).isoformat()
            if 'task' in proposal:
                operations['add'] = [{'description': proposal.pop('task'), 'timing': proposal.pop('timing'), 'evidence': message}]
            if proposal.pop('remove', False):
                operations.update(remove=True, remove_evidence=message)
            patch.update(proposal)
            call = ToolCall(name='update_event_draft', arguments={
                'patch': patch, 'task_operations': operations,
                'conversation_language': context.language.value,
            })
        async for event in ScriptedEventProvider([call]).stream_propose(message, state, context, tools):
            yield event
