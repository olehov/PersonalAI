"""Frontend asset helpers for the PersonalAI web application."""

from __future__ import annotations

from pathlib import Path


def frontend_index_path(frontend_dist_dir: Path) -> Path:
    return frontend_dist_dir / "index.html"


def has_frontend_assets(frontend_dist_dir: Path) -> bool:
    return frontend_index_path(frontend_dist_dir).exists()


def resolve_frontend_asset(frontend_dist_dir: Path, request_path: str) -> Path:
    cleaned = request_path.split("?", maxsplit=1)[0].split("#", maxsplit=1)[0]
    relative = cleaned.lstrip("/") or "index.html"
    candidate = (frontend_dist_dir / relative).resolve()
    root = frontend_dist_dir.resolve()
    if root == candidate or root in candidate.parents:
        return candidate
    return root / "index.html"
