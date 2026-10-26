# Backend architecture and technology stack

The Python backend treats each user message as an opportunity to update any explicit event field, regardless of the previous assistant question. For free text, the model proposes one structured tool call and Python validates and applies it. Playground forms send typed actions that Python applies directly without a model request. Missing required details are shown separately from optional suggestions; neither prevents the user from providing different information on the next turn. The model does not save events, schedule notifications, or execute arbitrary external actions.

## Stack and module boundaries

| Component | Role |
| --- | --- |
| Python 3.13 | Backend runtime and workflow orchestration |
| Pydantic 2 | Validates request, stored state, tool arguments, and event data |
| FastAPI and Uvicorn | HTTP application and local ASGI server |
| httpx | Asynchronous HTTP client for Ollama and Hugging Face Inference Providers |
| PostgreSQL and Psycopg 3 | Stores session language, timezone, and current workflow state as JSONB |
| Provider profiles | Stores named demo, Ollama, and Hugging Face configurations and one active profile |
| Docker Compose | Runs the API and PostgreSQL on localhost with a persistent database volume |
| Ollama | Optional local model provider with tool calling and NDJSON streaming |
| Hugging Face Inference Providers | Optional hosted model provider through an OpenAI-compatible streaming chat endpoint |
| `uv` | Dependency and lockfile management |
| pytest | Backend test runner |

Important source files are under `backend/src/kairos/`: `models/event.py` contains event constraints; `contracts.py` defines shared workflow contracts; `workflow.py` controls each drafting turn; `tools.py` defines tool schemas and handlers; `providers/` contains the shared prompt and the Ollama, Hugging Face, and scripted adapters; `stores/` persists sessions and provider profiles; `api/` contains the FastAPI application, HTTP schemas, settings, and diagnostics; `__main__.py` provides the CLI; `i18n.py` and `locales/messages.json` define the supported languages and static messages. Versioned SQL migrations are under `backend/migrations/`.

## Workflow

```mermaid
flowchart LR
    A["Free-text message or typed form action"] --> B{"Input type"}
    B -->|Free text| C["Provider proposes one tool call"]
    C --> D["ToolRegistry validates and applies it"]
    B -->|Form action| E["Python applies the typed action"]
    D --> F["Return updated draft and guidance"]
    E --> F
    F --> G["Required fields and optional templates"]
```

Each free-text turn makes at most one model request and accepts exactly one permitted tool call. A structured playground action makes no model request. `EventWorkflow.stream_advance` emits progress before the request and before validation, optional generated text as it arrives, and `completed` only after the proposal has passed validation and been applied. `advance` consumes the same stream for callers that need only the final state. Progress and static errors follow the interface language; generated text and clarifications follow the conversation language.

The Ollama adapter reads streaming NDJSON through `done=true`. The Hugging Face adapter reads OpenAI-compatible SSE chunks through `[DONE]`. Both keep streamed text separate from tool calls and buffer partial tool-call arguments until the stream finishes, so partial JSON is never executed or shown as the draft. Reasoning (`thinking`) is not exposed. Streamed text is provisional: a late error can follow text already displayed, while the state remains unchanged. Hugging Face provider/model combinations do not all support tool calling and streaming, so profiles must use a compatible combination.

## Tool validation and draft state

`ToolRegistry.schemas(state)` exposes the available schemas. For this event workflow the model can call `update_event_draft` or `ask_event_clarification`. Pydantic rejects undeclared fields (`extra="forbid"`), invalid values, and malformed tool arguments. Python applies accepted changes to a copy of the draft; a failed request leaves the previous state unchanged.

The main event action belongs in the title. Separate before/after activities use `task_operations.add`; each addition includes a quote from the current message, and Python accepts it only when that quote is present and contains a supported before/after marker. Unsupported activity proposals are ignored and cannot block other extracted fields. For removal, the model reports intent and quotes the request but does not choose a target. Each activity has a stable ID. Python removes a uniquely named activity or the only activity; when several remain and the message does not identify one exactly, the state holds the candidate IDs and offers choices. The user can provide other event details while that choice is pending; a numbered choice or playground button resolves it locally without another model call. Legacy full-list task updates are rejected by the patch schema.

A reminder is distinct from an activity. `reminders=null` means the user has not chosen yet, while `[]` means no reminders. Reminders are optional and are not a blocking question. The prompt interprets numeric intervals as reminder offsets, and Python independently converts clear forms such as `2 hours before` to minutes. Structured playground actions can update fields, add an explicitly described before/after activity, or configure reminders without a model call. An offset that would already be in the past is rejected. These checks do not send or schedule notifications. Locations are formatted conservatively for readability (spacing, separators, and capitalization) without geocoding or changing address details.

Date, local time, and IANA timezone are separate values. Missing time is not represented as midnight. Nonexistent or ambiguous local times, inconsistent UTC offsets, and dates that cannot be resolved safely require clarification. Relative dates use the request context's server-side `now` and timezone.

## HTTP, sessions, and streaming

`api/app.py` exposes `GET /health`, `POST /sessions`, `GET /sessions/{id}`, and `POST /sessions/{id}/turn`. The turn request accepts either `message` or a typed `action`. Its HTTP contracts live in `api/schemas.py`, runtime settings in `api/settings.py`, and structured diagnostic buffer in `api/diagnostics.py`. Session creation stores a UUID, interface language, IANA timezone, initial `EventWorkflowState` JSONB, and database timestamps. Each turn loads the latest state by session ID; the client no longer sends the state. Session responses include derived guidance: missing required fields and localized templates for title, date, time, location, duration, before/after activities, and reminders. Guidance is computed from the current draft and is not duplicated in the database. No conversation transcript is stored or sent to the model: the provider receives only the current message, current draft, and previous question as context.

The turn endpoint translates workflow events into SSE names `progress`, optional `text`, `completed`, and `error`. A `completed` event is sent only after the new `EventWorkflowState` has been committed to PostgreSQL. Updates use the previously read `updated_at` as an optimistic concurrency check, so overlapping turns cannot silently overwrite each other's state. Shared `httpx.AsyncClient` instances and a Psycopg async connection pool are created in the FastAPI lifespan and closed at shutdown. The SQL migration runner applies checked-in migrations at startup.

Migration `002_create_provider_profiles.sql` inserts three built-in provider profiles: active Demo, inactive local Ollama (`qwen3:8b` at `http://host.docker.internal:11434`), and inactive Hugging Face (`Qwen/Qwen3-8B`). A partial unique index allows at most one profile to be active. The API does not create profiles at startup; its admin interface only lists and activates these choices. Every API turn reads the active row, so switching the profile affects the next turn without restarting the service. Hugging Face uses the managed Inference Providers router and reads its credential from `HF_TOKEN`; secrets are not stored in PostgreSQL. Its streaming adapter assembles text and tool-call fragments before the workflow validates the single call.

The local-only administrative endpoints are `GET /admin/provider-profiles` and `POST /admin/provider-profiles/{profile_id}/activate`. They have no authentication and are safe only while the API remains bound to localhost. `HF_TOKEN` authenticates Hugging Face requests. The CLI still selects Ollama directly through its CLI argument and does not use the database profiles.

Three independent settings default to false in `APISettings`. The local Compose configuration currently enables all three for the playground. `PLAYGROUND_DEBUG_API_LOGS` emits structured HTTP metadata, bounded request/response payloads, SSE event names/data, and terminal outcomes with a shared request ID; successful health checks stay silent and Uvicorn access logs are disabled. Payloads are capped at 8 KiB and common credential fields are redacted, but request/response data can contain user messages and session drafts. `PLAYGROUND_DEBUG_CONNECTOR_LOGS` emits provider requests, aggregated responses, and failure details including status and a bounded HTTP body excerpt. Connector payloads may contain the system prompt and user text; Authorization headers and provider tokens are excluded. `PLAYGROUND_DEBUG_INTERNAL_LOGS` records provider choice, workflow progress, validation, and persistence outcomes without request content. Each setting controls only its own category.

The same FastAPI app serves a static developer playground at `/`. It calls the session, typed-action, SSE, and provider-profile APIs from the same origin. Contextual choices in the conversation open one structured widget at a time; the side panel summarizes the validated draft. These actions update the session without a model call, and free text remains available while a widget is open. Duration and reminder widgets share localized minute, hour, and day units from the guidance response; the browser converts the selected amount to minutes before submitting the action. The `/admin/diagnostics` GET/DELETE endpoints expose or clear a bounded 500-entry in-memory ring of structured records; they do not persist across process restarts. These unauthenticated pages and endpoints are for localhost development only. The Docker image copies the static files under `/app/static`.

`DATABASE_URL` configures the PostgreSQL connection; its local default is `postgresql://kairos:kairos-local@localhost:5432/kairos`. Docker Compose uses the database service hostname and a named volume. Both API and database ports bind to localhost. The prototype has no authentication or retention policy and is not ready for Internet exposure; retention and account-level authorization remain out of scope.

## Language behavior

`Language` declares Italian and English. The static message catalog has a complete entry for each language and is validated at startup. The interface language (`RequestContext.language`) is separate from the conversation language (`EventWorkflowState.conversation_language`). The model may propose the conversation language in the same tool call; Python validates and carries it across turns. Neutral or short replies preserve the prior choice. For a substantive message in an unsupported language, the prompt asks the model to use English. This behavior is covered by simulated responses, but a limited real-model evaluation found non-conforming language choices for the tested Qwen configuration; see [prompt evaluation](prompt-evaluation.md).

## Prompt evaluation

The runtime uses the baseline prompt. A single local comparison against a compact candidate found small measured input-token savings but semantic and language regressions. The candidate was not promoted. The [evaluation note](prompt-evaluation.md) and [raw report](../../backend/evals/results/qwen3-8b-prompt-comparison.md) describe the limited sample and its constraints; the results do not establish general model quality or latency.

## Current boundaries

The backend prepares drafts only. It persists the current session state, but not a chat transcript. It has no authentication, calendar integration, notification delivery, voice input, or mobile UI. The API and CLI are local prototype interfaces bound to localhost by the Compose configuration; the API is not ready for Internet exposure. There is no retention policy yet. Model output remains a proposal that must pass deterministic validation and user review before any future external action.
