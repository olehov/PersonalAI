"""Runner builders for training evaluation backends."""

from __future__ import annotations

from typing import Callable

from personal_ai.domain.models import PromptMessage, TrainingExample
from personal_ai.infrastructure.ollama_client import OllamaClient


def build_ollama_runner(
    *,
    ollama_client: OllamaClient,
    model: str,
    extra_instructions: tuple[str, ...],
    build_system_prompt: Callable[..., str],
    build_eval_prompt: Callable[[TrainingExample], str],
) -> Callable[[TrainingExample], str]:
    """Build a runner that evaluates examples through the local Ollama API."""
    system_prompt = build_system_prompt(
        extra_instructions=extra_instructions,
    )

    def _run(example: TrainingExample) -> str:
        return ollama_client.chat(
            model=model,
            messages=(
                PromptMessage(
                    role="system",
                    content=system_prompt,
                ),
                PromptMessage(role="user", content=build_eval_prompt(example)),
            ),
        )

    return _run


def build_local_model_runner(
    *,
    model_path_or_name: str,
    extra_instructions: tuple[str, ...],
    local_model_runner_factory: Callable[[str], Callable[[str, str], str]] | None,
    build_system_prompt: Callable[..., str],
    build_eval_prompt: Callable[[TrainingExample], str],
) -> tuple[Callable[[TrainingExample], str], Callable[[], None]]:
    """Build a runner for local fine-tuned models or adapters."""
    if local_model_runner_factory is not None:
        system_prompt = build_system_prompt(
            extra_instructions=extra_instructions,
        )
        local_runner = local_model_runner_factory(model_path_or_name)

        def _run_with_factory(example: TrainingExample) -> str:
            return local_runner(system_prompt, build_eval_prompt(example))

        return _run_with_factory, (lambda: None)

    from unsloth import FastLanguageModel
    import gc
    import torch

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path_or_name,
        max_seq_length=4096,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    system_prompt = build_system_prompt(
        extra_instructions=extra_instructions,
    )

    def _run(example: TrainingExample) -> str:
        prompt_tensor = tokenizer.apply_chat_template(
            (
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": build_eval_prompt(example)},
            ),
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(model.device)
        attention_mask = torch.ones_like(prompt_tensor)
        output = model.generate(
            input_ids=prompt_tensor,
            attention_mask=attention_mask,
            max_new_tokens=400,
            do_sample=False,
            use_cache=True,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )
        generated = output[0][prompt_tensor.shape[1]:]
        return tokenizer.decode(generated, skip_special_tokens=True)

    def _cleanup() -> None:
        nonlocal model, tokenizer
        del model
        del tokenizer
        gc.collect()
        torch.cuda.empty_cache()

    return _run, _cleanup
