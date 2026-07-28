"""Shared text normalization helpers for prompt preprocessing and routing."""

from __future__ import annotations


_MOJIBAKE_MARKERS = ("Р ", "РЎ", "Гђ", "Г‘", "Г‚", "Гѓ")
_MOJIBAKE_SOURCE_ENCODINGS = ("cp1251", "latin1")


def repair_common_utf8_mojibake(text: str) -> str:
    """Repair common UTF-8 Cyrillic mojibake such as ``Р ...`` sequences."""
    original_score = _mojibake_score(text)
    if original_score < 2:
        return text

    best_candidate = text
    best_score = original_score
    for source_encoding in _MOJIBAKE_SOURCE_ENCODINGS:
        try:
            candidate = text.encode(source_encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        candidate_score = _mojibake_score(candidate)
        if candidate_score >= best_score:
            continue
        best_candidate = candidate
        best_score = candidate_score

    return best_candidate


def _mojibake_score(text: str) -> int:
    return sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)
