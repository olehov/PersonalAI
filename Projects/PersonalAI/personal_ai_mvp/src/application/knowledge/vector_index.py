"""In-memory vector index for note-level semantic retrieval."""

from __future__ import annotations

from pathlib import Path

from domain.models import NoteDocument


class InMemoryVectorIndex:
    """Stores note vectors and provides cosine-similarity search."""

    def __init__(self, embedding_provider) -> None:
        self._embedding_provider = embedding_provider
        self._vectors: dict[Path, tuple[float, ...]] = {}

    def rebuild(self, notes: list[NoteDocument]) -> None:
        """Rebuilds the vector index for the given notes."""
        self._vectors = {
            note.path: self._embedding_provider.embed_text(_note_text(note))
            for note in notes
        }

    def search(self, query: str, *, top_k: int = 8) -> dict[Path, float]:
        """Returns the top semantic matches for a query."""
        query_vector = self._embedding_provider.embed_text(query)
        if not any(query_vector):
            return {}

        ranked = sorted(
            (
                (path, _cosine_similarity(query_vector, vector))
                for path, vector in self._vectors.items()
            ),
            key=lambda item: (-item[1], item[0].as_posix()),
        )
        return {
            path: score
            for path, score in ranked[:top_k]
            if score > 0
        }


def _note_text(note: NoteDocument) -> str:
    return "\n".join(
        [
            note.title,
            note.path.as_posix(),
            note.content,
        ]
    )


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))
