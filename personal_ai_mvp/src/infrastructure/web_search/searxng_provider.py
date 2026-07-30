"""SearxNG-backed provider for external web grounding."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from application.web_search.service import WebSearchResult


class SearxngWebSearchProvider:
    """Query a configured SearxNG instance and normalize its response."""

    def __init__(self, *, base_url: str, timeout_seconds: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "searxng"

    def search(self, query: str, *, max_results: int) -> tuple[WebSearchResult, ...]:
        params = urlencode(
            {
                "q": query,
                "format": "json",
                "safesearch": 0,
            }
        )
        request = Request(
            f"{self._base_url}/search?{params}",
            headers={"Accept": "application/json", "User-Agent": "PersonalAI/1.0"},
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"SearxNG request failed with HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError("Failed to reach SearxNG during web search execution.") from exc
        except TimeoutError as exc:
            raise RuntimeError("SearxNG web search timed out.") from exc

        results = payload.get("results", ())
        normalized: list[WebSearchResult] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            title = str(item.get("title", "")).strip()
            if not url or not title:
                continue
            normalized.append(
                WebSearchResult(
                    title=title,
                    url=url,
                    snippet=str(item.get("content", "")).strip(),
                    source=str(item.get("engine", "")).strip(),
                )
            )
            if len(normalized) >= max_results:
                break

        return tuple(normalized)


__all__ = ["SearxngWebSearchProvider"]
