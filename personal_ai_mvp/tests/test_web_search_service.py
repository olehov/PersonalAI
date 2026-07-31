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

    def test_search_returns_degraded_response_when_provider_fails(self) -> None:
        from application.web_search.service import WebSearchService

        service = WebSearchService(
            _FailingWebSearchProvider("SearxNG web search timed out."),
            enabled=True,
            default_max_results=5,
        )

        response = service.search("latest python docs")

        self.assertTrue(response.enabled)
        self.assertTrue(response.degraded)
        self.assertEqual(response.error, "SearxNG web search timed out.")
        self.assertEqual(response.results, ())
        self.assertEqual(response.applied_max_results, 5)

    def test_health_snapshot_reports_disabled_ready_and_degraded_states(self) -> None:
        from application.web_search.service import WebSearchService

        disabled_service = WebSearchService(
            _FakeWebSearchProvider(()),
            enabled=False,
            default_max_results=5,
        )
        disabled_snapshot = disabled_service.health_snapshot()
        self.assertEqual(disabled_snapshot.status, "disabled")
        self.assertFalse(disabled_snapshot.enabled)

        ready_service = WebSearchService(
            _FakeWebSearchProvider(
                (
                    WebSearchResult(
                        title="Docs",
                        url="https://docs.python.org/3/",
                        snippet="Docs",
                        source="docs",
                    ),
                )
            ),
            enabled=True,
            default_max_results=5,
        )
        ready_before = ready_service.health_snapshot()
        self.assertEqual(ready_before.status, "ready")
        ready_service.search("python docs")
        ready_after = ready_service.health_snapshot()
        self.assertEqual(ready_after.status, "ready")
        self.assertIsNotNone(ready_after.last_attempted_at)
        self.assertIsNotNone(ready_after.last_success_at)

        degraded_service = WebSearchService(
            _FailingWebSearchProvider("SearxNG web search timed out."),
            enabled=True,
            default_max_results=5,
        )
        degraded_service.search("python docs")
        degraded_snapshot = degraded_service.health_snapshot()
        self.assertEqual(degraded_snapshot.status, "degraded")
        self.assertTrue(degraded_snapshot.degraded)
        self.assertEqual(degraded_snapshot.last_error, "SearxNG web search timed out.")

    def test_refresh_health_uses_provider_probe(self) -> None:
        from application.web_search.service import WebSearchService

        ready_provider = _ProbeWebSearchProvider()
        ready_service = WebSearchService(
            ready_provider,
            enabled=True,
            default_max_results=5,
        )
        ready_snapshot = ready_service.refresh_health()
        self.assertEqual(ready_snapshot.status, "ready")
        self.assertEqual(ready_provider.probe_calls, 1)
        self.assertIsNotNone(ready_snapshot.last_success_at)

        failing_provider = _FailingProbeWebSearchProvider("probe failed")
        failing_service = WebSearchService(
            failing_provider,
            enabled=True,
            default_max_results=5,
        )
        failing_snapshot = failing_service.refresh_health()
        self.assertEqual(failing_snapshot.status, "degraded")
        self.assertEqual(failing_snapshot.last_error, "probe failed")
        self.assertEqual(failing_provider.probe_calls, 1)


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


class _FailingWebSearchProvider:
    def __init__(self, message: str) -> None:
        self.provider_name = "failing"
        self._message = message

    def search(self, query: str, *, max_results: int) -> tuple[WebSearchResult, ...]:
        raise RuntimeError(self._message)

    def probe(self) -> None:
        raise RuntimeError(self._message)


class _ProbeWebSearchProvider:
    def __init__(self) -> None:
        self.provider_name = "probe"
        self.probe_calls = 0

    def search(self, query: str, *, max_results: int) -> tuple[WebSearchResult, ...]:
        return ()

    def probe(self) -> None:
        self.probe_calls += 1


class _FailingProbeWebSearchProvider:
    def __init__(self, message: str) -> None:
        self.provider_name = "probe-failing"
        self._message = message
        self.probe_calls = 0

    def search(self, query: str, *, max_results: int) -> tuple[WebSearchResult, ...]:
        return ()

    def probe(self) -> None:
        self.probe_calls += 1
        raise RuntimeError(self._message)


if __name__ == "__main__":
    unittest.main()
