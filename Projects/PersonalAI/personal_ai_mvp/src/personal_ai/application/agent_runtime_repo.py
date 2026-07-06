"""Repository inspection helpers for the agent runtime."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path


def inspect_repo_summary(repo_path: Path, *, vault_root: Path) -> dict[str, str]:
    entries = sorted(repo_path.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))
    preview_entries = entries[:12]
    entry_lines = [
        f"{'[dir]' if item.is_dir() else '[file]'} {item.name}"
        for item in preview_entries
    ]
    has_makefile = (repo_path / "Makefile").exists()
    has_pyproject = (repo_path / "pyproject.toml").exists()
    has_package = (repo_path / "package.json").exists()
    has_src = (repo_path / "src").is_dir()
    has_tests = (repo_path / "tests").is_dir()
    summary = "\n".join(
        [
            f"path={repo_path.as_posix()}",
            f"entry_count={len(entries)}",
            f"has_makefile={str(has_makefile).lower()}",
            f"has_pyproject={str(has_pyproject).lower()}",
            f"has_package_json={str(has_package).lower()}",
            f"has_src_dir={str(has_src).lower()}",
            f"has_tests_dir={str(has_tests).lower()}",
            "entries=" + "; ".join(entry_lines) if entry_lines else "entries=none",
        ]
    )
    return {
        "display_path": repo_path.relative_to(vault_root).as_posix(),
        "summary": summary,
    }


def build_validation_plan(
    repo_summary: dict[str, str],
    build_config_summary: str | None,
) -> str:
    summary_text = repo_summary["summary"]
    lines: list[str] = [f"repo={repo_summary['display_path']}"]
    commands = recommend_validation_commands(
        repo_summary=repo_summary,
        build_config_summary=build_config_summary,
    )
    if "has_makefile=true" in summary_text:
        lines.extend(
            [
                "recommended_commands=" + "; ".join(commands),
                "validation_focus=confirm the first slice compiles before broad feature work",
            ]
        )
    elif "has_pyproject=true" in summary_text:
        lines.extend(
            [
                "recommended_commands=" + "; ".join(commands),
                "validation_focus=run the existing Python test suite for the modified slice",
            ]
        )
    elif "has_package_json=true" in summary_text:
        lines.extend(
            [
                "recommended_commands=" + "; ".join(commands),
                "validation_focus=use the package scripts already defined by the project",
            ]
        )
    else:
        lines.extend(
            [
                "recommended_commands=" + "; ".join(commands),
                "validation_focus=no standard validation command was inferred from repository markers",
            ]
        )
    return "\n".join(lines)


def recommend_validation_commands(
    *,
    repo_summary: dict[str, str],
    build_config_summary: str | None,
) -> list[str]:
    commands: list[str] = []
    summary_text = repo_summary["summary"]
    config_text = build_config_summary or ""

    if "has_makefile=true" in summary_text:
        make_targets = extract_summary_values(config_text, "targets")
        if "all" in make_targets:
            commands.append("make all")
        elif make_targets:
            commands.append(f"make {make_targets[0]}")
        else:
            commands.append("make")
        if "test" in make_targets:
            commands.append("make test")
        if "clean" in make_targets:
            commands.append("make clean")
        return commands

    if "has_pyproject=true" in summary_text:
        sections = extract_summary_values(config_text, "sections")
        test_framework_hints = extract_summary_values(config_text, "test_framework_hints")
        has_pytest_config = (
            "[tool.pytest.ini_options]" in sections
            or "[tool.pytest]" in sections
        )
        prefers_pytest = (
            "pytest_style" in test_framework_hints
            and "unittest_style" not in test_framework_hints
        )
        if "has_tests_dir=true" in summary_text:
            if prefers_pytest and has_pytest_config:
                commands.append("python -m pytest")
                commands.append("python -m unittest discover -s tests")
            else:
                commands.append("python -m unittest discover -s tests")
                if has_pytest_config:
                    commands.append("python -m pytest")
        elif has_pytest_config:
            commands.append("python -m pytest")
        else:
            commands.append("python -m unittest")
        return commands

    if "has_package_json=true" in summary_text:
        scripts = extract_summary_values(config_text, "scripts")
        for script_name in ("test", "build", "lint"):
            if script_name in scripts:
                commands.append(f"npm run {script_name}")
        if not commands:
            commands.append("npm run build")
        return commands

    return ["inspect existing build/test entrypoints before execution"]


def build_file_tree_summary(repo_path: Path, *, vault_root: Path) -> str:
    lines = [f"repo={repo_path.relative_to(vault_root).as_posix()}"]
    lines.extend(collect_tree_lines(repo_path, depth=0, max_depth=2, max_entries=24))
    return "\n".join(lines)


def build_config_summary(repo_path: Path, *, vault_root: Path) -> str:
    manifest_names = ("Makefile", "pyproject.toml", "package.json")
    lines = [f"repo={repo_path.relative_to(vault_root).as_posix()}"]
    found_any = False
    for manifest_name in manifest_names:
        manifest_path = repo_path / manifest_name
        if not manifest_path.exists() or not manifest_path.is_file():
            continue
        found_any = True
        lines.append(f"manifest={manifest_name}")
        manifest_text = manifest_path.read_text(encoding="utf-8", errors="replace")
        lines.extend(extract_manifest_summary(manifest_name, manifest_text))
    if not found_any:
        lines.append("manifest=none")
        lines.append("summary=No standard build manifest was found at repository root.")
    test_framework_hints = detect_test_framework_hints(repo_path)
    if test_framework_hints:
        lines.append("test_framework_hints=" + ", ".join(test_framework_hints))
    return "\n".join(lines)


def extract_manifest_summary(
    manifest_name: str,
    manifest_text: str,
) -> list[str]:
    if manifest_name == "Makefile":
        return summarize_makefile(manifest_text)
    if manifest_name == "pyproject.toml":
        return summarize_pyproject(manifest_text)
    if manifest_name == "package.json":
        return summarize_package_json(manifest_text)
    return ["summary=Unsupported manifest type."]


def summarize_makefile(manifest_text: str) -> list[str]:
    targets: list[str] = []
    for line in manifest_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("\t"):
            continue
        if ":" not in stripped:
            continue
        target = stripped.split(":", 1)[0].strip()
        if not target or "=" in target:
            continue
        for candidate in target.split():
            if candidate and "%" not in candidate:
                targets.append(candidate)
    unique_targets = list(dict.fromkeys(targets))[:8]
    if unique_targets:
        return ["targets=" + ", ".join(unique_targets)]
    return ["targets=none_detected"]


def summarize_pyproject(manifest_text: str) -> list[str]:
    try:
        parsed = tomllib.loads(manifest_text)
    except tomllib.TOMLDecodeError:
        parsed = None
    sections: list[str] = []
    if parsed is not None:
        sections.extend(flatten_toml_sections(parsed))
    else:
        for line in manifest_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                sections.append(stripped)
    unique_sections = list(dict.fromkeys(sections))[:8]
    if unique_sections:
        return ["sections=" + ", ".join(unique_sections)]
    return ["sections=none_detected"]


def detect_test_framework_hints(repo_path: Path) -> tuple[str, ...]:
    tests_dir = repo_path / "tests"
    if not tests_dir.is_dir():
        return ()
    pytest_detected = False
    unittest_detected = False
    inspected = 0
    for test_file in sorted(tests_dir.rglob("test*.py")):
        if inspected >= 12:
            break
        inspected += 1
        try:
            content = test_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if (
            "import unittest" in content
            or "from unittest" in content
            or "unittest.TestCase" in content
            or "TestCase)" in content
        ):
            unittest_detected = True
        if "def test_" in content or "pytest" in content or "tmp_path" in content:
            pytest_detected = True
    hints: list[str] = []
    if pytest_detected:
        hints.append("pytest_style")
    if unittest_detected:
        hints.append("unittest_style")
    return tuple(hints)


def summarize_package_json(manifest_text: str) -> list[str]:
    try:
        parsed = json.loads(manifest_text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        scripts = parsed.get("scripts")
        if isinstance(scripts, dict):
            script_names = [name for name in scripts.keys() if isinstance(name, str)]
            unique_scripts = list(dict.fromkeys(script_names))[:8]
            if unique_scripts:
                return ["scripts=" + ", ".join(unique_scripts)]
        keys = [key for key in parsed.keys() if isinstance(key, str)]
        unique_keys = list(dict.fromkeys(keys))[:8]
        if unique_keys:
            return ["keys=" + ", ".join(unique_keys)]
        return ["keys=none_detected"]
    script_names = re.findall(r'"([A-Za-z0-9:_-]+)"\s*:\s*"', manifest_text)
    unique_scripts = list(dict.fromkeys(script_names))[:8]
    if unique_scripts:
        return ["keys=" + ", ".join(unique_scripts)]
    return ["keys=none_detected"]


def flatten_toml_sections(
    parsed: dict[str, object],
    *,
    prefix: str = "",
) -> list[str]:
    sections: list[str] = []
    for key, value in parsed.items():
        if not isinstance(key, str):
            continue
        current = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            sections.append(f"[{current}]")
            sections.extend(flatten_toml_sections(value, prefix=current))
    return sections


def extract_summary_values(
    summary_text: str,
    key: str,
) -> tuple[str, ...]:
    for line in summary_text.splitlines():
        if not line.startswith(f"{key}="):
            continue
        raw_values = line.split("=", 1)[1].strip()
        if not raw_values or raw_values.endswith("none_detected"):
            return ()
        values = [
            value.strip()
            for value in raw_values.split(",")
            if value.strip()
        ]
        return tuple(values)
    return ()


def collect_tree_lines(
    directory: Path,
    *,
    depth: int,
    max_depth: int,
    max_entries: int,
) -> list[str]:
    if depth > max_depth or max_entries <= 0:
        return []
    try:
        entries = sorted(
            directory.iterdir(),
            key=lambda item: (not item.is_dir(), item.name.casefold()),
        )
    except OSError:
        return [f"{'  ' * depth}- [unreadable] {directory.name}"]

    lines: list[str] = []
    remaining = max_entries
    for entry in entries:
        if remaining <= 0:
            break
        prefix = "  " * depth
        marker = "[dir]" if entry.is_dir() else "[file]"
        lines.append(f"{prefix}- {marker} {entry.name}")
        remaining -= 1
        if entry.is_dir() and depth < max_depth and remaining > 0:
            child_lines = collect_tree_lines(
                entry,
                depth=depth + 1,
                max_depth=max_depth,
                max_entries=remaining,
            )
            lines.extend(child_lines)
            remaining -= len(child_lines)
    if len(entries) > len(lines):
        lines.append(f"{'  ' * depth}- ...")
    return lines


def find_repo_files(
    repo_path: Path,
    *,
    vault_root: Path,
    contains: str,
    limit: int,
) -> list[str]:
    matches: list[str] = []
    contains_lower = contains.casefold()
    for child in repo_path.rglob("*"):
        if len(matches) >= limit:
            break
        if not child.is_file():
            continue
        relative = child.relative_to(vault_root).as_posix()
        if contains_lower in relative.casefold():
            matches.append(relative)
    return matches


def find_repo_files_by_name(
    repo_path: Path,
    *,
    vault_root: Path,
    contains: str,
    limit: int,
) -> list[str]:
    matches: list[str] = []
    contains_lower = contains.casefold()
    for child in repo_path.rglob("*"):
        if len(matches) >= limit:
            break
        if not child.is_file():
            continue
        if contains_lower not in child.name.casefold():
            continue
        matches.append(child.relative_to(vault_root).as_posix())
    return matches


def collect_target_file_snippets(
    *,
    resolved_repo_path: Path | None,
    request_text: str,
    planning_output: str,
    vault_root: Path,
    extract_repo_like_paths,
) -> dict[str, str]:
    if resolved_repo_path is None:
        return {}
    target_files = select_target_file_paths(
        resolved_repo_path=resolved_repo_path,
        request_text=request_text,
        planning_output=planning_output,
        vault_root=vault_root,
        extract_repo_like_paths=extract_repo_like_paths,
    )
    snippets: dict[str, str] = {}
    for relative_path in target_files:
        file_path = vault_root / relative_path
        snippet = read_file_snippet(file_path)
        if snippet:
            snippets[relative_path] = snippet
    return snippets


def select_target_file_paths(
    *,
    resolved_repo_path: Path,
    request_text: str,
    planning_output: str,
    vault_root: Path,
    extract_repo_like_paths,
) -> tuple[str, ...]:
    candidates: list[str] = []
    code_extensions = {".py", ".c", ".h", ".hpp", ".cpp", ".js", ".ts", ".tsx", ".jsx", ".java"}
    for path_hint in extract_repo_like_paths(f"{planning_output}\n{request_text}"):
        normalized_hint = path_hint.replace("\\", "/").strip("./ ")
        canonical = canonicalize_repo_path_hint(
            path_hint,
            vault_root=vault_root,
            resolved_repo_path=resolved_repo_path,
            files_only=True,
        )
        if canonical is not None:
            candidates.append(canonical)
            continue
        hint_path = Path(normalized_hint)
        if "/" in normalized_hint and hint_path.suffix == "":
            continue
        basename = hint_path.name.casefold()
        if basename:
            candidates.extend(
                find_repo_files(
                    resolved_repo_path,
                    vault_root=vault_root,
                    contains=basename,
                    limit=2,
                )
            )

    patterns = ("store", "cli", "parser", "token", "main", "shell")
    for pattern in patterns:
        candidates.extend(
            find_repo_files_by_name(
                resolved_repo_path,
                vault_root=vault_root,
                contains=pattern,
                limit=2,
            )
        )
        candidates.extend(
            find_repo_files(
                resolved_repo_path,
                vault_root=vault_root,
                contains=pattern,
                limit=2,
            )
        )

    deduped = list(dict.fromkeys(candidates))
    deduped.sort(
        key=lambda item: (
            Path(item).suffix.casefold() not in code_extensions,
            "src/" not in item.replace("\\", "/").casefold(),
            "readme" in Path(item).name.casefold(),
            "pyproject.toml" in item.casefold() or "package.json" in item.casefold() or "makefile" in item.casefold(),
            len(Path(item).parts),
            item.casefold(),
        )
    )
    return tuple(deduped[:3])


def canonicalize_repo_path_hint(
    path_hint: str,
    *,
    vault_root: Path,
    resolved_repo_path: Path | None,
    files_only: bool,
) -> str | None:
    normalized = path_hint.replace("\\", "/").strip("./ ")
    if not normalized:
        return None
    direct = vault_root / normalized
    if direct.exists():
        if files_only and not direct.is_file():
            return None
        return direct.relative_to(vault_root).as_posix()
    if resolved_repo_path is not None:
        repo_relative = resolved_repo_path / normalized
        if repo_relative.exists():
            if files_only and not repo_relative.is_file():
                return None
            return repo_relative.relative_to(vault_root).as_posix()

        normalized_parts = tuple(part.casefold() for part in Path(normalized).parts if part)
        if normalized_parts:
            for child in resolved_repo_path.rglob("*"):
                if files_only and not child.is_file():
                    continue
                child_parts = child.relative_to(resolved_repo_path).parts
                if len(child_parts) < len(normalized_parts):
                    continue
                suffix = tuple(part.casefold() for part in child_parts[-len(normalized_parts):])
                if suffix == normalized_parts:
                    return child.relative_to(vault_root).as_posix()
    return None


def read_file_snippet(file_path: Path, *, max_lines: int = 40, max_chars: int = 1600) -> str:
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    lines = content.splitlines()
    excerpt = "\n".join(lines[:max_lines]).strip()
    if not excerpt:
        return "(empty file)"
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip() + "\n..."
    return excerpt
