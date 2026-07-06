"""Model-option helpers for agent runtime planning and execution."""

from __future__ import annotations


def is_high_risk_planning_model(
    model: str,
    *,
    high_risk_prefixes: tuple[str, ...],
) -> bool:
    """Return whether this model needs tighter generation caps."""
    normalized = model.strip().casefold()
    return any(prefix in normalized for prefix in high_risk_prefixes)


def planning_generation_options(
    model: str,
    *,
    high_risk_prefixes: tuple[str, ...],
) -> dict[str, object]:
    """Return bounded generation settings for the initial planning artifact."""
    if is_high_risk_planning_model(model, high_risk_prefixes=high_risk_prefixes):
        return {"num_predict": 520}
    return {"num_predict": 800}


def critique_generation_options(
    model: str,
    *,
    high_risk_prefixes: tuple[str, ...],
) -> dict[str, object]:
    """Return bounded generation settings for the critique pass."""
    if is_high_risk_planning_model(model, high_risk_prefixes=high_risk_prefixes):
        return {"num_predict": 180}
    return {"num_predict": 260}


def refinement_generation_options(
    model: str,
    *,
    high_risk_prefixes: tuple[str, ...],
) -> dict[str, object]:
    """Return bounded generation settings for the refinement pass."""
    if is_high_risk_planning_model(model, high_risk_prefixes=high_risk_prefixes):
        return {"num_predict": 520}
    return {"num_predict": 800}


def action_generation_options(
    model: str,
    *,
    high_risk_prefixes: tuple[str, ...],
) -> dict[str, object]:
    """Return bounded generation settings for module-draft and patch-plan artifacts."""
    if is_high_risk_planning_model(model, high_risk_prefixes=high_risk_prefixes):
        return {"num_predict": 360}
    return {"num_predict": 520}
