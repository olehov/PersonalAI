"""HTTP handler and static-serving helpers for the PersonalAI web UI."""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from infrastructure.config.settings import get_settings
from web_app.api_routes import handle_api_request as _handle_api_request
from web_app.app import PersonalAIWebApp


def make_handler(app: PersonalAIWebApp):
    """Create a request handler bound to the app instance."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/api/"):
                status_code, payload = handle_api_request(
                    app,
                    method="GET",
                    path=self.path,
                    body=None,
                )
                self._send_json(payload, status_code=status_code)
                return
            self._send_frontend()

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            if self.path.startswith("/api/"):
                status_code, payload = handle_api_request(
                    app,
                    method="POST",
                    path=self.path,
                    body=body,
                )
                self._send_json(payload, status_code=status_code)
                return
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Use the JSON API for mutations.")

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _send_json(self, payload: dict[str, object] | list[object], *, status_code: int) -> None:
            encoded = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_frontend(self) -> None:
            if not app.has_frontend_assets():
                self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                message = (
                    "Frontend build not found. Run `npm run build` inside "
                    "`H:/Projects/PersonalAI/personal_ai_mvp/frontend`."
                )
                encoded = message.encode("utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return

            requested_path = app.resolve_frontend_asset(self.path)
            is_existing_asset = requested_path.exists() and requested_path.is_file()
            response_path = requested_path if is_existing_asset else app.frontend_index_path()
            content_type = mimetypes.guess_type(response_path.name)[0] or "application/octet-stream"
            if response_path.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            encoded = response_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return Handler


def handle_api_request(
    app: PersonalAIWebApp,
    *,
    method: str,
    path: str,
    body: str | None,
) -> tuple[int, dict[str, object] | list[object]]:
    """Handle JSON API requests for the future JS frontend."""
    return _handle_api_request(
        app,
        method=method,
        path=path,
        body=body,
        default_ui_model=get_settings().default_model,
        debug_api_errors=get_settings().debug_api_errors,
    )
