"""Heuristic workflow router for backend auto-selection."""

from __future__ import annotations

from dataclasses import dataclass
import re

from personal_ai.application.query_mapping import normalize_knowledge_query


@dataclass(frozen=True, slots=True)
class WorkflowRouteDecision:
    """Routing decision for one incoming request."""

    workflow: str
    confidence: str
    reason: str
    reasoning_mode: str = "standard"
    derived_title: str | None = None
    derived_directory: str | None = None


class RequestRoutingService:
    """Classifies prompts into the most suitable workflow."""

    _AGENT_PATTERNS = (
        r"working inside my local project folder",
        r"act directly in the filesystem",
        r"compile and fix errors",
        r"keep going until (?:the project )?compiles",
        r"build the mandatory part",
        r"implement (?:the )?mandatory part",
        r"create (?:the )?folders?, headers?, source files?, and makefile",
        r"expected workflow:",
        r"output behavior:",
        r"\bscaffold\b",
        r"\bmakefile\b",
    )
    _IMPLEMENTATION_HINTS = (
        "implementation slice",
        "incremental slice",
        "scope implementation",
        "break the task into",
        "plan the first slice",
        "first slice",
        "code skeleton",
        "execution flow",
        "implement",
        "build",
    )
    _DRAFT_HINTS = (
        "write a note",
        "draft a note",
        "create a note",
        "generate a note",
        "запиши ноду",
        "напиши ноду",
        "створи нотатку",
        "створи ноду",
        "напиши нотатку",
        # Backward-compatible mojibake forms still seen in older fixtures.
        "Р·Р°РїРёС€Рё РЅРѕРґСѓ",
        "РЅР°РїРёС€Рё РЅРѕРґСѓ",
        "СЃС‚РІРѕСЂРё РЅРѕС‚Р°С‚РєСѓ",
        "СЃС‚РІРѕСЂРё РЅРѕРґСѓ",
        "РЅР°РїРёС€Рё РЅРѕС‚Р°С‚РєСѓ",
    )
    _ANALYZE_HINTS = (
        "analyze directory",
        "analyze this directory",
        "analyze knowledge slice",
        "what is missing from the graph",
        "inspect this directory",
        "проаналізуй директорію",
        "проаналізуй граф",
        # Backward-compatible mojibake forms still seen in older fixtures.
        "РїСЂРѕР°РЅР°Р»С–Р·СѓР№ РґРёСЂРµРєС‚РѕСЂС–СЋ",
        "РїСЂРѕР°РЅР°Р»С–Р·СѓР№ РіСЂР°С„",
    )
    _PATH_PATTERN = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+")

    def route_request(
        self,
        *,
        prompt: str,
        title: str = "",
        directory: str = "",
        target_dir: str = "",
    ) -> WorkflowRouteDecision:
        """Return the best workflow for the given request."""
        del target_dir
        normalized_prompt = normalize_knowledge_query(prompt)
        normalized = " ".join(normalized_prompt.strip().split()).casefold()
        explicit_directory = directory.strip()
        explicit_title = title.strip()

        if explicit_directory:
            return WorkflowRouteDecision(
                workflow="analyze",
                confidence="high",
                reason="A concrete directory was provided, so directory analysis is the best fit.",
                reasoning_mode="standard",
                derived_directory=explicit_directory,
            )

        agent_hits = sum(
            1 for pattern in self._AGENT_PATTERNS if re.search(pattern, normalized)
        )
        if agent_hits >= 2:
            return WorkflowRouteDecision(
                workflow="agent",
                confidence="high",
                reason="The request includes multiple project-scale execution signals, so agent runtime is the safest fit.",
                reasoning_mode="high",
            )

        inferred_directory = self._extract_directory_hint(normalized_prompt)
        if inferred_directory and (
            any(hint in normalized for hint in self._ANALYZE_HINTS)
            or normalized.startswith("analyze ")
        ):
            return WorkflowRouteDecision(
                workflow="analyze",
                confidence="medium",
                reason="The prompt asks for analysis and includes a directory-like path.",
                reasoning_mode="standard",
                derived_directory=inferred_directory,
            )

        implementation_hits = sum(
            1 for hint in self._IMPLEMENTATION_HINTS if hint in normalized
        )
        if implementation_hits >= 2:
            return WorkflowRouteDecision(
                workflow="implementation",
                confidence="medium",
                reason="The request is implementation-oriented but does not require the full agent runtime.",
                reasoning_mode="high",
            )

        if explicit_title or any(hint in normalized for hint in self._DRAFT_HINTS):
            return WorkflowRouteDecision(
                workflow="draft",
                confidence="high" if explicit_title else "medium",
                reason="The request looks like note authoring, so safe note drafting is the best fit.",
                reasoning_mode="standard",
                derived_title=explicit_title or self._derive_note_title(prompt),
            )

        return WorkflowRouteDecision(
            workflow="ask",
            confidence="medium",
            reason="Defaulting to grounded ask because no stronger workflow signal was detected.",
            reasoning_mode=self._derive_reasoning_mode(normalized_prompt),
        )

    def _derive_reasoning_mode(self, prompt: str) -> str:
        normalized = " ".join(prompt.strip().split()).casefold()
        if len(normalized) >= 220:
            return "high"
        high_reasoning_hints = (
            "analyze",
            "tradeoff",
            "compare",
            "best approach",
            "architecture",
            "design",
            "edge case",
            "debug",
            "root cause",
            "why does this fail",
        )
        if any(hint in normalized for hint in high_reasoning_hints):
            return "high"
        return "standard"

    def _derive_note_title(self, prompt: str) -> str:
        match = re.search(
            r"(?:write|draft|create|generate)\s+(?:a\s+)?note\s+(?:about|on)\s+(.+)",
            prompt,
            flags=re.IGNORECASE,
        )
        if match:
            return self._title_case_fragment(match.group(1))
        return self._title_case_fragment(prompt)

    def _extract_directory_hint(self, prompt: str) -> str | None:
        match = self._PATH_PATTERN.search(prompt.replace("\\", "/"))
        if not match:
            return None
        candidate = match.group(0).strip("./ ")
        if not candidate or "." in candidate.rsplit("/", maxsplit=1)[-1]:
            return None
        return candidate

    def _title_case_fragment(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip(" .:-")
        if not cleaned:
            return "Draft Note"
        words = cleaned.split(" ")
        compact = " ".join(words[:6])
        return " ".join(word[:1].upper() + word[1:] for word in compact.split())
