import asyncio
import json
from datetime import datetime

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from kairos.contracts import EventWorkflowState, RequestContext, ToolResult, WorkflowError
from kairos.providers import OllamaEventProvider
from kairos.tools import ToolDefinition, ToolRegistry
from kairos.workflow import EventWorkflow


class EmptyArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SegmentedStream(httpx.AsyncByteStream):
    def __init__(self, done_frame_seen):
        self.done_frame_seen = done_frame_seen

    async def __aiter__(self):
        text = json.dumps({"message": {"content": "Working"}, "done": False}) + "\n"
        call = json.dumps({"message": {"tool_calls": [{"function": {
            "name": "test_tool", "arguments": {},
        }}]}, "done": True}) + "\n"
        encoded = text.encode()
        yield encoded[:9]
        yield encoded[9:]
        self.done_frame_seen[0] = True
        yield call.encode()

    async def aclose(self):
        return None


class InterruptedToolStream(httpx.AsyncByteStream):
    def __init__(self, failure):
        self.failure = failure

    async def __aiter__(self):
        frame = json.dumps({"message": {"tool_calls": [{"function": {
            "name": "test_tool", "arguments": {},
        }}]}, "done": False}) + "\n"
        yield frame.encode()
        if self.failure == "read_error":
            raise httpx.ReadError("connection interrupted")

    async def aclose(self):
        return None


def test_text_streams_before_done_and_tool_handler_waits_for_complete_stream():
    async def run():
        done_frame_seen = [False]
        executed = []

        def handler(arguments, state, context):
            assert done_frame_seen[0]
            executed.append(True)
            return ToolResult(draft=state.draft)

        registry = ToolRegistry([ToolDefinition(
            name="test_tool", description="A bounded test tool",
            arguments_model=EmptyArguments, handler=handler,
        )])

        def transport(request):
            return httpx.Response(200, stream=SegmentedStream(done_frame_seen))

        async with httpx.AsyncClient(
            base_url="http://localhost:11434", transport=httpx.MockTransport(transport)
        ) as client:
            workflow = EventWorkflow(OllamaEventProvider("test-model", client), tools=registry)
            context = RequestContext(
                now=datetime.fromisoformat("2026-10-24T12:00:00+02:00"),
                timezone="Europe/Rome",
            )
            events = workflow.stream_advance(EventWorkflowState(), "A request", context)
            first = await anext(events)
            assert first.kind == "progress"
            streamed = await anext(events)
            assert streamed.kind == "text" and streamed.text == "Working"
            assert not done_frame_seen[0]
            assert executed == []
            remaining = [event async for event in events]
            assert [event.kind for event in remaining] == ["progress", "completed"]
            assert executed == [True]

    asyncio.run(run())


@pytest.mark.parametrize("failure", ["eof", "read_error"])
def test_interrupted_stream_after_complete_tool_frame_never_executes_or_completes(failure):
    async def run():
        executed = []
        original = EventWorkflowState(
            question="When should I remind you?", conversation_language="en", turns=2
        )
        before = original.model_copy(deep=True)

        def handler(arguments, state, context):
            executed.append(True)
            return ToolResult(draft=state.draft)

        registry = ToolRegistry([ToolDefinition(
            name="test_tool", description="A bounded test tool",
            arguments_model=EmptyArguments, handler=handler,
        )])

        def transport(request):
            return httpx.Response(200, stream=InterruptedToolStream(failure))

        async with httpx.AsyncClient(
            base_url="http://localhost:11434", transport=httpx.MockTransport(transport)
        ) as client:
            workflow = EventWorkflow(OllamaEventProvider("test-model", client), tools=registry)
            context = RequestContext(
                now=datetime.fromisoformat("2026-10-24T12:00:00+02:00"),
                timezone="Europe/Rome",
            )
            events = []
            with pytest.raises(WorkflowError):
                async for event in workflow.stream_advance(original, "A request", context):
                    events.append(event)

        assert all(event.kind != "completed" for event in events)
        assert executed == []
        assert original == before

    asyncio.run(run())
