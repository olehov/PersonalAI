"""Protocol for pluggable web-search backends."""

from __future__ import annotations

from typing import Protocol

from application.web_search.service import WebSearchResult


class WebSearchProvider(Protocol):
    """Duck-typed contract for external search backends."""

    @property
    def provider_name(self) -> str:
        """Return the provider identifier used for diagnostics."""

    def search(self, query: str, *, max_results: int) -> tuple[WebSearchResult, ...]:
        """Execute a web search and return normalized result objects."""


__all__ = ["WebSearchProvider"]
