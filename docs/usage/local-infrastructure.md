# Local infrastructure setup

This guide starts the local HTTP API and PostgreSQL database with Docker Compose. This Compose configuration is for local development; a future deployment pipeline can build the backend image, but should use deployment-specific configuration and secrets. For API endpoints and model profiles, see [Start and use the module](module-guide.md).

## Start the API and PostgreSQL

From the repository root, build and start the services:

```bash
docker compose up --build
```

Compose binds the API to `127.0.0.1:8000` and PostgreSQL to `127.0.0.1:5432`. PostgreSQL data is stored in the `kairos-postgres` named volume. The API waits for the database health check and applies versioned SQL migrations from `backend/migrations/` at startup.

Open the local developer playground at [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Create a session (Italian and `Europe/Rome` are preselected), describe an event, and follow the streamed progress and response. The page also lets you inspect and activate a built-in provider, review the validated draft and raw SSE events, and filter local diagnostic records by the turn's request ID. The playground and admin endpoints are unauthenticated developer tools; use only with this localhost-bound Compose setup.

Database migrations leave two real-provider profiles: local Ollama (`qwen3:8b` at `http://host.docker.internal:11434`) and Hugging Face (`Qwen/Qwen3-8B`). Migration `003` removes the historical demo profile, preserving an active real provider or selecting Ollama if necessary. The simulated provider is used only by the browser demo. The profiles and current selection are stored in PostgreSQL and persist across container restarts. Select one through the local admin API described in the [module guide](module-guide.md).

## Debug the API locally with VS Code

To use Python breakpoints while keeping PostgreSQL in Docker and the playground in a browser, stop the Compose API and leave the database running:

```bash
docker compose stop api
docker compose up -d db
```

In VS Code, select **Kairos API + playground** in Run and Debug and press F5. This launches Uvicorn from `backend/.venv`, with the API bound to `127.0.0.1:8000` and all three local diagnostic categories enabled. The launch configuration reads `.env.local` for `HF_TOKEN`. Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) to use the same playground served by FastAPI; requests made there hit breakpoints in `backend/src/kairos`.

This launch does not use Uvicorn's `--reload`, so breakpoints stay in the debugged process. Restart the VS Code debug session after changing Python code. Keep the database container running; its data volume is unchanged.

## Connect Hugging Face Inference Providers

Create a fine-grained Hugging Face access token with the **Make calls to Inference Providers** permission. Add it to the root `.env.local` file; do not commit or paste the real value into documentation:

```dotenv
HF_TOKEN=hf_your_token
```

Compose does not load `.env.local` automatically, so start or recreate the API with that file:

```bash
docker compose --env-file .env.local up --build
```

`.env.local` is used for `HF_TOKEN` only; do not put the logging flags there. Compose currently sets `PLAYGROUND_DEBUG_API_LOGS`, `PLAYGROUND_DEBUG_CONNECTOR_LOGS`, and `PLAYGROUND_DEBUG_INTERNAL_LOGS` to `true` directly so the playground can display diagnostics. Kairos does not store the HF token in PostgreSQL. After startup, list profiles and activate the built-in Hugging Face profile using its returned ID. Its bare model ID is routed automatically through Hugging Face Inference Providers. See the module guide for the activation request.

The admin endpoints have no authentication and must only be used with the local API bound to localhost. Switching the active profile affects the next API turn; it does not require a container restart. HF usage and credits are managed separately in your Hugging Face account.

## API logs and model diagnostics

The API writes structured JSON log lines to container stdout. Routine Uvicorn access logs are disabled and successful `/health` checks are omitted. When API logging is enabled, health-check failures remain visible. Other HTTP requests include a request ID, method, route, response status, and elapsed time. Since SSE turns return HTTP 200 even when workflow processing fails, the API also logs each turn's terminal `completed` or `error` outcome with the same request ID.

The API settings default all diagnostic categories to off, but the local Compose file currently overrides them to `true` for the playground. The flags are `PLAYGROUND_DEBUG_API_LOGS`, `PLAYGROUND_DEBUG_CONNECTOR_LOGS`, and `PLAYGROUND_DEBUG_INTERNAL_LOGS`; to turn one off in Compose, change its value in `compose.yaml`. Do not add them to `.env.local`, which is reserved for `HF_TOKEN`.

`PLAYGROUND_DEBUG_API_LOGS` writes request/response metadata and SSE terminal outcomes with a shared request ID; successful health checks remain quiet. It also logs validated JSON request bodies, successful JSON response data, and each SSE event name and data without buffering or replacing the stream. Each logged body/event payload is capped at 8 KiB; fields named `authorization`, `token`, `hf_token`, or `access_token` are redacted. Request and response payloads can still contain user messages and session drafts, so treat these logs as sensitive. `PLAYGROUND_DEBUG_CONNECTOR_LOGS` records provider requests, aggregated responses, and failures; connector payloads include prompts and user text. Authorization headers and the Hugging Face token are never logged. Provider failures include provider, model, exception type, and HTTP status when available; connector logs also add an HTTP error-body excerpt capped at 1,200 characters. `PLAYGROUND_DEBUG_INTERNAL_LOGS` records provider selection plus workflow progress, validation, and persistence outcomes without request content. The playground diagnostics panel reads a 500-entry process-local buffer through `GET /admin/diagnostics` and can clear it with `DELETE /admin/diagnostics`; these local admin endpoints have no authentication and are not suitable for network exposure.

## Database and service configuration

`DATABASE_URL` configures the API's PostgreSQL connection; Compose sets it to the `db` service. For direct local Uvicorn execution, the default URL is `postgresql://kairos:kairos-local@localhost:5432/kairos`. `API_PORT` and `POSTGRES_HOST_PORT` change the host ports. `MIGRATIONS_DIR` optionally overrides the backend's default migration directory. `.env.local` is ignored by Git and is used here for secrets such as `HF_TOKEN`.

The API has no authentication or session-retention policy and must not be exposed to the Internet. `docker compose down` stops the services but keeps the named volume and its sessions. `docker compose down -v` also deletes the local database volume, including saved drafts.
