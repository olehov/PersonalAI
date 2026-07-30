"""Chat and request-routing pipeline subpackage."""

from application.chat.acceptance import (
    AcceptanceResult,
    assess_answer_quality,
    build_repair_messages,
)
from application.chat.follow_up import (
    FollowUpContext,
    build_follow_up_context,
    build_unfinished_recovery_instruction,
    find_follow_up_anchor,
    find_latest_assistant_answer,
    is_follow_up_prompt,
    looks_like_follow_up_with_history,
    looks_like_incomplete_answer,
)
from application.chat.generation import (
    build_critique_messages,
    build_refinement_messages,
    generate_answer_text,
)
from application.chat.history import (
    compact_history_content,
    merge_conversation_history,
    normalize_conversation_history,
)
from application.chat.model_options import (
    answer_generation_options,
    critique_generation_options,
    repair_generation_options,
    refinement_generation_options,
)
from application.chat.preprocessor import (
    PromptPreprocessResult,
    PromptPreprocessor,
)
from application.chat.query_mapping import normalize_knowledge_query
from application.chat.routing import (
    RequestRoutingService,
    WorkflowRouteDecision,
)
from application.chat.scope import (
    build_complexity_message,
    build_scoped_user_prompt,
    normalize_scope_question,
    validate_question,
)

__all__ = [
    "AcceptanceResult",
    "FollowUpContext",
    "PromptPreprocessResult",
    "PromptPreprocessor",
    "RequestRoutingService",
    "WorkflowRouteDecision",
    "answer_generation_options",
    "assess_answer_quality",
    "build_complexity_message",
    "build_critique_messages",
    "build_follow_up_context",
    "build_repair_messages",
    "build_refinement_messages",
    "build_scoped_user_prompt",
    "build_unfinished_recovery_instruction",
    "compact_history_content",
    "critique_generation_options",
    "find_follow_up_anchor",
    "find_latest_assistant_answer",
    "generate_answer_text",
    "is_follow_up_prompt",
    "looks_like_follow_up_with_history",
    "looks_like_incomplete_answer",
    "merge_conversation_history",
    "normalize_conversation_history",
    "normalize_knowledge_query",
    "normalize_scope_question",
    "refinement_generation_options",
    "repair_generation_options",
    "validate_question",
]
