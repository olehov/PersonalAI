"""Infrastructure web-search providers and factories."""

from infrastructure.web_search.disabled_provider import DisabledWebSearchProvider
from infrastructure.web_search.factory import build_web_search_service
from infrastructure.web_search.provider import WebSearchProvider
from infrastructure.web_search.searxng_provider import SearxngWebSearchProvider

__all__ = [
    "build_web_search_service",
    "DisabledWebSearchProvider",
    "SearxngWebSearchProvider",
    "WebSearchProvider",
]
