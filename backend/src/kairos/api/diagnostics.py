"""Structured API and workflow diagnostics buffered in process memory."""

import json
import sys
from collections import deque
from datetime import UTC, datetime
from threading import Lock

from fastapi import Request


MAX_API_LOG_BYTES = 8 * 1024
MAX_DIAGNOSTIC_ENTRIES = 500
MAX_DIAGNOSTIC_ENTRY_FIELD_BYTES = 16 * 1024
SENSITIVE_LOG_KEYS = {"authorization", "token", "hf_token", "access_token"}
DIAGNOSTIC_LOGS: deque[dict] = deque(maxlen=MAX_DIAGNOSTIC_ENTRIES)
DIAGNOSTIC_LOGS_LOCK = Lock()


def _emit_log(event: str, **fields: object) -> None:
    """Write one structured JSON record to container stdout."""
    record = {
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "event": event,
        **fields,
    }
    sanitized = _sanitize_log_data(record)
    buffered = dict(sanitized)
    for key in ("data", "body", "response_body_excerpt"):
        if key in buffered:
            max_bytes = 1_200 if key == "response_body_excerpt" else MAX_DIAGNOSTIC_ENTRY_FIELD_BYTES
            buffered[key] = _bounded_log_data(buffered[key], max_bytes=max_bytes)
    with DIAGNOSTIC_LOGS_LOCK:
        DIAGNOSTIC_LOGS.append(buffered)
    print(json.dumps(sanitized, ensure_ascii=False, default=str), file=sys.stdout, flush=True)


def _sanitize_log_data(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if str(key).lower() in SENSITIVE_LOG_KEYS else _sanitize_log_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_log_data(item) for item in value]
    return value


def _bounded_log_data(value: object, *, max_bytes: int = MAX_API_LOG_BYTES) -> object:
    sanitized = _sanitize_log_data(value)
    encoded = json.dumps(sanitized, ensure_ascii=False, default=str).encode("utf-8")
    if len(encoded) <= max_bytes:
        return sanitized
    return {
        "truncated": True,
        "max_bytes": max_bytes,
        "preview": encoded[:max_bytes].decode("utf-8", errors="ignore"),
    }


def _record_api_request_data(request: Request, data: object) -> None:
    if request.app.state.configuration.debug_api_logs:
        request.state.api_request_data = _bounded_log_data(data)


def _log_api_response_data(request: Request, data: object) -> None:
    if request.app.state.configuration.debug_api_logs:
        _emit_log(
            "api.response_data",
            request_id=request.state.request_id,
            data=_bounded_log_data(data),
        )




def read_diagnostics(request_id: str | None = None) -> dict[str, object]:
    with DIAGNOSTIC_LOGS_LOCK:
        entries = list(DIAGNOSTIC_LOGS)
    if request_id:
        entries = [entry for entry in entries if entry.get("request_id") == request_id]
    return {"items": list(reversed(entries)), "capacity": MAX_DIAGNOSTIC_ENTRIES}


def clear_diagnostics() -> dict[str, int]:
    with DIAGNOSTIC_LOGS_LOCK:
        cleared = len(DIAGNOSTIC_LOGS)
        DIAGNOSTIC_LOGS.clear()
    return {"cleared": cleared}
