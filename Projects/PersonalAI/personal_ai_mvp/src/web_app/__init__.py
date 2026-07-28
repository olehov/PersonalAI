"""Web application package for PersonalAI."""

from web_app.api_helpers import (
    normalize_reasoning_mode,
    parse_conversation_history,
    parse_scope_dirs,
    serialize_route_decision,
)
from web_app.api_routes import handle_api_request
from web_app.app import (
    DEFAULT_UI_MODEL,
    PersonalAIWebApp,
)
from web_app.cli import (
    build_parser,
    main,
)
from web_app.http import (
    make_handler,
)

__all__ = [
    "DEFAULT_UI_MODEL",
    "PersonalAIWebApp",
    "build_parser",
    "handle_api_request",
    "main",
    "make_handler",
    "normalize_reasoning_mode",
    "parse_conversation_history",
    "parse_scope_dirs",
    "serialize_route_decision",
]
