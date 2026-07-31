"""Factory helpers for constructing web-search services from settings."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from application.web_search.service import WebSearchService
from infrastructure.web_search.disabled_provider import DisabledWebSearchProvider
from infrastructure.web_search.searxng_provider import SearxngWebSearchProvider


def build_web_search_service(settings) -> WebSearchService:
    """Build a configured web-search service from centralized settings."""
    provider_name = settings.web_search_provider.casefold()
    if provider_name == "searxng":
        if not settings.web_search_base_url:
            raise RuntimeError(
                "PERSONAL_AI_WEB_SEARCH_BASE_URL must be configured when "
                "PERSONAL_AI_WEB_SEARCH_PROVIDER=searxng."
            )
        _validate_search_base_url(settings.web_search_base_url)
        provider = SearxngWebSearchProvider(
            base_url=settings.web_search_base_url,
            timeout_seconds=settings.web_search_timeout_seconds,
        )
        enabled = True
    else:
        provider = DisabledWebSearchProvider()
        enabled = False

    return WebSearchService(
        provider,
        enabled=enabled,
        default_max_results=settings.web_search_max_results,
        max_query_chars=settings.web_search_max_query_chars,
        health_probe_ttl_seconds=settings.web_search_health_probe_ttl_seconds,
        allowed_domains=settings.web_search_allowed_domains,
        blocked_domains=settings.web_search_blocked_domains,
    )


def _validate_search_base_url(base_url: str) -> None:
    parsed = urlsplit(base_url)
    scheme = parsed.scheme.casefold()
    hostname = parsed.hostname

    if scheme not in {"http", "https"}:
        raise RuntimeError(
            "PERSONAL_AI_WEB_SEARCH_BASE_URL must use http or https."
        )
    if not hostname:
        raise RuntimeError(
            "PERSONAL_AI_WEB_SEARCH_BASE_URL must include a hostname."
        )
    if scheme == "https":
        return
    if _is_local_or_private_hostname(hostname):
        return
    raise RuntimeError(
        "PERSONAL_AI_WEB_SEARCH_BASE_URL must use https for non-local endpoints."
    )


def _is_local_or_private_hostname(hostname: str) -> bool:
    lowered = hostname.casefold()
    if lowered in {"localhost", "::1"}:
        return True
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
    )


__all__ = ["build_web_search_service"]
