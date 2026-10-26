"""Fixed provider responses for demos and deterministic workflows."""

from collections.abc import AsyncIterator

from kairos.contracts import EventWorkflowState, ProviderEvent, RequestContext, ToolCall, WorkflowError
from kairos.i18n import MessageId


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
