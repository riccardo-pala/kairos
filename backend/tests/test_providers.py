import asyncio
import json
from datetime import datetime

import httpx
import pytest

from kairos.providers import OllamaEventProvider
from kairos.contracts import EventWorkflowState, RequestContext, WorkflowError
from kairos.tools import event_tools


def request_to_provider(handler):
    async def request():
        async with httpx.AsyncClient(
            base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
        ) as client:
            provider = OllamaEventProvider("test-model", client)
            context = RequestContext(
                now=datetime.fromisoformat("2026-10-24T12:00:00+02:00"),
                timezone="Europe/Rome",
            )
            return await provider.propose("Una visita", EventWorkflowState(), context, event_tools().schemas(EventWorkflowState()))
    return asyncio.run(request())


def test_ollama_adapter_sends_schema_and_context_and_parses_tool_call():
    def handler(request):
        payload = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert payload["stream"] is False
        assert payload["tools"][0]["function"]["name"] == "update_event_draft"
        assert payload["tools"][1]["function"]["name"] == "ask_event_clarification"
        data = json.loads(payload["messages"][1]["content"])
        assert data["context"]["timezone"] == "Europe/Rome"
        assert data["message"] == "Una visita"
        assert set(data["supported_languages"]) == {"it", "en"}
        return httpx.Response(200, json={"message": {"tool_calls": [
            {"function": {"name": "update_event_draft", "arguments": {"patch": {"title": "Visita"}}}}
        ]}})
    assert request_to_provider(handler).arguments["patch"]["title"] == "Visita"


@pytest.mark.parametrize("body", [
    {"message": {"content": "Saved your event!"}},
    {"message": {"tool_calls": []}},
    {"message": {"tool_calls": [{"function": {}}, {"function": {}}]}},
    {"message": {"tool_calls": [{"function": {"name": "update_event_draft", "arguments": "invalid"}}]}},
])
def test_missing_or_malformed_tool_call_fails_closed(body):
    with pytest.raises(WorkflowError):
        request_to_provider(lambda request: httpx.Response(200, json=body))


def test_provider_error_does_not_expose_response_body():
    with pytest.raises(WorkflowError, match="unavailable"):
        request_to_provider(lambda request: httpx.Response(500, text="sensitive body"))
