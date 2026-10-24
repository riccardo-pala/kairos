"""Run `python -m kairos` for a scripted demo, or select an Ollama model."""

import argparse
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from kairos.providers import OllamaEventProvider, ScriptedEventProvider
from kairos.workflow import EventWorkflow, EventWorkflowState, RequestContext, ToolCall, WorkflowError


async def run(args):
    context = RequestContext(
        now=datetime.now(ZoneInfo(args.timezone)),
        language=args.language,
        timezone=args.timezone,
    )
    state = EventWorkflowState()
    async with httpx.AsyncClient(base_url="http://localhost:11434", timeout=60.0) as client:
        if args.model:
            workflow = EventWorkflow(OllamaEventProvider(args.model, client))
            print("Bozza locale in memoria; /exit per uscire. Nessun evento verrà salvato.")
            while True:
                message = input("> ")
                if message == "/exit":
                    break
                try:
                    state = await workflow.advance(state, message, context)
                    print(state.model_dump_json(indent=2))
                except WorkflowError as exc:
                    print(f"Errore: {exc}")
        else:
            print("DEMO: risposte predefinite, nessuna chiamata LLM o notifica reale.")
            provider = ScriptedEventProvider([
                ToolCall(name="update_event_draft", arguments={"patch": {
                    "title": "Visita medica", "starts_at": "2026-10-31T14:30:00",
                    "location": "Ambulatorio X", "duration_minutes": 30,
                    "tasks": [{"description": "Portare i documenti", "timing": "before"}],
                }}),
                ToolCall(name="update_event_draft", arguments={"patch": {
                    "reminders": [{"minutes_before": 60}, {"minutes_before": 1440}],
                }}),
            ])
            workflow = EventWorkflow(provider)
            for message in ["Il 31 ottobre 2026 alle 14:30 ho una visita...", "Un'ora e un giorno prima"]:
                print(f"> {message}")
                state = await workflow.advance(state, message, context)
                print(state.model_dump_json(indent=2))


def main():
    parser = argparse.ArgumentParser(description="Kairos event-draft workflow")
    parser.add_argument("--model", help="Installed Ollama model supporting tool calling")
    parser.add_argument("--language", choices=["it", "en"], default="it")
    parser.add_argument("--timezone", default="Europe/Rome")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
