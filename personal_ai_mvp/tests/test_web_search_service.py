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

    def test_factory_builds_searxng_provider_when_configured(self) -> None:
        previous = {
            key: os.environ.get(key)
            for key in (
                "PERSONAL_AI_WEB_SEARCH_PROVIDER",
                "PERSONAL_AI_WEB_SEARCH_BASE_URL",
                "PERSONAL_AI_WEB_SEARCH_TIMEOUT_SECONDS",
                "PERSONAL_AI_WEB_SEARCH_MAX_RESULTS",
                "PERSONAL_AI_WEB_SEARCH_ALLOWED_DOMAINS",
            )
        }
        try:
            os.environ["PERSONAL_AI_WEB_SEARCH_PROVIDER"] = "searxng"
            os.environ["PERSONAL_AI_WEB_SEARCH_BASE_URL"] = "http://127.0.0.1:8888"
            os.environ["PERSONAL_AI_WEB_SEARCH_TIMEOUT_SECONDS"] = "33"
            os.environ["PERSONAL_AI_WEB_SEARCH_MAX_RESULTS"] = "7"
            os.environ["PERSONAL_AI_WEB_SEARCH_ALLOWED_DOMAINS"] = "docs.python.org,openai.com"

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


if __name__ == "__main__":
    unittest.main()
