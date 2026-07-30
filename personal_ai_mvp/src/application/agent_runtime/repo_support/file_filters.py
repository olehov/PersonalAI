"""File classification helpers for repository inspection."""

from __future__ import annotations

from pathlib import Path

PREFERRED_CODE_EXTENSIONS = {
    ".py",
    ".c",
    ".h",
    ".hpp",
    ".cpp",
    ".cc",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
}
SOURCE_LIKE_FILENAMES = {
    "makefile",
    "cmakelists.txt",
    "pyproject.toml",
    "package.json",
}
EXCLUDED_FILE_EXTENSIONS = {
    ".json",
    ".log",
    ".sqlite3",
    ".db",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".zip",
}
EXCLUDED_FILE_NAME_PARTS = (
    "raw",
    "response",
    "build",
    "artifact",
    "draft",
    "history",
    "trace",
)


def is_preferred_repo_context_file(file_path: Path) -> bool:
    suffix = file_path.suffix.casefold()
    name = file_path.name.casefold()
    if name in SOURCE_LIKE_FILENAMES:
        return True
    if suffix in PREFERRED_CODE_EXTENSIONS:
        return True
    return False


def is_excluded_repo_context_file(file_path: Path) -> bool:
    suffix = file_path.suffix.casefold()
    name = file_path.name.casefold()
    if suffix == ".md" and "readme" not in name:
        return True
    if suffix in EXCLUDED_FILE_EXTENSIONS:
        return True
    return any(part in name for part in EXCLUDED_FILE_NAME_PARTS)
