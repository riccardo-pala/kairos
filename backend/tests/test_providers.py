import asyncio
import json
from datetime import datetime

import httpx
import pytest

from kairos.providers import OllamaEventProvider, OllamaMetrics
from kairos.contracts import EventWorkflowState, RequestContext, WorkflowError
from kairos.tools import event_tools


def collect_provider(handler, state=None):
    async def request():
        async with httpx.AsyncClient(
            base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
        ) as client:
            provider = OllamaEventProvider("test-model", client)
            context = RequestContext(
                now=datetime.fromisoformat("2026-10-24T12:00:00+02:00"),
                timezone="Europe/Rome",
            )
            return [event async for event in provider.stream_propose(
                "Una visita", state or EventWorkflowState(), context,
                event_tools().schemas(EventWorkflowState()),
            )]
    return asyncio.run(request())


def ndjson(*frames):
    return httpx.Response(200, content="\n".join(json.dumps(frame) for frame in frames).encode())


def test_ollama_stream_sends_context_and_emits_content_and_structured_call():
    def handler(request):
        payload = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert payload["stream"] is True
        assert "think" not in payload
        assert payload["tools"][0]["function"]["name"] == "update_event_draft"
        assert payload["tools"][1]["function"]["name"] == "ask_event_clarification"
        data = json.loads(payload["messages"][1]["content"])
        assert data["context"]["timezone"] == "Europe/Rome"
        assert data["message"] == "Una visita"
        assert data["conversation_language"] is None
        assert set(data["supported_languages"]) == {"it", "en"}
        return ndjson(
            {"message": {"content": "Sto verificando"}, "done": False},
            {"message": {"thinking": "do not show", "tool_calls": [
                {"function": {"name": "update_event_draft", "arguments": {"patch": {"title": "Visita"}}}}
            ]}, "done": True},
        )
    events = collect_provider(handler)
    assert [(event.kind, event.text) for event in events if event.kind == "text"] == [("text", "Sto verificando")]
    call = next(event.tool_call for event in events if event.kind == "tool_call")
    assert call.arguments["patch"]["title"] == "Visita"


@pytest.mark.parametrize("frames", [
    [{"message": {"tool_calls": [
        {"function": {"name": "update_event_draft", "arguments": "{\"patch\": {}}"}}
    ]}, "done": True}],
    [{"message": {"tool_calls": "invalid"}, "done": True}],
    [{"message": {"content": "partial"}, "done": False}],
    [{"message": {"content": "partial"}}],
])
def test_malformed_missing_or_incomplete_stream_fails_closed(frames):
    with pytest.raises(WorkflowError):
        collect_provider(lambda request: ndjson(*frames))


def test_provider_error_does_not_expose_response_body():
    with pytest.raises(WorkflowError, match="unavailable"):
        collect_provider(lambda request: httpx.Response(500, text="sensitive body"))


def test_invalid_ndjson_frame_fails_closed():
    with pytest.raises(WorkflowError):
        collect_provider(lambda request: httpx.Response(200, content=b"{not-json}\n"))


def test_final_frame_metrics_keep_missing_values_null_and_zero_counts():
    metrics = OllamaMetrics.from_done_frame({
        "done": True, "total_duration": 15, "prompt_eval_count": 0,
        "prompt_eval_cached_count": True, "eval_count": 3,
    })
    assert metrics.total_duration == 15
    assert metrics.prompt_eval_count == 0
    assert metrics.prompt_eval_cached_count is None
    assert metrics.eval_count == 3
    assert metrics.load_duration is None
    assert metrics.prompt_eval_duration is None
    assert metrics.eval_duration is None


def test_provider_reports_only_metrics_from_the_terminal_frame():
    captured = []

    def handler(request):
        return ndjson(
            {"message": {"content": "A little text"}, "done": False, "prompt_eval_count": 999},
            {"message": {"tool_calls": [{"function": {
                "name": "ask_event_clarification", "arguments": {"question": "Which date?"},
            }}]}, "done": True, "prompt_eval_count": 25, "eval_count": 8, "total_duration": 1000},
        )

    async def run():
        async with httpx.AsyncClient(
            base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
        ) as client:
            provider = OllamaEventProvider("test-model", client, metrics_callback=captured.append)
            context = RequestContext(
                now=datetime.fromisoformat("2026-10-24T12:00:00+02:00"), timezone="Europe/Rome"
            )
            events = [event async for event in provider.stream_propose(
                "A date", EventWorkflowState(), context,
                event_tools().schemas(EventWorkflowState()),
            )]
            assert any(event.kind == "tool_call" for event in events)

    asyncio.run(run())
    assert len(captured) == 1
    assert captured[0].prompt_eval_count == 25
    assert captured[0].eval_count == 8
    assert captured[0].total_duration == 1000
    assert captured[0].load_duration is None


def test_unsupported_fallback_persists_neutral_reply_and_explicit_language_request_takes_priority():
    requests = []
    responses = iter([
        {"message": {"tool_calls": [{"function": {"name": "ask_event_clarification", "arguments": {
            "question": "What day do you mean?", "conversation_language": "en",
        }}}]}, "done": True},
        {"message": {"tool_calls": [{"function": {"name": "ask_event_clarification", "arguments": {
            "question": "What year should I use?",
        }}}]}, "done": True},
        {"message": {"tool_calls": [{"function": {"name": "ask_event_clarification", "arguments": {
            "question": "A che ora?", "conversation_language": "it",
        }}}]}, "done": True},
        {"message": {"tool_calls": [{"function": {"name": "ask_event_clarification", "arguments": {
            "question": "I will continue in English. What time works?", "conversation_language": "en",
        }}}]}, "done": True},
    ])

    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        return ndjson(next(responses))

    async def run():
        async with httpx.AsyncClient(
            base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
        ) as client:
            from kairos.workflow import EventWorkflow

            workflow = EventWorkflow(OllamaEventProvider("test-model", client))
            context = RequestContext(
                now=datetime.fromisoformat("2026-10-24T12:00:00+02:00"),
                timezone="Europe/Rome", language="it",
            )
            state = EventWorkflowState()
            state = await workflow.advance(state, "Je voudrais prendre rendez-vous vendredi à Paris", context)
            assert state.conversation_language.value == "en"
            assert state.question == "What day do you mean?"

            state = await workflow.advance(state, "ok, 18/03/2027 alle 10", context)
            assert state.conversation_language.value == "en"
            assert state.question == "What year should I use?"

            state = await workflow.advance(state, "Veuillez continuer en italien", context)
            assert state.conversation_language.value == "it"
            assert state.question == "A che ora?"

            state = await workflow.advance(state, "I need to reschedule the appointment", context)
            assert state.conversation_language.value == "en"
            assert state.question == "I will continue in English. What time works?"
            return state

    asyncio.run(run())
    assert len(requests) == 4
    prompt = requests[0]["messages"][0]["content"]
    assert "unsupported language" in prompt
    assert "use English" in prompt
    assert "explicit request to use a supported language" in prompt
    first_input = json.loads(requests[0]["messages"][1]["content"])
    second_input = json.loads(requests[1]["messages"][1]["content"])
    third_input = json.loads(requests[2]["messages"][1]["content"])
    fourth_input = json.loads(requests[3]["messages"][1]["content"])
    assert first_input["context"]["language"] == "it"
    assert first_input["conversation_language"] is None
    assert second_input["conversation_language"] == "en"
    assert second_input["previous_question"] == "What day do you mean?"
    assert third_input["conversation_language"] == "en"
    assert third_input["previous_question"] == "What year should I use?"
    assert fourth_input["conversation_language"] == "it"
    assert fourth_input["previous_question"] == "A che ora?"


@pytest.mark.parametrize("calls", [[], [
    {"function": {"name": "update_event_draft", "arguments": {"patch": {}}}},
    {"function": {"name": "ask_event_clarification", "arguments": {"question": "Which?"}}},
]])
def test_workflow_rejects_zero_or_multiple_calls_after_stream_completion(calls):
    from kairos.workflow import EventWorkflow

    response = ndjson({"message": {"tool_calls": calls}, "done": True})
    def handler(request):
        return response

    async def run():
        async with httpx.AsyncClient(
            base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
        ) as client:
            workflow = EventWorkflow(OllamaEventProvider("test-model", client))
            context = RequestContext(now=datetime.fromisoformat("2026-10-24T12:00:00+02:00"), timezone="Europe/Rome")
            return await workflow.advance(EventWorkflowState(), "Una visita", context)
    with pytest.raises(WorkflowError):
        asyncio.run(run())
