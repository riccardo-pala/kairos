"""Run `python -m kairos` for a scripted demo, or select an Ollama model."""

import argparse
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from kairos.providers import OllamaEventProvider, ScriptedEventProvider
from kairos.contracts import EventWorkflowState, RequestContext, ToolCall, WorkflowError
from kairos.i18n import Language, MessageId, translate
from kairos.workflow import EventWorkflow


async def run(args):
    context = RequestContext(
        now=datetime.now(ZoneInfo(args.timezone)),
        language=args.language,
        timezone=args.timezone,
    )
    state = EventWorkflowState()
    def text(message_id):
        return translate(message_id, context.language)

    async with httpx.AsyncClient(base_url="http://localhost:11434", timeout=60.0) as client:
        if args.model:
            workflow = EventWorkflow(OllamaEventProvider(args.model, client))
            print(text(MessageId.CLI_SESSION))
            while True:
                message = await asyncio.to_thread(input, "> ")
                if message == "/exit":
                    break
                streamed_text = False
                try:
                    async for event in workflow.stream_advance(state, message, context):
                        if event.kind == "progress":
                            if streamed_text:
                                print()
                                streamed_text = False
                            print(event.message, flush=True)
                        elif event.kind == "text":
                            print(event.text, end="", flush=True)
                            streamed_text = True
                        elif event.kind == "completed":
                            state = event.state
                            if streamed_text:
                                print()
                                streamed_text = False
                            if state.question:
                                print(f"{text(MessageId.CLI_NEEDS_CLARIFICATION)} {state.question}")
                            else:
                                print(text(MessageId.CLI_READY))
                            print(state.draft.model_dump_json(indent=2))
                except WorkflowError as exc:
                    if streamed_text:
                        print()
                    print(f"{text(MessageId.CLI_ERROR)}: {exc.text(context.language)}")
        else:
            print(text(MessageId.CLI_DEMO))
            provider = ScriptedEventProvider([
                ToolCall(name="update_event_draft", arguments={"patch": {
                    "title": text(MessageId.DEMO_TITLE), "starts_at": "2026-10-31T14:30:00",
                    "location": "Ambulatorio X", "duration_minutes": 30,
                    "tasks": [{"description": text(MessageId.DEMO_TASK), "timing": "before"}],
                }}),
                ToolCall(name="update_event_draft", arguments={"patch": {
                    "reminders": [{"minutes_before": 60}, {"minutes_before": 1440}],
                }}),
            ])
            workflow = EventWorkflow(provider)
            for message in [text(MessageId.DEMO_FIRST_MESSAGE), text(MessageId.DEMO_SECOND_MESSAGE)]:
                print(f"> {message}")
                state = await workflow.advance(state, message, context)
                if state.question:
                    print(f"{text(MessageId.CLI_NEEDS_CLARIFICATION)} {state.question}")
                else:
                    print(text(MessageId.CLI_READY))
                print(state.draft.model_dump_json(indent=2))


def main():
    language_parser = argparse.ArgumentParser(add_help=False)
    language_parser.add_argument("--language", choices=list(Language), default=Language.IT)
    language_args, _ = language_parser.parse_known_args()
    language = Language(language_args.language)
    parser = argparse.ArgumentParser(description=translate(MessageId.CLI_DESCRIPTION, language))
    parser.add_argument("--model", help=translate(MessageId.CLI_MODEL_HELP, language))
    parser.add_argument("--language", choices=list(Language), default=Language.IT,
                        help=translate(MessageId.CLI_LANGUAGE_HELP, language))
    parser.add_argument("--timezone", default="Europe/Rome",
                        help=translate(MessageId.CLI_TIMEZONE_HELP, language))
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
