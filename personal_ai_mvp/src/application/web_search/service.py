"""Application service for controlled external web search grounding."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    """One normalized web-search hit returned by a provider."""

    title: str
    url: str
    snippet: str = ""
    source: str = ""


@dataclass(frozen=True, slots=True)
class WebSearchResponse:
    """Normalized web-search response plus execution metadata."""

    query: str
    provider: str
    results: tuple[WebSearchResult, ...] = field(default_factory=tuple)
    enabled: bool = False


class WebSearchService:
    """Small facade over a pluggable web-search provider."""

    def __init__(
        self,
        provider,
        *,
        enabled: bool,
        default_max_results: int,
        allowed_domains: tuple[str, ...] = (),
    ) -> None:
        self._provider = provider
        self._enabled = enabled
        self._default_max_results = max(1, default_max_results)
        self._allowed_domains = tuple(domain.casefold() for domain in allowed_domains if domain.strip())

    def search(self, query: str, *, max_results: int | None = None) -> WebSearchResponse:
        """Run a controlled web search and normalize the result set."""
        normalized_query = query.strip()
        if not normalized_query:
            return WebSearchResponse(
                query="",
                provider=self.provider_name,
                results=(),
                enabled=self._enabled,
            )

        limit = max(1, max_results or self._default_max_results)
        raw_results = self._provider.search(normalized_query, max_results=limit)
        filtered_results = tuple(
            result
            for result in raw_results
            if self._allow_result(result.url)
        )[:limit]
        return WebSearchResponse(
            query=normalized_query,
            provider=self.provider_name,
            results=filtered_results,
            enabled=self._enabled,
        )

    @property
    def provider_name(self) -> str:
        """Expose the underlying provider name for diagnostics."""
        return str(self._provider.provider_name)

    @property
    def enabled(self) -> bool:
        """Expose whether web search is enabled at all."""
        return self._enabled

    def _allow_result(self, url: str) -> bool:
        if not self._allowed_domains:
            return True
        lower_url = url.casefold()
        return any(domain in lower_url for domain in self._allowed_domains)


__all__ = [
    "WebSearchResponse",
    "WebSearchResult",
    "WebSearchService",
]
