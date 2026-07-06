"""Policy checks for safe note writes inside the vault."""

from __future__ import annotations

from pathlib import Path


class NotePolicy:
    """Validates whether a note mutation is safe to apply."""

    RESTRICTED_PREFIXES = (
        Path(".personal_ai"),
        Path(".obsidian"),
        Path(".trash"),
        Path(".history"),
        Path("Projects/PersonalAI/personal_ai_mvp"),
    )

    def __init__(self, vault_root: Path) -> None:
        self._vault_root = vault_root.resolve()

    def validate_target(self, relative_path: Path) -> tuple[bool, tuple[str, ...]]:
        """Checks whether a target path is allowed for note writes."""
        warnings: list[str] = []

        if relative_path.suffix.lower() != ".md":
            warnings.append("Only markdown note files can be modified.")

        normalized = Path(relative_path.as_posix())
        if normalized.is_absolute():
            warnings.append("Target path must stay relative to the vault root.")

        if self.is_restricted_relative_path(normalized):
            warnings.append(f"Target path is inside restricted area: {self._matching_restricted_prefix(normalized)}")

        absolute_target = (self._vault_root / normalized).resolve()
        try:
            absolute_target.relative_to(self._vault_root)
        except ValueError:
            warnings.append("Target path escapes the vault root.")

        return not warnings, tuple(warnings)

    @classmethod
    def is_restricted_relative_path(cls, relative_path: Path) -> bool:
        """Return whether a vault-relative path points inside a restricted area."""
        normalized = Path(relative_path.as_posix())
        return cls._matching_restricted_prefix(normalized) is not None

    @classmethod
    def _matching_restricted_prefix(cls, relative_path: Path) -> str | None:
        normalized = Path(relative_path.as_posix())
        for restricted in cls.RESTRICTED_PREFIXES:
            try:
                normalized.relative_to(restricted)
                return restricted.as_posix()
            except ValueError:
                continue
        return None
