# Local infrastructure setup

This guide starts the local HTTP API, PostgreSQL database, and optional Ollama connection with Docker Compose. This Compose configuration is for local development; a future deployment pipeline can build the backend image, but should use deployment-specific configuration and secrets. For API endpoints and requests, see [Start and use the module](module-guide.md).

## Start the API and PostgreSQL

From the repository root, build and start the services:

```bash
docker compose up --build
```

Compose binds the API to `127.0.0.1:8000` and PostgreSQL to `127.0.0.1:5432`. PostgreSQL data is stored in the `kairos-postgres` named volume. The API waits for the database health check and applies versioned SQL migrations from `backend/migrations/` at startup.

This command uses a deterministic demo provider unless Ollama variables are supplied through the shell or an automatically loaded `.env` file. The demo provider is useful for checking the HTTP flow but does not interpret arbitrary messages.

## Connect Ollama

To use an Ollama model available on the host, create a `.env.local` file in the repository root with these values:

```dotenv
KAIROS_OLLAMA_MODEL=qwen3:8b
KAIROS_OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Compose does not load `.env.local` automatically, so pass it explicitly when starting the services:

```bash
docker compose --env-file .env.local up --build
```

Compose passes these values to the API using the mappings in `compose.yaml`. The `.env.local` file is ignored by Git. `KAIROS_OLLAMA_MODEL` selects the model; leave it empty or unset to use the demo provider. `KAIROS_OLLAMA_BASE_URL` is optional and defaults to `http://host.docker.internal:11434` in Compose.

## Database and service configuration

`KAIROS_DATABASE_URL` configures the API's PostgreSQL connection; Compose sets it to the `db` service. For direct local Uvicorn execution, the default URL is `postgresql://kairos:kairos-local@localhost:5432/kairos`. `KAIROS_API_PORT` and `POSTGRES_HOST_PORT` change the host ports.

The API has no authentication or session-retention policy and must not be exposed to the Internet. `docker compose down` stops the services but keeps the named volume and its sessions. `docker compose down -v` also deletes the local database volume, including saved drafts.
