"""Infrastructure layer for PersonalAI."""

from infrastructure.config.env_loader import default_env_file_path, load_env_file
from infrastructure.vault.frontmatter import parse_frontmatter
from infrastructure.hashed_embedding_provider import HashedEmbeddingProvider
from infrastructure.llm.ollama_client import OllamaClient
from infrastructure.llm.openai_responses_client import OpenAIResponsesClient
from infrastructure.history.repository import SQLiteQueryHistoryRepository
from infrastructure.llm.routing_model_client import RoutingModelClient
from infrastructure.vault.reader import VaultReader

__all__ = [
    "default_env_file_path",
    "HashedEmbeddingProvider",
    "OllamaClient",
    "OpenAIResponsesClient",
    "RoutingModelClient",
    "SQLiteQueryHistoryRepository",
    "VaultReader",
    "load_env_file",
    "parse_frontmatter",
]
