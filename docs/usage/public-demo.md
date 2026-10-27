# Public playground demo

The GitHub Pages demo runs the same Python workflow, Pydantic validation, structured actions, draft guidance, translations, and frontend components as the local playground. Pyodide runs Python in a dedicated browser worker. All runtime packages are pinned, downloaded during the build, and served with the site. No model endpoint, API key, PostgreSQL connection, or private API is used.

The demo displays only session creation, chat, and the current draft. Provider controls, diagnostics, and response-event tools are excluded from the published HTML. Their real HTTP adapter is also excluded from the artifact.

## Try the demo

Create a session, then select one of the guided conversations: the mechanic, dinner, or studying Python. Each conversation proposes the next example message. Structured controls accept your own field values and use the real Python workflow to validate them. Unsupported free text receives an explanation rather than fabricated event data.

Responses and the short progress delay are explicitly simulated. Session data stays in memory in the current browser tab and is cleared when the page is reloaded or a new session is created. Italian and English examples are available.

Change Italian or English from the flag selector in the navigation bar. It updates the interface, active session language, and guided examples without discarding the draft. Choose a timezone from the session menu; options are ordered by current UTC offset, then by name, and include daylight-saving offsets.

The first load downloads the browser Python runtime and takes longer than subsequent visits. Browser caching can reuse these assets. If initialization fails, reload the page to retry.

## Build and preview locally

From the repository root:

```bash
python3 scripts/build_pages_demo.py
node scripts/check_pages_demo.mjs
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist/pages
```

Open `http://127.0.0.1:8080/`. Building requires internet access to download the pinned Pyodide runtime; the generated site is self-contained. The source tree is explicitly allowlisted, so local environment files, SQL migrations, real provider adapters, and logs cannot enter the Pages artifact.

## Publish

GitHub Pages must use **GitHub Actions** as its publishing source. The `Publish playground demo` workflow builds and validates the browser runtime, then publishes `dist/pages` whenever relevant code is pushed to `main`. It can also be started manually. No Hugging Face secret is required in GitHub Actions.

HTML, CSS, images, and UI modules have one source under `backend/src/kairos/static/`. The build changes the generated configuration to demo mode and removes local-only controls. It does not maintain a separate copy of the interface.

## Real playground

The real playground remains served by FastAPI on localhost. Its provider controls are inside the chat card; diagnostics and response events are grouped below the workspace. PostgreSQL profiles contain only Ollama and Hugging Face. Migration `003_remove_demo_provider.sql` removes the historical demo entry, preserves an active real provider, and selects Ollama if no real provider is active. Restart the API to apply pending migrations.
