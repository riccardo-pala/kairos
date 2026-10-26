"""Streaming adapter for a local Ollama model."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Callable

import httpx
from pydantic import ValidationError

from kairos.contracts import EventWorkflowState, ProviderEvent, RequestContext, ToolCall, WorkflowError
from kairos.i18n import Language, MessageId
from kairos.providers.prompts import SYSTEM_PROMPT


@dataclass(frozen=True)
class OllamaMetrics:
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    prompt_eval_cached_count: int | None = None
    prompt_eval_duration: int | None = None
    eval_count: int | None = None
    eval_duration: int | None = None

    @classmethod
    def from_done_frame(cls, frame: dict) -> "OllamaMetrics":
        names = cls.__dataclass_fields__
        values = {}
        for name in names:
            value = frame.get(name)
            values[name] = value if type(value) is int and value >= 0 else None
        return cls(**values)


class OllamaEventProvider:
    def __init__(
        self,
        model: str,
        client: httpx.AsyncClient,
        *,
        endpoint_url: str | None = None,
        system_prompt: str | None = None,
        think: bool | None = None,
        options: dict | None = None,
        metrics_callback: Callable[[OllamaMetrics], None] | None = None,
        model_io_callback: Callable[[str, str], None] | None = None,
        failure_callback: Callable[[dict], None] | None = None,
        debug_connector_logs: bool = False,
    ):
        self.model = model
        self.client = client
        self.endpoint_url = (
            f"{endpoint_url.rstrip('/')}/api/chat" if endpoint_url else "/api/chat"
        )
        self.system_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT
        self.think = think
        self.options = options
        self.metrics_callback = metrics_callback
        self.model_io_callback = model_io_callback
        self.failure_callback = failure_callback
        self.debug_connector_logs = debug_connector_logs

    async def stream_propose(
        self, message: str, state: EventWorkflowState, context: RequestContext, tools: list[dict]
    ) -> AsyncIterator[ProviderEvent]:
        current_draft = state.draft.model_dump(mode="json")
        for task in current_draft["tasks"]:
            task.pop("id", None)
        payload = {
            "model": self.model,
            "stream": True,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "context": context.model_dump(mode="json"),
                            "current_draft": current_draft,
                            "previous_question": state.question,
                            "conversation_language": state.conversation_language.value
                            if state.conversation_language else None,
                            "supported_languages": [language.value for language in Language],
                            "message": message,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "tools": tools,
        }
        if self.think is not None:
            payload["think"] = self.think
        if self.options is not None:
            payload["options"] = self.options
        self._trace("request", json.dumps(payload, ensure_ascii=False, indent=2))
        received_done = False
        response_status = None
        response_excerpt = None
        debug_frames: list[dict] | None = [] if self.model_io_callback is not None else None
        try:
            async with self.client.stream("POST", self.endpoint_url, json=payload) as response:
                response_status = response.status_code
                if response.is_error and self.debug_connector_logs:
                    response_excerpt = (await response.aread()).decode("utf-8", errors="replace")[:1200]
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    frame = json.loads(line)
                    if not isinstance(frame, dict):
                        raise ValueError("Ollama frame must be a JSON object")
                    if debug_frames is not None:
                        debug_frames.append(json.loads(self._frame_for_debug(frame)))
                    if frame.get("error"):
                        raise httpx.ProtocolError("Ollama returned an error frame")
                    msg = frame.get("message", {})
                    if not isinstance(msg, dict):
                        raise ValueError("Ollama message must be an object")
                    content = msg.get("content", "")
                    if content:
                        if not isinstance(content, str):
                            raise ValueError("Ollama content must be text")
                        yield ProviderEvent(kind="text", text=content)
                    calls = msg.get("tool_calls", [])
                    if not isinstance(calls, list):
                        raise ValueError("Ollama tool_calls must be a list")
                    for call in calls:
                        function = call["function"]
                        arguments = function["arguments"]
                        yield ProviderEvent(
                            kind="tool_call",
                            tool_call=ToolCall(name=function["name"], arguments=arguments),
                        )
                    done = frame.get("done")
                    if not isinstance(done, bool):
                        raise ValueError("Ollama frame is missing a boolean done flag")
                    if done:
                        received_done = True
                        if self.metrics_callback is not None:
                            self.metrics_callback(OllamaMetrics.from_done_frame(frame))
                        break
            if not received_done:
                raise ValueError("Ollama stream ended before its done frame")
        except httpx.HTTPError as exc:
            self._trace_failure(exc, response_status, response_excerpt)
            raise WorkflowError(MessageId.MODEL_UNAVAILABLE) from exc
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            self._trace_failure(exc, response_status, None)
            raise WorkflowError(MessageId.INVALID_TOOL_CALL) from exc
        finally:
            if debug_frames is not None:
                self._trace(
                    "response",
                    self._aggregate_debug_frames(debug_frames, response_status),
                )

    def _trace(self, direction: str, content: str) -> None:
        if self.model_io_callback is not None:
            self.model_io_callback(direction, content)

    def _trace_failure(self, exc: Exception, status: int | None, body: str | None) -> None:
        if self.failure_callback is not None:
            self.failure_callback({
                "provider": "ollama",
                "model": self.model,
                "exception_type": type(exc).__name__,
                "http_status": status,
                "response_body_excerpt": body,
            })

    @staticmethod
    def _frame_for_debug(frame: dict) -> str:
        """Keep useful protocol data but never print Ollama's thinking field."""
        def redact(value):
            if isinstance(value, dict):
                return {key: redact(item) for key, item in value.items() if key != "thinking"}
            if isinstance(value, list):
                return [redact(item) for item in value]
            return value

        safe_frame = redact(frame)
        return json.dumps(safe_frame, ensure_ascii=False, indent=2)

    @staticmethod
    def _aggregate_debug_frames(frames: list[dict], status: int | None) -> str:
        """Render a streamed response once, with text and tool calls reassembled."""
        response = {"http_status": status, "stream_frames": len(frames)}
        message = {"role": "assistant", "content": "", "tool_calls": []}
        for frame in frames:
            for key, value in frame.items():
                if key != "message":
                    response[key] = value
                    continue
                if not isinstance(value, dict):
                    continue
                if isinstance(value.get("role"), str):
                    message["role"] = value["role"]
                content = value.get("content")
                if isinstance(content, str):
                    message["content"] += content
                tool_calls = value.get("tool_calls")
                if isinstance(tool_calls, list):
                    message["tool_calls"].extend(tool_calls)
        response["message"] = message
        return json.dumps(response, ensure_ascii=False, indent=2)
