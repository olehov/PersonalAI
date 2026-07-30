from __future__ import annotations

from pathlib import Path

from infrastructure.config.settings import get_settings


def state_dir_name() -> str:
    return get_settings().state_dir_name


def history_db_name() -> str:
    return get_settings().history_db_name


def runtime_drafts_dir_name() -> str:
    return get_settings().agent_runtime_drafts_dir_name


def runtime_scaffold_dir_name() -> str:
    return get_settings().runtime_scaffold_dir_name


def runtime_write_probe_dir_name() -> str:
    return get_settings().runtime_write_probe_dir_name


def state_dir_path(root: Path) -> Path:
    return root / state_dir_name()


def history_db_path(root: Path) -> Path:
    return state_dir_path(root) / history_db_name()


def runtime_drafts_path(root: Path) -> Path:
    return state_dir_path(root) / runtime_drafts_dir_name()


def scaffold_path(*parts: str) -> str:
    base = Path(runtime_scaffold_dir_name())
    if not parts:
        return base.as_posix()
    return base.joinpath(*parts).as_posix()


def scaffold_root(root: Path) -> Path:
    return root / runtime_scaffold_dir_name()


def write_probe_root(root: Path) -> Path:
    return root / runtime_write_probe_dir_name()
