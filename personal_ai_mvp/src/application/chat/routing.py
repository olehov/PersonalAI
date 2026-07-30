"""Heuristic workflow router for backend auto-selection."""

from __future__ import annotations

from dataclasses import dataclass
import re

from application.chat.follow_up import (
    find_follow_up_anchor,
    is_follow_up_prompt,
    looks_like_follow_up_with_history,
)
from application.chat.query_mapping import normalize_knowledge_query
from domain.models import PromptMessage


@dataclass(frozen=True, slots=True)
class WorkflowRouteDecision:
    """Routing decision for one incoming request."""

    workflow: str
    confidence: str
    reason: str
    reasoning_mode: str = "standard"
    derived_title: str | None = None
    derived_directory: str | None = None
    web_search_required: bool = False
    web_search_reason: str | None = None


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
        "generate code",
        "write code",
        "write a program",
        "finish the code",
        "complete the code",
        "implement",
        "build",
    )
    _DRAFT_HINTS = (
        "write a note",
        "draft a note",
        "create a note",
        "generate a note",
    )
    _ANALYZE_HINTS = (
        "analyze directory",
        "analyze this directory",
        "analyze knowledge slice",
        "what is missing from the graph",
        "inspect this directory",
    )
    _PATH_PATTERN = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+")
    _WEB_SEARCH_PATTERNS = (
        r"\bsearch\b",
        r"\blook up\b",
        r"\bfind online\b",
        r"\bonline\b",
        r"\bweb\b",
        r"\binternet\b",
        r"\blatest\b",
        r"\bmost recent\b",
        r"\bcurrent\b",
        r"\btoday\b",
        r"\brecent\b",
        r"\bprice\b",
        r"\bpricing\b",
        r"\bversion\b",
        r"\brelease notes\b",
        r"\bdocumentation\b",
        r"\bdocs\b",
        r"\bapi reference\b",
    )

    def route_request(
        self,
        *,
        prompt: str,
        conversation_history: tuple[PromptMessage, ...] = (),
        title: str = "",
        directory: str = "",
        target_dir: str = "",
    ) -> WorkflowRouteDecision:
        """Return the best workflow for the given request."""
        normalized_prompt = normalize_knowledge_query(prompt)
        normalized = " ".join(normalized_prompt.strip().split()).casefold()
        explicit_directory = directory.strip()
        explicit_title = title.strip()
        web_search_required, web_search_reason = self._detect_web_search_need(normalized)

        if conversation_history and self._is_follow_up_prompt_with_history(
            prompt=prompt,
            normalized_prompt=normalized,
            conversation_history=conversation_history,
        ):
            anchored_prompt = self._find_follow_up_anchor(conversation_history)
            if anchored_prompt is not None:
                anchored_decision = self.route_request(
                    prompt=anchored_prompt,
                    conversation_history=(),
                    title=title,
                    directory=directory,
                    target_dir=target_dir,
                )
                return WorkflowRouteDecision(
                    workflow=anchored_decision.workflow,
                    confidence=anchored_decision.confidence,
                    reason=(
                        "The request looks like a follow-up, so routing is locked to the "
                        f"most recent substantive task: {anchored_decision.reason}"
                    ),
                    reasoning_mode=anchored_decision.reasoning_mode,
                    derived_title=anchored_decision.derived_title,
                    derived_directory=anchored_decision.derived_directory,
                    web_search_required=web_search_required or anchored_decision.web_search_required,
                    web_search_reason=web_search_reason or anchored_decision.web_search_reason,
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
                web_search_required=web_search_required,
                web_search_reason=web_search_reason,
            )

        if explicit_directory:
            return WorkflowRouteDecision(
                workflow="analyze",
                confidence="high",
                reason="A concrete directory was provided, so directory analysis is the best fit.",
                reasoning_mode="standard",
                derived_directory=explicit_directory,
                web_search_required=False,
                web_search_reason=None,
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
                web_search_required=False,
                web_search_reason=None,
            )

        if self._looks_like_code_generation_request(normalized):
            return WorkflowRouteDecision(
                workflow="implementation",
                confidence="high",
                reason="The request explicitly asks for code generation, so implementation scoping is the best fit.",
                reasoning_mode="high",
                web_search_required=web_search_required,
                web_search_reason=web_search_reason,
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
                web_search_required=web_search_required,
                web_search_reason=web_search_reason,
            )

        if any(hint in normalized for hint in self._DRAFT_HINTS):
            return WorkflowRouteDecision(
                workflow="draft",
                confidence="medium",
                reason="The request looks like note authoring, so safe note drafting is the best fit.",
                reasoning_mode="standard",
                derived_title=explicit_title or self._derive_note_title(prompt),
                web_search_required=False,
                web_search_reason=None,
            )

        if explicit_title:
            return WorkflowRouteDecision(
                workflow="draft",
                confidence="medium",
                reason="A note title was provided and no stronger workflow signal was detected.",
                reasoning_mode="standard",
                derived_title=explicit_title,
                web_search_required=False,
                web_search_reason=None,
            )

        return WorkflowRouteDecision(
            workflow="ask",
            confidence="medium",
            reason="Defaulting to grounded ask because no stronger workflow signal was detected.",
            reasoning_mode=self._derive_reasoning_mode(normalized_prompt),
            web_search_required=web_search_required,
            web_search_reason=web_search_reason,
        )

    def _detect_web_search_need(self, normalized_prompt: str) -> tuple[bool, str | None]:
        for pattern in self._WEB_SEARCH_PATTERNS:
            if re.search(pattern, normalized_prompt):
                return (
                    True,
                    "The prompt asks for fresh or external information, so web grounding is recommended.",
                )
        return False, None

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

    def _looks_like_code_generation_request(self, normalized_prompt: str) -> bool:
        code_hints = (
            " code ",
            " program ",
            " function ",
            " module ",
            " source file",
            " header ",
            " makefile",
            " implementation ",
            " skeleton ",
            " snippet ",
            " modules",
            " execution flow",
            " edge cases",
        )
        action_hints = (
            "generate",
            "write",
            "create",
            "implement",
            "build",
        )
        padded = f" {normalized_prompt} "
        has_code_hint = any(hint in padded for hint in code_hints)
        has_action_hint = any(hint in normalized_prompt for hint in action_hints)
        return has_code_hint and has_action_hint

    def _is_follow_up_prompt(self, normalized_prompt: str) -> bool:
        return is_follow_up_prompt(normalized_prompt)

    def _is_follow_up_prompt_with_history(
        self,
        *,
        prompt: str,
        normalized_prompt: str,
        conversation_history: tuple[PromptMessage, ...],
    ) -> bool:
        if is_follow_up_prompt(normalized_prompt):
            return True
        return looks_like_follow_up_with_history(prompt, conversation_history)

    def _find_follow_up_anchor(
        self,
        conversation_history: tuple[PromptMessage, ...],
    ) -> str | None:
        return find_follow_up_anchor(conversation_history)
