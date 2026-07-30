"""Model-option helpers for grounded ask/chat generation."""

from __future__ import annotations


def is_resource_heavy_chat_model(model: str) -> bool:
    """Return whether the chat model should use tighter but explicit output caps."""
    return "gpt-oss" in model.strip().casefold()


def answer_generation_options(
    model: str,
    *,
    task_mode: str,
    reasoning_mode: str,
) -> dict[str, object]:
    """Return generation caps for the first grounded answer pass."""
    if task_mode == "implementation":
        if is_resource_heavy_chat_model(model):
            return {"num_predict": 1400}
        if reasoning_mode == "high":
            return {"num_predict": 1800}
        return {"num_predict": 1600}

    if is_resource_heavy_chat_model(model):
        return {"num_predict": 700}
    if reasoning_mode == "high":
        return {"num_predict": 900}
    return {"num_predict": 700}


def critique_generation_options(
    model: str,
    *,
    task_mode: str,
) -> dict[str, object]:
    """Return bounded generation caps for the critique pass."""
    if task_mode == "implementation":
        if is_resource_heavy_chat_model(model):
            return {"num_predict": 220}
        return {"num_predict": 320}
    if is_resource_heavy_chat_model(model):
        return {"num_predict": 140}
    return {"num_predict": 220}


def refinement_generation_options(
    model: str,
    *,
    task_mode: str,
    reasoning_mode: str,
) -> dict[str, object]:
    """Return generation caps for the final refined answer."""
    if task_mode == "implementation":
        if is_resource_heavy_chat_model(model):
            return {"num_predict": 1400}
        if reasoning_mode == "high":
            return {"num_predict": 1800}
        return {"num_predict": 1600}

    if is_resource_heavy_chat_model(model):
        return {"num_predict": 700}
    if reasoning_mode == "high":
        return {"num_predict": 900}
    return {"num_predict": 700}


def repair_generation_options(
    model: str,
    *,
    task_mode: str,
    reasoning_mode: str,
    retry_index: int = 0,
) -> dict[str, object]:
    """Return generation caps for one bounded acceptance-repair pass."""
    if task_mode == "implementation":
        if is_resource_heavy_chat_model(model):
            return {"num_predict": 1200 if retry_index == 0 else 1800}
        if reasoning_mode == "high":
            return {"num_predict": 1600 if retry_index == 0 else 2200}
        return {"num_predict": 1400 if retry_index == 0 else 2000}

    if is_resource_heavy_chat_model(model):
        return {"num_predict": 650 if retry_index == 0 else 850}
    if reasoning_mode == "high":
        return {"num_predict": 850 if retry_index == 0 else 1050}
    return {"num_predict": 650 if retry_index == 0 else 850}
