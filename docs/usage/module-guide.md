# Start and use the Kairos backend

This guide covers the Python backend and its local CLI and HTTP API. The API prepares event drafts only; it does not save events or schedule notifications.

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

## Start the HTTP API

Run the local server from `backend/`:

```bash
uv run uvicorn kairos.api:app --reload --host 127.0.0.1 --port 8000
```

Without `KAIROS_OLLAMA_MODEL`, the API uses a deterministic demo provider. It does not interpret arbitrary text. To connect an installed Ollama model, configure:

```bash
export KAIROS_OLLAMA_MODEL=qwen3:8b
export KAIROS_OLLAMA_BASE_URL=http://localhost:11434
uv run uvicorn kairos.api:app --reload --host 127.0.0.1 --port 8000
```

`KAIROS_OLLAMA_BASE_URL` is optional and defaults to `http://localhost:11434`.

The liveness endpoint is `GET /health`. The drafting endpoint is `POST /workflow/turn`. A first request can omit `state`:

```bash
curl -N http://127.0.0.1:8000/workflow/turn \
  -H 'Content-Type: application/json' \
  -d '{"message":"I need to take my motorcycle to the mechanic tomorrow","language":"en","timezone":"Europe/Rome"}'
```

The endpoint responds as Server-Sent Events (SSE): `progress` reports workflow phases, `text` carries optional model text, `completed` carries the updated state, and `error` reports a workflow error. The client must keep the state from `completed` and send it in the next request. Omitting `state` starts a new draft. The server creates the current timestamp using the supplied IANA timezone; the client supplies the interface language and timezone. The HTTP client for Ollama is opened at application startup and closed at shutdown.

The local OpenAPI page is available at `http://127.0.0.1:8000/docs`.

## Inspect the project in VS Code

Select `backend/.venv/bin/python` as the Python interpreter. Workspace settings include paths for Pylance and pytest.
