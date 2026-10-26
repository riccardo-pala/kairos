"""Streaming adapter for Hugging Face Inference Providers."""

import json
from collections.abc import AsyncIterator
from typing import Callable

import httpx
from pydantic import ValidationError

from kairos.contracts import EventWorkflowState, ProviderEvent, RequestContext, ToolCall, WorkflowError
from kairos.i18n import Language, MessageId
from kairos.providers.prompts import SYSTEM_PROMPT


class HuggingFaceEventProvider:
    """OpenAI-compatible streaming adapter for Hugging Face Inference Providers."""

    endpoint = "/chat/completions"

    def __init__(
        self,
        model: str,
        token: str | None,
        client: httpx.AsyncClient,
        *,
        system_prompt: str | None = None,
        model_io_callback: Callable[[str, str], None] | None = None,
        failure_callback: Callable[[dict], None] | None = None,
        debug_connector_logs: bool = False,
    ):
        self.model = model
        self.token = token
        self.client = client
        self.system_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT
        self.model_io_callback = model_io_callback
        self.failure_callback = failure_callback
        self.debug_connector_logs = debug_connector_logs

    async def stream_propose(
        self, message: str, state: EventWorkflowState, context: RequestContext, tools: list[dict]
    ) -> AsyncIterator[ProviderEvent]:
        if not self.token:
            self._trace_failure(RuntimeError("HF_TOKEN is not configured"), None, None)
            raise WorkflowError(MessageId.MODEL_UNAVAILABLE)

        request_context = {
            "context": context.model_dump(mode="json"),
            "current_draft": state.draft.model_dump(mode="json"),
            "previous_question": state.question,
            "conversation_language": state.conversation_language.value
            if state.conversation_language else None,
            "supported_languages": [language.value for language in Language],
            "message": message,
        }
        payload = {
            "model": self.model,
            "stream": True,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": json.dumps(request_context, ensure_ascii=False)},
            ],
            "tools": tools,
        }
        self._trace("request", json.dumps(payload, ensure_ascii=False, indent=2))
        response_status = None
        response_excerpt = None
        frame_count = 0
        response_text: list[str] = []
        tool_calls: dict[int, dict[str, str]] = {}
        received_done = False

        try:
            async with self.client.stream(
                "POST",
                self.endpoint,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "text/event-stream",
                },
            ) as response:
                response_status = response.status_code
                if response.is_error and self.debug_connector_logs:
                    raw_body = (await response.aread()).decode("utf-8", errors="replace")
                    if self.token:
                        raw_body = raw_body.replace(self.token, "[REDACTED]")
                    response_excerpt = raw_body[:1200]
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        received_done = True
                        break
                    if not data:
                        continue

                    frame = json.loads(data)
                    if not isinstance(frame, dict):
                        raise ValueError("Inference Providers frame must be a JSON object")
                    frame_count += 1
                    if frame.get("error"):
                        raise httpx.ProtocolError("Inference Providers returned an error frame")
                    choices = frame.get("choices", [])
                    if not isinstance(choices, list):
                        raise ValueError("Inference Providers choices must be a list")

                    for choice in choices:
                        if not isinstance(choice, dict):
                            raise ValueError("Inference Providers choice must be an object")
                        delta = choice.get("delta", {})
                        if not isinstance(delta, dict):
                            raise ValueError("Inference Providers delta must be an object")
                        content = delta.get("content")
                        if content is not None:
                            if not isinstance(content, str):
                                raise ValueError("Inference Providers content must be text")
                            if content:
                                response_text.append(content)
                                yield ProviderEvent(kind="text", text=content)

                        chunks = delta.get("tool_calls") or []
                        if not isinstance(chunks, list):
                            raise ValueError("Inference Providers tool_calls must be a list")
                        for chunk in chunks:
                            if not isinstance(chunk, dict) or type(chunk.get("index")) is not int:
                                raise ValueError("Inference Providers tool call must include an index")
                            index = chunk["index"]
                            call = tool_calls.setdefault(index, {"name": "", "arguments": ""})
                            function = chunk.get("function", {})
                            if not isinstance(function, dict):
                                raise ValueError("Inference Providers function must be an object")
                            name = function.get("name") or ""
                            arguments = function.get("arguments") or ""
                            if not isinstance(name, str) or not isinstance(arguments, str):
                                raise ValueError("Inference Providers function chunks must be text")
                            call["name"] += name
                            call["arguments"] += arguments

            if not received_done:
                raise ValueError("Inference Providers stream ended before its [DONE] frame")

            for index in sorted(tool_calls):
                call = tool_calls[index]
                arguments = json.loads(call["arguments"])
                if not isinstance(arguments, dict):
                    raise ValueError("Inference Providers tool arguments must be an object")
                yield ProviderEvent(
                    kind="tool_call",
                    tool_call=ToolCall(name=call["name"], arguments=arguments),
                )
        except httpx.HTTPError as exc:
            self._trace_failure(exc, response_status, response_excerpt)
            raise WorkflowError(MessageId.MODEL_UNAVAILABLE) from exc
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            self._trace_failure(exc, response_status, None)
            raise WorkflowError(MessageId.INVALID_TOOL_CALL) from exc
        finally:
            if self.model_io_callback is not None:
                response_summary = {
                    "http_status": response_status,
                    "stream_frames": frame_count,
                    "message": {
                        "role": "assistant",
                        "content": "".join(response_text),
                        "tool_calls": [
                            {
                                "function": {
                                    "name": call["name"],
                                    "arguments": call["arguments"],
                                }
                            }
                            for _, call in sorted(tool_calls.items())
                        ],
                    },
                }
                self._trace(
                    "response", json.dumps(response_summary, ensure_ascii=False, indent=2)
                )

    def _trace(self, direction: str, content: str) -> None:
        if self.model_io_callback is not None:
            if self.token:
                content = content.replace(self.token, "[REDACTED]")
            self.model_io_callback(direction, content)

    def _trace_failure(self, exc: Exception, status: int | None, body: str | None) -> None:
        if self.failure_callback is not None:
            self.failure_callback({
                "provider": "huggingface",
                "model": self.model,
                "exception_type": type(exc).__name__,
                "http_status": status,
                "response_body_excerpt": body,
            })
