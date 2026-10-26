# Local infrastructure setup

This guide starts the local HTTP API and PostgreSQL database with Docker Compose. This Compose configuration is for local development; a future deployment pipeline can build the backend image, but should use deployment-specific configuration and secrets. For API endpoints and model profiles, see [Start and use the module](module-guide.md).

## Start the API and PostgreSQL

From the repository root, build and start the services:

```bash
docker compose up --build
```

Compose binds the API to `127.0.0.1:8000` and PostgreSQL to `127.0.0.1:5432`. PostgreSQL data is stored in the `kairos-postgres` named volume. The API waits for the database health check and applies versioned SQL migrations from `backend/migrations/` at startup.

The provider-profile migration installs three built-in choices: the active deterministic Demo profile, local Ollama (`qwen3:8b` at `http://host.docker.internal:11434`), and Hugging Face (`Qwen/Qwen3-8B`). Demo checks the HTTP flow but does not interpret arbitrary messages. The profiles and current selection are stored in PostgreSQL and persist across container restarts. Select one through the local admin API described in the [module guide](module-guide.md).

## Connect Hugging Face Inference Providers

Create a fine-grained Hugging Face access token with the **Make calls to Inference Providers** permission. Add it to the root `.env.local` file; do not commit or paste the real value into documentation:

```dotenv
HF_TOKEN=hf_your_token
```

Compose does not load `.env.local` automatically, so start or recreate the API with that file:

```bash
docker compose --env-file .env.local up --build
```

Compose passes `HF_TOKEN` to the API container. Kairos does not store it in PostgreSQL. After startup, list profiles and activate the built-in Hugging Face profile using its returned ID. Its bare model ID is routed automatically through Hugging Face Inference Providers. See the module guide for the activation request.

The admin endpoints have no authentication and must only be used with the local API bound to localhost. Switching the active profile affects the next API turn; it does not require a container restart. HF usage and credits are managed separately in your Hugging Face account.

## Database and service configuration

`DATABASE_URL` configures the API's PostgreSQL connection; Compose sets it to the `db` service. For direct local Uvicorn execution, the default URL is `postgresql://kairos:kairos-local@localhost:5432/kairos`. `API_PORT` and `POSTGRES_HOST_PORT` change the host ports. `MIGRATIONS_DIR` optionally overrides the backend's default migration directory. `.env.local` is ignored by Git and is used here for secrets such as `HF_TOKEN`.

The API has no authentication or session-retention policy and must not be exposed to the Internet. `docker compose down` stops the services but keeps the named volume and its sessions. `docker compose down -v` also deletes the local database volume, including saved drafts.
