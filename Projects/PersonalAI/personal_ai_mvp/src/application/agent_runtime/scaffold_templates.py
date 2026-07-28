"""Reusable fallback scaffold templates for the agent runtime."""

from __future__ import annotations

from pathlib import Path


def scaffold_path(scaffold_root: str, *parts: str) -> str:
    """Join repository-relative scaffold paths under the configured root."""
    root = Path(scaffold_root)
    if not parts:
        return root.as_posix()
    return root.joinpath(*parts).as_posix()


def fallback_scaffold_file_content(target: str) -> str:
    """Return a compact fallback scaffold file when model output is unusable."""
    target_name = Path(target).name
    suffix = Path(target).suffix.casefold()
    if target_name == "Makefile":
        return "\n".join(
            [
                "NAME := scaffold_app",
                "CC := cc",
                "CFLAGS := -Wall -Wextra -Werror",
                "",
                "SRC := src/main.c",
                "OBJ := $(SRC:.c=.o)",
                "",
                "all: $(NAME)",
                "",
                "$(NAME): $(OBJ)",
                "\t$(CC) $(CFLAGS) $(OBJ) -o $(NAME)",
                "",
                "clean:",
                "\trm -f $(OBJ)",
                "",
                "fclean: clean",
                "\trm -f $(NAME)",
                "",
                "re: fclean all",
            ]
        )
    if suffix == ".py":
        stem = Path(target).stem
        if "helper" in stem.casefold():
            return "\n".join(
                [
                    '"""Generated helper scaffold."""',
                    "",
                    "from __future__ import annotations",
                    "",
                    "",
                    "def normalize_text(value: str) -> str:",
                    '    """Return a trimmed single-line representation."""',
                    '    return " ".join(value.strip().split())',
                ]
            )
        return "\n".join(
            [
                '"""Generated scaffold file."""',
                "",
                "from __future__ import annotations",
                "",
                "",
                "def main() -> int:",
                '    """Return a success code for the scaffold entrypoint."""',
                "    return 0",
                "",
                "",
                'if __name__ == "__main__":',
                "    raise SystemExit(main())",
            ]
        )
    if suffix in {".js", ".mjs"}:
        return "\n".join(
            [
                "/** Generated scaffold file. */",
                "",
                "export function main() {",
                "  return 0;",
                "}",
            ]
        )
    if suffix in {".c", ".h"}:
        if suffix == ".h":
            return "\n".join(
                [
                    "/* Generated scaffold header. */",
                    "#ifndef GENERATED_SCAFFOLD_H",
                    "#define GENERATED_SCAFFOLD_H",
                    "",
                    "int generated_scaffold(void);",
                    "",
                    "#endif",
                ]
            )
        return "\n".join(
            [
                "/* Generated scaffold file. */",
                "",
                "int generated_scaffold(void)",
                "{",
                "    return 0;",
                "}",
            ]
        )
    return "\n".join(
        [
            "# Generated Scaffold",
            "",
            "created_by=safe_agent_runtime",
            f"target={target}",
        ]
    )


def fallback_scaffold_tree_manifest(
    request_text: str,
    *,
    scaffold_root: str,
) -> tuple[list[str], list[dict[str, str]]]:
    """Return a realistic fallback scaffold tree for common project shapes."""
    lowered = request_text.casefold()
    if "minishell" in lowered or " shell" in lowered or lowered.endswith("shell"):
        return (
            [
                scaffold_path(scaffold_root, "include"),
                scaffold_path(scaffold_root, "src"),
                scaffold_path(scaffold_root, "src", "builtins"),
                scaffold_path(scaffold_root, "src", "executor"),
                scaffold_path(scaffold_root, "src", "lexer"),
                scaffold_path(scaffold_root, "src", "parser"),
                scaffold_path(scaffold_root, "src", "signals"),
            ],
            [
                {"path": scaffold_path(scaffold_root, "Makefile"), "purpose": "Build the minishell target from modular C sources."},
                {"path": scaffold_path(scaffold_root, "include", "minishell.h"), "purpose": "Shared core shell structures and lifecycle prototypes."},
                {"path": scaffold_path(scaffold_root, "include", "parser.h"), "purpose": "Parser and token interfaces."},
                {"path": scaffold_path(scaffold_root, "include", "executor.h"), "purpose": "Pipeline and command execution interfaces."},
                {"path": scaffold_path(scaffold_root, "include", "builtins.h"), "purpose": "Builtin dispatch interfaces."},
                {"path": scaffold_path(scaffold_root, "include", "signals.h"), "purpose": "Interactive signal handling interfaces."},
                {"path": scaffold_path(scaffold_root, "src", "main.c"), "purpose": "Program entrypoint and shell loop wiring."},
                {"path": scaffold_path(scaffold_root, "src", "shell.c"), "purpose": "Read-eval loop and high-level orchestration."},
                {"path": scaffold_path(scaffold_root, "src", "parser", "lexer.c"), "purpose": "Token scanning for shell input."},
                {"path": scaffold_path(scaffold_root, "src", "parser", "parser.c"), "purpose": "Command and pipeline parsing."},
                {"path": scaffold_path(scaffold_root, "src", "executor", "exec.c"), "purpose": "PATH resolution and execve-based external execution."},
                {"path": scaffold_path(scaffold_root, "src", "executor", "redirections.c"), "purpose": "Input/output redirection helpers."},
                {"path": scaffold_path(scaffold_root, "src", "executor", "pipes.c"), "purpose": "Pipeline creation and fd wiring."},
                {"path": scaffold_path(scaffold_root, "src", "builtins", "builtins.c"), "purpose": "Builtin dispatch table and implementations."},
                {"path": scaffold_path(scaffold_root, "src", "signals", "interactive.c"), "purpose": "Interactive ctrl-C and ctrl-\\ behavior."},
            ],
        )
    if any(token in lowered for token in ("python", "pyproject", "cli")):
        return (
            [
                scaffold_path(scaffold_root, "src"),
                scaffold_path(scaffold_root, "src", "app"),
                scaffold_path(scaffold_root, "tests"),
            ],
            [
                {"path": scaffold_path(scaffold_root, "pyproject.toml"), "purpose": "Python project metadata and test configuration."},
                {"path": scaffold_path(scaffold_root, "src", "app", "__init__.py"), "purpose": "Package marker."},
                {"path": scaffold_path(scaffold_root, "src", "app", "main.py"), "purpose": "CLI or application entrypoint."},
                {"path": scaffold_path(scaffold_root, "src", "app", "helpers.py"), "purpose": "Reusable helper functions for the first slice."},
                {"path": scaffold_path(scaffold_root, "tests", "test_basic.py"), "purpose": "Minimal regression test scaffold."},
            ],
        )
    if any(token in lowered for token in ("javascript", "typescript", "node", "react", "vite", "frontend")):
        return (
            [
                scaffold_path(scaffold_root, "src"),
                scaffold_path(scaffold_root, "public"),
            ],
            [
                {"path": scaffold_path(scaffold_root, "package.json"), "purpose": "Project scripts and package metadata."},
                {"path": scaffold_path(scaffold_root, "src", "main.js"), "purpose": "Application bootstrap entrypoint."},
                {"path": scaffold_path(scaffold_root, "src", "helpers.js"), "purpose": "Reusable helper module for the first slice."},
            ],
        )
    return (
        [scaffold_path(scaffold_root, "src")],
        [
            {"path": scaffold_path(scaffold_root, "src", "main.txt"), "purpose": "Starter scaffold artifact for the requested project."},
        ],
    )
