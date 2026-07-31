"""No-op web-search provider used when external search is disabled."""

from __future__ import annotations

from application.web_search.service import WebSearchResult


class DisabledWebSearchProvider:
    """Always returns an empty result set."""

    @property
    def provider_name(self) -> str:
        return "disabled"

    def search(self, query: str, *, max_results: int) -> tuple[WebSearchResult, ...]:
        return ()

    def probe(self) -> None:
        return None


__all__ = ["DisabledWebSearchProvider"]
