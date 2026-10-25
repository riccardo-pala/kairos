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

Start the API and its PostgreSQL database by following the [local infrastructure setup](local-infrastructure.md). The API uses a deterministic demo provider unless `KAIROS_OLLAMA_MODEL` is configured; the demo provider does not interpret arbitrary text.

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

The response is Server-Sent Events (SSE): `progress` reports workflow phases, `text` carries optional model text, `completed` contains the persisted session and updated draft, and `error` reports a workflow or concurrency error. A completed state is committed before its SSE event is sent. `GET /sessions/SESSION_UUID` reads the current draft and session metadata. Only the current state is stored; chat messages and transcript history are not saved or sent to the model. The model receives the current user message, draft, and previous question.

The local OpenAPI page is available at `http://127.0.0.1:8000/docs`.

## Inspect the project in VS Code

Select `backend/.venv/bin/python` as the Python interpreter. Workspace settings include paths for Pylance and pytest.
