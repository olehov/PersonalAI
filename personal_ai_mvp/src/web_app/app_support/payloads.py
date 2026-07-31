"""Payload helpers for the PersonalAI web application."""

from __future__ import annotations


def serialize_preprocess_result(result) -> dict[str, object]:
    """Convert one prompt-preprocessing result into a JSON-friendly payload."""
    return {
        "mode": result.mode,
        "applied": result.applied,
        "original_text": result.original_text,
        "processed_text": result.processed_text,
        "translator_output": result.translator_output,
        "translator_error": result.translator_error,
        "fallback_reason": result.fallback_reason,
    }


def serialize_web_search_response(response) -> dict[str, object]:
    """Convert one web-search response into a JSON-friendly payload."""
    return {
        "query": response.query,
        "original_query": response.original_query,
        "query_truncated": response.query_truncated,
        "provider": response.provider,
        "enabled": response.enabled,
        "degraded": response.degraded,
        "error": response.error,
        "policy": {
            "requested_max_results": response.requested_max_results,
            "applied_max_results": response.applied_max_results,
            "raw_result_count": response.raw_result_count,
            "filtered_result_count": response.filtered_result_count,
            "invalid_result_count": response.invalid_result_count,
            "blocked_result_count": response.blocked_result_count,
            "allowlist_filtered_count": response.allowlist_filtered_count,
        },
        "results": [
            {
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "source": item.source,
            }
            for item in response.results
        ],
    }
