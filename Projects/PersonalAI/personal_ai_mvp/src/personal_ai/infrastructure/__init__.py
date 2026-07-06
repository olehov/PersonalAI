"""Infrastructure layer for PersonalAI."""

from personal_ai.infrastructure.env_loader import default_env_file_path, load_env_file
from personal_ai.infrastructure.frontmatter import parse_frontmatter
from personal_ai.infrastructure.hashed_embedding_provider import HashedEmbeddingProvider
from personal_ai.infrastructure.ollama_client import OllamaClient
from personal_ai.infrastructure.query_history_repository import SQLiteQueryHistoryRepository
from personal_ai.infrastructure.vault_reader import VaultReader

__all__ = [
    "default_env_file_path",
    "HashedEmbeddingProvider",
    "OllamaClient",
    "SQLiteQueryHistoryRepository",
    "VaultReader",
    "load_env_file",
    "parse_frontmatter",
]
