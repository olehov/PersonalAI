"""Deterministic local text embeddings without external dependencies."""

from __future__ import annotations

import math
import re


class HashedEmbeddingProvider:
    """Builds simple normalized vectors from token hashes."""

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    def embed_text(self, text: str) -> tuple[float, ...]:
        """Embeds text into a normalized dense vector."""
        vector = [0.0] * self._dimensions
        tokens = _tokenize(text)
        if not tokens:
            return tuple(vector)

        for token in tokens:
            index = hash(token) % self._dimensions
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return tuple(vector)
        return tuple(value / norm for value in vector)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]{2,}", text.casefold())
