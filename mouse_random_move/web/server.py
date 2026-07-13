from __future__ import annotations

import json
import mimetypes
import threading
from collections import Counter, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class BrowserEvent:
    sequence: int
    event_type: str
    received_at: str
    details: dict[str, Any]


class BrowserEventStore:
    def __init__(self) -> None:
        self._events: deque[BrowserEvent] = deque(maxlen=500)
        self._counts: Counter[str] = Counter()
        self._sequence = 0
        self._active = False
        self._lock = threading.Lock()

    def set_active(self, active: bool) -> None:
        with self._lock:
            self._active = active

    def add(self, event_type: str, details: dict[str, Any]) -> BrowserEvent | None:
        with self._lock:
            if not self._active and event_type != "page_ready":
                return None
            self._sequence += 1
            event = BrowserEvent(
                sequence=self._sequence,
                event_type=event_type,
                received_at=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                details=details,
            )
            self._events.append(event)
            self._counts[event_type] += 1
            return event

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            last = asdict(self._events[-1]) if self._events else None
            return {
                "active": self._active,
                "sequence": self._sequence,
                "counts": dict(self._counts),
                "last_event": last,
            }

    def has_event_after(self, event_type: str, sequence: int) -> bool:
        with self._lock:
            return any(
                event.sequence > sequence and event.event_type == event_type
                for event in self._events
            )

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._counts.clear()
            self._sequence = 0


class TestPageServer:
    def __init__(self, frontend_root: Path) -> None:
        self.frontend_root = frontend_root.resolve()
        self.store = BrowserEventStore()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        if self._server is None:
            raise RuntimeError("Server is not running.")
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/"

    def start(self) -> None:
        if self._server is not None:
            return

        store = self.store
        frontend_root = self.frontend_root

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/api/status":
                    self._send_json(HTTPStatus.OK, store.snapshot())
                    return

                relative = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
                requested = (frontend_root / relative).resolve()
                try:
                    requested.relative_to(frontend_root)
                except ValueError:
                    self.send_error(HTTPStatus.FORBIDDEN)
                    return

                if not requested.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return

                content = requested.read_bytes()
                mime_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(content)

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/api/reset":
                    store.reset()
                    self._send_json(HTTPStatus.OK, {"ok": True})
                    return
                if parsed.path != "/api/event":
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return

                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 64_000:
                        raise ValueError("Invalid body size")
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    event_type = str(payload.get("type", "unknown"))[:64]
                    details = payload.get("details", {})
                    if not isinstance(details, dict):
                        details = {"value": details}
                    event = store.add(event_type, details)
                    self._send_json(
                        HTTPStatus.OK,
                        {"ok": True, "ignored": event is None, "sequence": event.sequence if event else None},
                    )
                except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False})

            def log_message(self, _format: str, *_args: object) -> None:
                return

            def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
                content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(content)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="mouse-random-move-test-page",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
