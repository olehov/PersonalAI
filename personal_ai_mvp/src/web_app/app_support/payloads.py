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
