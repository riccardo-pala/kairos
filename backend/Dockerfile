FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY migrations/ ./migrations/
RUN uv sync --locked --no-dev --no-editable

FROM python:3.13-slim AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN groupadd --system --gid 10001 kairos \
    && useradd --system --uid 10001 --gid kairos --home-dir /app kairos
COPY --from=builder --chown=kairos:kairos /app/.venv /app/.venv
COPY --from=builder --chown=kairos:kairos /app/migrations /app/migrations

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "kairos.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
