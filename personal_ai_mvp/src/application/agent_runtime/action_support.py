"""Filesystem and command support helpers for runtime action execution."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

from application.agent_runtime.scaffold_templates import (
    scaffold_path as build_scaffold_path,
)
from infrastructure.config.settings import get_settings

RESTRICTED_REPO_SEGMENTS = {
    ".git",
    ".runtime",
    ".venv",
    ".venv-unsloth",
    "node_modules",
    "__pycache__",
}


def _normalized_relative_parts(path_value: str) -> tuple[str, ...]:
    """Return normalized repo-relative path parts for policy checks."""
    normalized = path_value.replace("\\", "/").strip().strip("/")
    if not normalized:
        return ()
    return tuple(part for part in Path(normalized).parts if part not in {"", "."})


def _is_allowed_runtime_subtree(candidate_parts: tuple[str, ...]) -> bool:
    """Return whether the candidate matches one configured runtime-safe subtree."""
    if not candidate_parts:
        return False
    allowed_roots = (
        runtime_scaffold_dir_name(),
        runtime_write_probe_dir_name(),
    )
    for raw_root in allowed_roots:
        root_parts = _normalized_relative_parts(raw_root)
        if root_parts and candidate_parts[: len(root_parts)] == root_parts:
            return True
    return False


def state_dir_name() -> str:
    """Return the configured PersonalAI state directory name."""
    return get_settings().state_dir_name


def runtime_scaffold_dir_name() -> str:
    """Return the configured runtime scaffold directory name."""
    return get_settings().runtime_scaffold_dir_name


def runtime_write_probe_dir_name() -> str:
    """Return the configured runtime write-probe directory name."""
    return get_settings().runtime_write_probe_dir_name


def scaffold_path(*parts: str) -> str:
    """Build a path rooted under the configured runtime scaffold directory."""
    return build_scaffold_path(runtime_scaffold_dir_name(), *parts)


def slugify_target(target: str) -> str:
    """Convert a target path into a filename-safe draft slug."""
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", target.strip())
    sanitized = sanitized.strip("-._")
    return sanitized or "artifact"


def persist_artifact_draft(
    *,
    vault_root: Path,
    resolved_repo_path: Path | None,
    kind: str,
    target: str,
    content: str,
) -> str | None:
    """Persist one runtime artifact draft under the configured state directory."""
    drafts_root = get_settings().runtime_drafts_path(vault_root)
    repo_segment = (
        resolved_repo_path.relative_to(vault_root).as_posix().replace("/", "__")
        if resolved_repo_path is not None
        else "no_repo"
    )
    output_dir = drafts_root / repo_segment
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{kind}__{slugify_target(target)}.md"
    output_path.write_text(content, encoding="utf-8")
    return output_path.relative_to(vault_root).as_posix()


def resolve_allowed_command(command: str) -> list[str] | None:
    """Resolve one whitelisted command into argv for controlled execution."""
    stripped = command.strip()
    if not stripped:
        return None
    if stripped.startswith("python -m "):
        suffix = stripped[len("python -m ") :].strip()
        if not suffix:
            return None
        return [sys.executable, "-m", *suffix.split()]
    if stripped.startswith("npm run "):
        npm_path = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm_path:
            return None
        script = stripped[len("npm run ") :].strip()
        if not script:
            return None
        return [npm_path, "run", *script.split()]
    if stripped.startswith("make"):
        make_path = shutil.which("make")
        if not make_path:
            return None
        parts = stripped.split()
        return [make_path, *parts[1:]]
    return None


def resolve_safe_repo_write_path(
    *,
    resolved_repo_path: Path | None,
    target: str,
) -> tuple[Path | None, str | None]:
    """Resolve a repo-relative write target while enforcing scope restrictions."""
    if resolved_repo_path is None:
        return None, "Safe write actions need a resolved repository path."
    normalized = target.replace("\\", "/").strip()
    if not normalized:
        return None, "Safe write target was empty."
    candidate = Path(normalized)
    if candidate.is_absolute():
        return None, "Absolute paths are not allowed for safe repo writes."
    if any(part in {"..", ""} for part in candidate.parts):
        return None, "Parent-directory traversal is not allowed for safe repo writes."
    candidate_parts = _normalized_relative_parts(normalized)
    if _is_allowed_runtime_subtree(candidate_parts):
        resolved_path = (resolved_repo_path / candidate).resolve()
        try:
            resolved_path.relative_to(resolved_repo_path.resolve())
        except ValueError:
            return None, "Resolved write target escaped the selected repository scope."
        return resolved_path, None
    restricted_segments = RESTRICTED_REPO_SEGMENTS | {state_dir_name().casefold()}
    if any(part.casefold() in restricted_segments for part in candidate.parts):
        return None, "Safe repo writes cannot target restricted runtime or environment directories."
    resolved_path = (resolved_repo_path / candidate).resolve()
    try:
        resolved_path.relative_to(resolved_repo_path.resolve())
    except ValueError:
        return None, "Resolved write target escaped the selected repository scope."
    return resolved_path, None


def build_probe_file_content(
    *,
    repo_display_path: str,
    target: str,
    request_text: str,
    instruction: str,
) -> str:
    """Build the content of a controlled write-probe file."""
    return "\n".join(
        [
            "# Runtime Write Probe",
            "",
            "created_by=safe_agent_runtime",
            f"repo={repo_display_path}",
            f"target={target}",
            f"request={request_text}",
            f"instruction={instruction}",
            "",
            "This file was created by the controlled create_file runtime adapter.",
        ]
    )


def is_runtime_scaffold_path(path: str) -> bool:
    """Return whether the path stays under the configured runtime scaffold root."""
    normalized = path.replace("\\", "/").strip().strip("/")
    scaffold_root = runtime_scaffold_dir_name().replace("\\", "/").strip().strip("/")
    return normalized == scaffold_root or normalized.startswith(f"{scaffold_root}/")


def manifest_has_only_runtime_scaffold_paths(
    dirs: list[str],
    files: list[dict[str, str]],
) -> bool:
    """Return whether all manifest items remain under the runtime scaffold root."""
    if any(not is_runtime_scaffold_path(path) for path in dirs):
        return False
    if any(not is_runtime_scaffold_path(item["path"]) for item in files):
        return False
    return True
