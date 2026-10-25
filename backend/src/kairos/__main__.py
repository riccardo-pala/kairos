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


def print_draft(state: EventWorkflowState, language: Language, *, debug: bool = False) -> None:
    draft = state.draft
    print(translate(MessageId.CLI_DRAFT_SUMMARY, language))
    if draft.title:
        print(f"  {translate(MessageId.CLI_EVENT_TITLE, language)}: {draft.title}")
    if draft.start_date:
        print(f"  {translate(MessageId.CLI_EVENT_DATE, language)}: {draft.start_date.isoformat()}")
    if draft.start_time:
        print(f"  {translate(MessageId.CLI_EVENT_TIME, language)}: {draft.start_time.isoformat(timespec='minutes')}")
    if draft.timezone:
        print(f"  {translate(MessageId.CLI_EVENT_TIMEZONE, language)}: {draft.timezone}")
    if draft.location:
        print(f"  {translate(MessageId.CLI_EVENT_LOCATION, language)}: {draft.location}")
    if draft.duration_minutes is not None:
        minutes = translate(MessageId.CLI_MINUTES, language).format(
            value=draft.duration_minutes
        )
        print(f"  {translate(MessageId.CLI_EVENT_DURATION, language)}: {minutes}")
    if draft.tasks:
        print(f"  {translate(MessageId.CLI_EVENT_TASKS, language)}:")
        for task in draft.tasks:
            timing = translate(
                MessageId.CLI_TASK_BEFORE if task.timing == "before" else MessageId.CLI_TASK_AFTER,
                language,
            )
            print(f"    - {task.description} ({timing})")
    if draft.reminders is not None:
        label = translate(MessageId.CLI_EVENT_REMINDERS, language)
        if not draft.reminders:
            print(f"  {label}: {translate(MessageId.CLI_NO_REMINDERS, language)}")
        else:
            print(f"  {label}:")
            for reminder in draft.reminders:
                minutes = translate(MessageId.CLI_MINUTES, language).format(
                    value=reminder.minutes_before
                )
                before = translate(MessageId.CLI_TASK_BEFORE, language)
                print(f"    - {minutes} {before}")
    if debug:
        print(state.model_dump_json(indent=2))


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
            workflow = EventWorkflow(OllamaEventProvider(args.model, client, think=args.think))
            print(text(MessageId.CLI_SESSION))
            while True:
                message = await asyncio.to_thread(input, "> ")
                if message == "/exit":
                    break
                streamed_text = False
                try:
                    async for event in workflow.stream_advance(state, message, context):
                        if event.kind == "progress":
                            if args.debug and streamed_text:
                                print()
                                streamed_text = False
                            print(event.message, flush=True)
                        elif event.kind == "text":
                            if args.debug:
                                print(event.text, end="", flush=True)
                                streamed_text = True
                        elif event.kind == "completed":
                            state = event.state
                            if args.debug and streamed_text:
                                print()
                                streamed_text = False
                            if state.question:
                                print(f"{text(MessageId.CLI_NEEDS_CLARIFICATION)} {state.question}")
                            else:
                                print(text(MessageId.CLI_READY))
                            print_draft(state, context.language, debug=args.debug)
                except WorkflowError as exc:
                    if args.debug and streamed_text:
                        print()
                    print(f"{text(MessageId.CLI_ERROR)}: {exc.text(context.language)}")
        else:
            print(text(MessageId.CLI_DEMO))
            provider = ScriptedEventProvider([
                ToolCall(name="update_event_draft", arguments={"patch": {
                    "title": text(MessageId.DEMO_TITLE), "start_date": "2026-10-31",
                    "start_time": "14:30",
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
                print_draft(state, context.language, debug=args.debug)


def main():
    language_parser = argparse.ArgumentParser(add_help=False)
    language_parser.add_argument("--language", choices=list(Language), default=Language.IT)
    language_args, _ = language_parser.parse_known_args()
    language = Language(language_args.language)
    parser = argparse.ArgumentParser(description=translate(MessageId.CLI_DESCRIPTION, language))
    parser.add_argument("--model", help=translate(MessageId.CLI_MODEL_HELP, language))
    parser.add_argument("--think", action="store_true",
                        help=translate(MessageId.CLI_THINK_HELP, language))
    parser.add_argument("--language", choices=list(Language), default=Language.IT,
                        help=translate(MessageId.CLI_LANGUAGE_HELP, language))
    parser.add_argument("--timezone", default="Europe/Rome",
                        help=translate(MessageId.CLI_TIMEZONE_HELP, language))
    parser.add_argument("--debug", action="store_true",
                        help=translate(MessageId.CLI_DEBUG_HELP, language))
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
