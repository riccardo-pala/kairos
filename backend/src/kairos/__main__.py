"""Run `python -m kairos` for a scripted demo, or select an Ollama model."""

import argparse
import asyncio
from datetime import datetime
import os
import sys
from zoneinfo import ZoneInfo

import httpx

from kairos.providers import OllamaEventProvider, ScriptedEventProvider
from kairos.contracts import EventWorkflowState, RequestContext, ToolCall, WorkflowError
from kairos.i18n import Language, MessageId, translate
from kairos.workflow import EventWorkflow


def _debug_style(value: str, ansi: str, enabled: bool) -> str:
    return f"\033[{ansi}m{value}\033[0m" if enabled else value


def _model_io_trace(direction: str, content: str, language: Language) -> None:
    color = sys.stderr.isatty() and "NO_COLOR" not in os.environ
    message_id = (
        MessageId.CLI_DEBUG_MODEL_REQUEST
        if direction == "request"
        else MessageId.CLI_DEBUG_MODEL_RESPONSE
    )
    heading = translate(message_id, language)
    print(_debug_style(f"[{heading}]", "1;35", color), file=sys.stderr, flush=True)
    print(content, file=sys.stderr, flush=True)


def print_draft(state: EventWorkflowState, language: Language, *, debug: bool = False) -> None:
    draft = state.draft
    color_summary = sys.stdout.isatty() and "NO_COLOR" not in os.environ

    def emit_field(label: str, value: str, indent: int = 2) -> None:
        prefix = " " * indent
        label = _debug_style(label, "1;33", color_summary)
        value = _debug_style(value, "97", color_summary)
        print(f"{prefix}{label}: {value}")

    summary = translate(MessageId.CLI_DRAFT_SUMMARY, language)
    print(_debug_style(summary, "1;36", color_summary))
    if draft.title:
        emit_field(translate(MessageId.CLI_EVENT_TITLE, language), draft.title)
    if draft.start_date:
        emit_field(translate(MessageId.CLI_EVENT_DATE, language), draft.start_date.isoformat())
    if draft.start_time:
        emit_field(translate(MessageId.CLI_EVENT_TIME, language), draft.start_time.isoformat(timespec="minutes"))
    if draft.timezone:
        emit_field(translate(MessageId.CLI_EVENT_TIMEZONE, language), draft.timezone)
    if draft.location:
        emit_field(translate(MessageId.CLI_EVENT_LOCATION, language), draft.location)
    if draft.duration_minutes is not None:
        minutes = translate(MessageId.CLI_MINUTES, language).format(
            value=draft.duration_minutes
        )
        emit_field(translate(MessageId.CLI_EVENT_DURATION, language), minutes)
    if draft.tasks:
        task_label = _debug_style(translate(MessageId.CLI_EVENT_TASKS, language), "1;34", color_summary)
        print(f"  {task_label}:")
        for task in draft.tasks:
            timing = translate(
                MessageId.CLI_TASK_BEFORE if task.timing == "before" else MessageId.CLI_TASK_AFTER,
                language,
            )
            description = _debug_style(task.description, "97", color_summary)
            timing = _debug_style(timing, "90", color_summary)
            print(f"    - {description} ({timing})")
    if draft.reminders is not None:
        label = translate(MessageId.CLI_EVENT_REMINDERS, language)
        if not draft.reminders:
            emit_field(label, translate(MessageId.CLI_NO_REMINDERS, language))
        else:
            label = _debug_style(label, "1;34", color_summary)
            print(f"  {label}:")
            for reminder in draft.reminders:
                minutes = translate(MessageId.CLI_MINUTES, language).format(
                    value=reminder.minutes_before
                )
                before = translate(MessageId.CLI_TASK_BEFORE, language)
                minutes = _debug_style(minutes, "97", color_summary)
                before = _debug_style(before, "90", color_summary)
                print(f"    - {minutes} {before}")
    if debug:
        json_label = _debug_style(translate(MessageId.CLI_DEBUG_JSON, language), "1;35", color_summary)
        debug_json = _debug_style(state.model_dump_json(indent=2), "35", color_summary)
        print(json_label)
        print(debug_json)


async def run(args):
    context = RequestContext(
        now=datetime.now(ZoneInfo(args.timezone)),
        language=args.language,
        timezone=args.timezone,
    )
    state = EventWorkflowState()
    def text(message_id):
        return translate(message_id, context.language)

    debug_model_io = args.debug or args.debug_model_io
    debug_draft_json = args.debug or args.debug_draft_json
    debug_validation = args.debug or args.debug_validation
    async with httpx.AsyncClient(base_url="http://localhost:11434", timeout=60.0) as client:
        if args.model:
            def trace(direction: str, content: str) -> None:
                _model_io_trace(direction, content, context.language)

            workflow = EventWorkflow(OllamaEventProvider(
                args.model,
                client,
                think=args.think,
                model_io_callback=trace if debug_model_io else None,
            ))
            print(text(MessageId.CLI_SESSION))
            while True:
                message = await asyncio.to_thread(input, "> ")
                if message == "/exit":
                    break
                try:
                    async for event in workflow.stream_advance(state, message, context):
                        if event.kind == "progress":
                            print(event.message, flush=True)
                        elif event.kind == "completed":
                            state = event.state
                            if state.question:
                                print(f"{text(MessageId.CLI_NEEDS_CLARIFICATION)} {state.question}")
                            else:
                                print(text(MessageId.CLI_READY))
                            print_draft(state, context.language, debug=debug_draft_json)
                except WorkflowError as exc:
                    print(f"{text(MessageId.CLI_ERROR)}: {exc.text(context.language)}")
                    if debug_validation and exc.__cause__ is not None:
                        details = f"[DEBUG validation] {exc.__cause__}"
                        color_debug = sys.stderr.isatty() and "NO_COLOR" not in os.environ
                        print(_debug_style(details, "35", color_debug), file=sys.stderr, flush=True)
        else:
            print(text(MessageId.CLI_DEMO))
            provider = ScriptedEventProvider([
                ToolCall(name="update_event_draft", arguments={"patch": {
                    "title": text(MessageId.DEMO_TITLE), "start_date": "2026-10-31",
                    "start_time": "14:30",
                    "location": "Ambulatorio X", "duration_minutes": 30,
                }, "task_operations": {
                    "add": [{
                        "description": text(MessageId.DEMO_TASK),
                        "timing": "before",
                        "evidence": text(MessageId.DEMO_FIRST_MESSAGE),
                    }],
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
                print_draft(state, context.language, debug=debug_draft_json)


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
    parser.add_argument("--debug-model-io", action="store_true",
                        help=translate(MessageId.CLI_DEBUG_MODEL_IO_HELP, language))
    parser.add_argument("--debug-draft-json", action="store_true",
                        help=translate(MessageId.CLI_DEBUG_DRAFT_JSON_HELP, language))
    parser.add_argument("--debug-validation", action="store_true",
                        help=translate(MessageId.CLI_DEBUG_VALIDATION_HELP, language))
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
