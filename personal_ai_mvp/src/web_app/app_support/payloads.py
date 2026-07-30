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
        "provider": response.provider,
        "enabled": response.enabled,
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
