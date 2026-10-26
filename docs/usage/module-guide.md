# Start and use the Kairos backend

This guide covers the Python backend and its local CLI and HTTP API. The API prepares event drafts only; it does not create calendar events or schedule notifications.

## Requirements and setup

Use Python 3.13 and `uv`. From the repository root:

```bash
cd backend
uv sync --dev
```

`uv.lock` pins the resolved dependencies. The project tests can be run with `uv run pytest` when validation is needed.

## Use the CLI

Start the scripted demo without a model:

```bash
uv run python -m kairos
```

For a real conversation, start Ollama and select a model that supports tool calling:

```bash
uv run python -m kairos --model qwen3:8b --language it --timezone Europe/Rome
```

Use `--language en` for English interface messages, `--think` to enable model reasoning generation (reasoning is not displayed), and `/exit` to end the session. The available debug options are `--debug-model-io`, `--debug-draft-json`, and `--debug-validation`; `--debug` enables all three. Model input/output and validation diagnostics go to stderr; draft JSON goes to stdout. Debug output may contain user messages and prompt data.

## Use the HTTP API

Start the API and its PostgreSQL database by following the [local infrastructure setup](local-infrastructure.md). The provider-profile migration installs a deterministic demo profile, active by default; it does not interpret arbitrary text. Provider profiles and the active selection are stored in PostgreSQL and survive API restarts.

`GET /health` checks the database connection. `POST /sessions` creates a UUID session and stores the selected interface language and IANA timezone:

```bash
curl -s http://127.0.0.1:8000/sessions \
  -H 'Content-Type: application/json' \
  -d '{"language":"en","timezone":"Europe/Rome"}'
```

Use the returned `id` to send a turn. The client sends only the current message; it does not send `EventWorkflowState`:

```bash
curl -N http://127.0.0.1:8000/sessions/SESSION_UUID/turn \
  -H 'Content-Type: application/json' \
  -d '{"message":"I need to take my motorcycle to the mechanic tomorrow"}'
```

The response is Server-Sent Events (SSE): `progress` reports workflow phases, `text` carries optional model text, `completed` contains the persisted session, draft, and derived guidance, and `error` reports a workflow or concurrency error. A completed state is committed before its SSE event is sent. `GET /sessions/SESSION_UUID` reads the current draft, guidance, and session metadata. Only the current state is stored; chat messages and transcript history are not saved or sent to the model. The model receives the current user message, draft, and previous question as context, but the question does not restrict which fields can be updated.

The turn endpoint also accepts a structured action so form controls can update a field without a model call. For example, a 2-hour reminder can be added with:

```bash
curl -N http://127.0.0.1:8000/sessions/SESSION_UUID/turn \
  -H 'Content-Type: application/json' \
  -d '{"action":{"type":"add_reminder","minutes_before":120}}'
```

The session response includes required fields still missing and localized templates for title, date, time, location, duration, reminders, and an explicitly described activity before or after the event. The user can ignore a template or submit any other free-text update instead. Structured actions are applied by Python without calling the model. An activity action includes its description and timing:

```json
{"action":{"type":"add_task","description":"Pick up the documents","timing":"before"}}
```

The local OpenAPI page is available at `http://127.0.0.1:8000/docs`.

### Use the local playground

With Docker Compose running, open `http://127.0.0.1:8000/`. The page creates and chats through a session, displays SSE progress/text/completed/error events, shows the validated draft, and lets you list and activate the built-in provider profiles. Its diagnostics panel reads recent structured API, connector, and workflow logs from a bounded in-memory buffer and can filter by the request ID returned with each turn. The buffer is local to the API process and clears on restart. The playground and its admin endpoints have no authentication; keep them on localhost. Logs may contain prompts, user messages, and session data.

### Select a model provider

The database migration installs three built-in profiles: deterministic **Demo** (active initially), **Local Ollama (Qwen 3 8B)** using `qwen3:8b`, and **Hugging Face (Qwen3 8B)** using `Qwen/Qwen3-8B`. The Hugging Face router selects a compatible inference provider automatically from the bare model ID. These profiles are fixed in this prototype; the local admin API only lists them and activates one.

First list the profiles and copy the `id` of the one to use:

```bash
curl -s http://127.0.0.1:8000/admin/provider-profiles
```

Activate that profile; it will be used for the next API turn without restarting the service:

```bash
curl -s -X POST http://127.0.0.1:8000/admin/provider-profiles/PROFILE_UUID/activate
```

For Ollama to work, start Ollama on the host and make sure `qwen3:8b` is installed. Compose reaches it through the built-in endpoint `http://host.docker.internal:11434`. The Hugging Face profile uses the managed Inference Providers router; configure `HF_TOKEN` as described in [Local infrastructure setup](local-infrastructure.md) before activating it. The token is never stored in PostgreSQL.

These admin endpoints have no authentication. Use them only with the local API bound to localhost; the prototype must not be exposed to the Internet.

## Inspect the project in VS Code

Select `backend/.venv/bin/python` as the Python interpreter. Workspace settings include paths for Pylance and pytest.
