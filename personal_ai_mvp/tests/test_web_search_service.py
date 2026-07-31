from __future__ import annotations

import os
import unittest

from application.web_search.service import WebSearchResult
from infrastructure.config.settings import get_settings
from infrastructure.web_search.factory import build_web_search_service


class WebSearchServiceTests(unittest.TestCase):
    def test_disabled_provider_returns_empty_results(self) -> None:
        previous_provider = os.environ.get("PERSONAL_AI_WEB_SEARCH_PROVIDER")
        try:
            os.environ["PERSONAL_AI_WEB_SEARCH_PROVIDER"] = "disabled"

            service = build_web_search_service(get_settings())
            response = service.search("latest c compiler flags")

            self.assertFalse(service.enabled)
            self.assertEqual(response.provider, "disabled")
            self.assertEqual(response.results, ())
        finally:
            if previous_provider is None:
                os.environ.pop("PERSONAL_AI_WEB_SEARCH_PROVIDER", None)
            else:
                os.environ["PERSONAL_AI_WEB_SEARCH_PROVIDER"] = previous_provider

    def test_allowed_domains_filter_results(self) -> None:
        provider = _FakeWebSearchProvider(
            (
                WebSearchResult(
                    title="Allowed",
                    url="https://docs.python.org/3/",
                    snippet="Docs",
                    source="docs",
                ),
                WebSearchResult(
                    title="Blocked",
                    url="https://example.com/",
                    snippet="Other",
                    source="example",
                ),
            )
        )

        from application.web_search.service import WebSearchService

        service = WebSearchService(
            provider,
            enabled=True,
            default_max_results=5,
            allowed_domains=("docs.python.org",),
        )
        response = service.search("python docs")

        self.assertTrue(service.enabled)
        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0].url, "https://docs.python.org/3/")

    def test_blocked_domains_override_allowlist(self) -> None:
        provider = _FakeWebSearchProvider(
            (
                WebSearchResult(
                    title="Allowed",
                    url="https://docs.python.org/3/library/",
                    snippet="Docs",
                    source="docs",
                ),
                WebSearchResult(
                    title="Blocked",
                    url="https://ads.docs.python.org/banner",
                    snippet="Ads",
                    source="ads",
                ),
            )
        )

        from application.web_search.service import WebSearchService

        service = WebSearchService(
            provider,
            enabled=True,
            default_max_results=5,
            allowed_domains=("docs.python.org",),
            blocked_domains=("ads.docs.python.org",),
        )
        response = service.search("python docs")

        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0].url, "https://docs.python.org/3/library/")
        self.assertEqual(response.blocked_result_count, 1)
        self.assertEqual(response.allowlist_filtered_count, 0)

    def test_search_clamps_requested_results_to_configured_ceiling(self) -> None:
        provider = _RecordingWebSearchProvider(
            tuple(
                WebSearchResult(
                    title=f"Result {index}",
                    url=f"https://docs.python.org/{index}",
                    snippet="Docs",
                    source="docs",
                )
                for index in range(10)
            )
        )

        from application.web_search.service import WebSearchService

        service = WebSearchService(
            provider,
            enabled=True,
            default_max_results=3,
        )
        response = service.search("python docs", max_results=9)

        self.assertEqual(provider.last_max_results, 3)
        self.assertEqual(len(response.results), 3)
        self.assertEqual(response.requested_max_results, 9)
        self.assertEqual(response.applied_max_results, 3)

    def test_search_normalizes_and_truncates_query_before_provider_call(self) -> None:
        provider = _RecordingWebSearchProvider(())

        from application.web_search.service import WebSearchService

        service = WebSearchService(
            provider,
            enabled=True,
            default_max_results=5,
            max_query_chars=23,
        )
        response = service.search("   latest   python\tasyncio   docs   release notes   ")

        self.assertEqual(response.query, "latest python asyncio d")
        self.assertEqual(provider.last_query, "latest python asyncio d")
        self.assertTrue(response.query_truncated)
        self.assertIn("release notes", response.original_query)

    def test_search_rejects_non_http_results(self) -> None:
        provider = _FakeWebSearchProvider(
            (
                WebSearchResult(
                    title="Unsafe",
                    url="file:///C:/secret.txt",
                    snippet="Nope",
                    source="local",
                ),
                WebSearchResult(
                    title="Safe",
                    url="https://docs.python.org/3/",
                    snippet="Docs",
                    source="docs",
                ),
            )
        )

        from application.web_search.service import WebSearchService

        service = WebSearchService(
            provider,
            enabled=True,
            default_max_results=5,
        )
        response = service.search("python docs")

        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0].url, "https://docs.python.org/3/")
        self.assertEqual(response.invalid_result_count, 1)
        self.assertEqual(response.filtered_result_count, 1)

    def test_factory_builds_searxng_provider_when_configured(self) -> None:
        previous = {
            key: os.environ.get(key)
            for key in (
                "PERSONAL_AI_WEB_SEARCH_PROVIDER",
                "PERSONAL_AI_WEB_SEARCH_BASE_URL",
                "PERSONAL_AI_WEB_SEARCH_TIMEOUT_SECONDS",
                "PERSONAL_AI_WEB_SEARCH_MAX_RESULTS",
                "PERSONAL_AI_WEB_SEARCH_MAX_QUERY_CHARS",
                "PERSONAL_AI_WEB_SEARCH_ALLOWED_DOMAINS",
                "PERSONAL_AI_WEB_SEARCH_BLOCKED_DOMAINS",
            )
        }
        try:
            os.environ["PERSONAL_AI_WEB_SEARCH_PROVIDER"] = "searxng"
            os.environ["PERSONAL_AI_WEB_SEARCH_BASE_URL"] = "http://127.0.0.1:8888"
            os.environ["PERSONAL_AI_WEB_SEARCH_TIMEOUT_SECONDS"] = "33"
            os.environ["PERSONAL_AI_WEB_SEARCH_MAX_RESULTS"] = "7"
            os.environ["PERSONAL_AI_WEB_SEARCH_MAX_QUERY_CHARS"] = "280"
            os.environ["PERSONAL_AI_WEB_SEARCH_ALLOWED_DOMAINS"] = "docs.python.org,openai.com"
            os.environ["PERSONAL_AI_WEB_SEARCH_BLOCKED_DOMAINS"] = "ads.docs.python.org"

            service = build_web_search_service(get_settings())

            self.assertTrue(service.enabled)
            self.assertEqual(service.provider_name, "searxng")
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_factory_rejects_non_local_http_endpoint(self) -> None:
        previous = {
            key: os.environ.get(key)
            for key in (
                "PERSONAL_AI_WEB_SEARCH_PROVIDER",
                "PERSONAL_AI_WEB_SEARCH_BASE_URL",
            )
        }
        try:
            os.environ["PERSONAL_AI_WEB_SEARCH_PROVIDER"] = "searxng"
            os.environ["PERSONAL_AI_WEB_SEARCH_BASE_URL"] = "http://example.com"

            with self.assertRaisesRegex(
                RuntimeError,
                "must use https for non-local endpoints",
            ):
                build_web_search_service(get_settings())
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_factory_allows_private_http_endpoint(self) -> None:
        previous = {
            key: os.environ.get(key)
            for key in (
                "PERSONAL_AI_WEB_SEARCH_PROVIDER",
                "PERSONAL_AI_WEB_SEARCH_BASE_URL",
            )
        }
        try:
            os.environ["PERSONAL_AI_WEB_SEARCH_PROVIDER"] = "searxng"
            os.environ["PERSONAL_AI_WEB_SEARCH_BASE_URL"] = "http://192.168.1.20:8080"

            service = build_web_search_service(get_settings())

            self.assertTrue(service.enabled)
            self.assertEqual(service.provider_name, "searxng")
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


class _FakeWebSearchProvider:
    def __init__(self, results: tuple[WebSearchResult, ...]) -> None:
        self.provider_name = "fake"
        self._results = results

    def search(self, query: str, *, max_results: int) -> tuple[WebSearchResult, ...]:
        return self._results[:max_results]


class _RecordingWebSearchProvider:
    def __init__(self, results: tuple[WebSearchResult, ...]) -> None:
        self.provider_name = "recording"
        self._results = results
        self.last_query: str | None = None
        self.last_max_results: int | None = None

    def search(self, query: str, *, max_results: int) -> tuple[WebSearchResult, ...]:
        self.last_query = query
        self.last_max_results = max_results
        return self._results[:max_results]


if __name__ == "__main__":
    unittest.main()
