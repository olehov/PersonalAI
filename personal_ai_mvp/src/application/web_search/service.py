"""Application service for controlled external web search grounding."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit


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
    original_query: str = ""
    query_truncated: bool = False
    requested_max_results: int = 0
    applied_max_results: int = 0
    raw_result_count: int = 0
    filtered_result_count: int = 0
    invalid_result_count: int = 0
    blocked_result_count: int = 0
    allowlist_filtered_count: int = 0


class WebSearchService:
    """Small facade over a pluggable web-search provider."""

    def __init__(
        self,
        provider,
        *,
        enabled: bool,
        default_max_results: int,
        max_query_chars: int = 400,
        allowed_domains: tuple[str, ...] = (),
        blocked_domains: tuple[str, ...] = (),
    ) -> None:
        self._provider = provider
        self._enabled = enabled
        self._default_max_results = max(1, default_max_results)
        self._max_query_chars = max(1, max_query_chars)
        self._allowed_domains = self._normalize_domains(allowed_domains)
        self._blocked_domains = self._normalize_domains(blocked_domains)

    def search(self, query: str, *, max_results: int | None = None) -> WebSearchResponse:
        """Run a controlled web search and normalize the result set."""
        normalized_query, query_truncated = self._normalize_query(query)
        requested_limit = max(1, max_results or self._default_max_results)
        if not self._enabled or not normalized_query:
            return WebSearchResponse(
                query=normalized_query,
                provider=self.provider_name,
                results=(),
                enabled=self._enabled,
                original_query=query,
                query_truncated=query_truncated,
                requested_max_results=requested_limit,
                applied_max_results=0 if not self._enabled else self._resolve_limit(max_results),
            )

        limit = self._resolve_limit(max_results)
        raw_results = self._provider.search(normalized_query, max_results=limit)
        invalid_result_count = 0
        blocked_result_count = 0
        allowlist_filtered_count = 0
        accepted_results: list[WebSearchResult] = []
        for result in raw_results:
            allowed, reason = self._classify_result(result.url)
            if allowed:
                accepted_results.append(result)
                continue
            if reason == "blocked":
                blocked_result_count += 1
            elif reason == "allowlist":
                allowlist_filtered_count += 1
            else:
                invalid_result_count += 1
        filtered_results = tuple(accepted_results[:limit])
        return WebSearchResponse(
            query=normalized_query,
            provider=self.provider_name,
            results=filtered_results,
            enabled=self._enabled,
            original_query=query,
            query_truncated=query_truncated,
            requested_max_results=requested_limit,
            applied_max_results=limit,
            raw_result_count=len(raw_results),
            filtered_result_count=len(raw_results) - len(filtered_results),
            invalid_result_count=invalid_result_count,
            blocked_result_count=blocked_result_count,
            allowlist_filtered_count=allowlist_filtered_count,
        )

    @property
    def provider_name(self) -> str:
        """Expose the underlying provider name for diagnostics."""
        return str(self._provider.provider_name)

    @property
    def enabled(self) -> bool:
        """Expose whether web search is enabled at all."""
        return self._enabled

    def _classify_result(self, url: str) -> tuple[bool, str | None]:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").casefold()
        scheme = parsed.scheme.casefold()
        if not hostname or scheme not in {"http", "https"}:
            return False, "invalid"
        if self._matches_domains(hostname, self._blocked_domains):
            return False, "blocked"
        if not self._allowed_domains:
            return True, None
        if self._matches_domains(hostname, self._allowed_domains):
            return True, None
        return False, "allowlist"

    def _resolve_limit(self, max_results: int | None) -> int:
        if max_results is None:
            return self._default_max_results
        requested = max(1, max_results)
        return min(requested, self._default_max_results)

    def _normalize_query(self, query: str) -> tuple[str, bool]:
        collapsed = " ".join(query.split())
        truncated = len(collapsed) > self._max_query_chars
        return collapsed[: self._max_query_chars].strip(), truncated

    @staticmethod
    def _normalize_domains(domains: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(domain.casefold() for domain in domains if domain.strip())

    @staticmethod
    def _matches_domains(hostname: str, domains: tuple[str, ...]) -> bool:
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in domains
        )


__all__ = [
    "WebSearchResponse",
    "WebSearchResult",
    "WebSearchService",
]
