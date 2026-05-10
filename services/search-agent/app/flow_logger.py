from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


def log_flow(service: str, step: str, message: str, **context: Any) -> None:
    path = os.environ.get("FLOW_LOG_PATH")
    timestamp = datetime.now(timezone.utc).isoformat()
    sanitized_context = _sanitize(context)
    payload = {
        "timestamp": timestamp,
        "service": service,
        "step": step,
        "message": message,
        "context": sanitized_context if isinstance(sanitized_context, dict) else {},
    }

    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
        try:
            os.chmod(target, 0o666)
        except OSError:
            pass

        line = " | ".join(
            [
                timestamp,
                service,
                step,
                message,
            ]
        )

        if context:
            line += " | " + json.dumps(sanitized_context, ensure_ascii=True, sort_keys=True)

        with target.open("a", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.write(line + "\n")
            handle.flush()
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    _push_event(payload)


def _sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= 240 else value[:237] + "..."
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize(item) for item in value)
    return value


def _push_event(payload: dict[str, Any]) -> None:
    url = os.environ.get("FLOW_EVENT_PUSH_URL")
    if not url:
        return

    request = urllib_request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    token = os.environ.get("FLOW_EVENT_TOKEN")
    if token:
        request.add_header("X-Flow-Event-Token", token)

    try:
        with urllib_request.urlopen(request, timeout=0.5) as response:
            response.read()
    except (urllib_error.URLError, TimeoutError, OSError):
        return
