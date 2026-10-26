# Backend architecture and technology stack

The Python backend turns one user message into a validated event-draft update. The model proposes one structured tool call; Python validates it, applies it to a copy of the current state, and decides whether to ask the next required question. The model does not save events, schedule notifications, or execute arbitrary external actions.

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

Important source files are under `backend/src/kairos/`: `models/event.py` contains event constraints; `contracts.py` defines shared workflow contracts; `workflow.py` controls each drafting turn; `tools.py` defines tool schemas and handlers; `providers.py` contains the prompt and model adapters; `provider_store.py` persists provider profiles; `api.py` adapts sessions and workflow events to HTTP/SSE; `session_store.py` persists session records; `__main__.py` provides the CLI; `i18n.py` and `locales/messages.json` define the supported languages and static messages. Versioned SQL migrations are under `backend/migrations/`.

## Workflow

```mermaid
flowchart LR
    A["Client message and current draft"] --> B["EventWorkflow"]
    B --> C["Provider proposes one tool call"]
    C --> D["ToolRegistry validates and applies it"]
    D --> E{"Required details complete?"}
    E -->|No| F["Return a focused question and updated draft"]
    E -->|Yes| G["Return a draft ready for review"]
```

Each turn makes at most one model request and accepts exactly one permitted tool call. `EventWorkflow.stream_advance` emits progress before the request and before validation, optional generated text as it arrives, and `completed` only after the proposal has passed validation and been applied. `advance` consumes the same stream for callers that need only the final state. Progress and static errors follow the interface language; generated text and clarifications follow the conversation language.

The Ollama adapter reads streaming NDJSON through `done=true`. The Hugging Face adapter reads OpenAI-compatible SSE chunks through `[DONE]`. Both keep streamed text separate from tool calls and buffer partial tool-call arguments until the stream finishes, so partial JSON is never executed or shown as the draft. Reasoning (`thinking`) is not exposed. Streamed text is provisional: a late error can follow text already displayed, while the state remains unchanged. Hugging Face provider/model combinations do not all support tool calling and streaming, so profiles must use a compatible combination.

## Tool validation and draft state

`ToolRegistry.schemas(state)` exposes the available schemas. For this event workflow the model can call `update_event_draft` or `ask_event_clarification`. Pydantic rejects undeclared fields (`extra="forbid"`), invalid values, and malformed tool arguments. Python applies accepted changes to a copy of the draft; a failed request leaves the previous state unchanged.

The main event action belongs in the title. Separate before/after activities are represented using `task_operations.add` and `.remove`; removal succeeds only for a unique matching description. A reminder is distinct from an activity. `reminders=null` means the user has not chosen yet, while `[]` means no reminders. When answering a reminder question, the backend restricts the update to reminders; a clock time such as 11:00 is converted to an offset before the event when it can be resolved safely. An offset that would already be in the past is rejected. These checks do not send or schedule notifications.

Date, local time, and IANA timezone are separate values. Missing time is not represented as midnight. Nonexistent or ambiguous local times, inconsistent UTC offsets, and dates that cannot be resolved safely require clarification. Relative dates use the request context's server-side `now` and timezone.

## HTTP, sessions, and streaming

`api.py` exposes `GET /health`, `POST /sessions`, `GET /sessions/{id}`, and `POST /sessions/{id}/turn`. Session creation stores a UUID, interface language, IANA timezone, initial `EventWorkflowState` JSONB, and database timestamps. Each turn loads the latest state by session ID; the client no longer sends the state. No conversation transcript is stored or sent to the model: the provider receives only the current message, current draft, and existing previous question.

The turn endpoint translates workflow events into SSE names `progress`, optional `text`, `completed`, and `error`. A `completed` event is sent only after the new `EventWorkflowState` has been committed to PostgreSQL. Updates use the previously read `updated_at` as an optimistic concurrency check, so overlapping turns cannot silently overwrite each other's state. Shared `httpx.AsyncClient` instances and a Psycopg async connection pool are created in the FastAPI lifespan and closed at shutdown. The SQL migration runner applies checked-in migrations at startup.

Migration `002_create_provider_profiles.sql` inserts three built-in provider profiles: active Demo, inactive local Ollama (`qwen3:8b` at `http://host.docker.internal:11434`), and inactive Hugging Face (`Qwen/Qwen3-8B`). A partial unique index allows at most one profile to be active. The API does not create profiles at startup; its admin interface only lists and activates these choices. Every API turn reads the active row, so switching the profile affects the next turn without restarting the service. Hugging Face uses the managed Inference Providers router and reads its credential from `HF_TOKEN`; secrets are not stored in PostgreSQL. Its streaming adapter assembles text and tool-call fragments before the workflow validates the single call.

The local-only administrative endpoints are `GET /admin/provider-profiles` and `POST /admin/provider-profiles/{profile_id}/activate`. They have no authentication and are safe only while the API remains bound to localhost. `HF_TOKEN` authenticates Hugging Face requests. The CLI still selects Ollama directly through its CLI argument and does not use the database profiles.

`DATABASE_URL` configures the PostgreSQL connection; its local default is `postgresql://kairos:kairos-local@localhost:5432/kairos`. Docker Compose uses the database service hostname and a named volume. Both API and database ports bind to localhost. The prototype has no authentication or retention policy and is not ready for Internet exposure; retention and account-level authorization remain out of scope.

## Language behavior

`Language` declares Italian and English. The static message catalog has a complete entry for each language and is validated at startup. The interface language (`RequestContext.language`) is separate from the conversation language (`EventWorkflowState.conversation_language`). The model may propose the conversation language in the same tool call; Python validates and carries it across turns. Neutral or short replies preserve the prior choice. For a substantive message in an unsupported language, the prompt asks the model to use English. This behavior is covered by simulated responses, but a limited real-model evaluation found non-conforming language choices for the tested Qwen configuration; see [prompt evaluation](prompt-evaluation.md).

## Prompt evaluation

The runtime uses the baseline prompt. A single local comparison against a compact candidate found small measured input-token savings but semantic and language regressions. The candidate was not promoted. The [evaluation note](prompt-evaluation.md) and [raw report](../../backend/evals/results/qwen3-8b-prompt-comparison.md) describe the limited sample and its constraints; the results do not establish general model quality or latency.

## Current boundaries

The backend prepares drafts only. It persists the current session state, but not a chat transcript. It has no authentication, calendar integration, notification delivery, voice input, or mobile UI. The API and CLI are local prototype interfaces bound to localhost by the Compose configuration; the API is not ready for Internet exposure. There is no retention policy yet. Model output remains a proposal that must pass deterministic validation and user review before any future external action.
