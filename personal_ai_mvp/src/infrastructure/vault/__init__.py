"""Vault parsing and reading infrastructure."""

from infrastructure.vault.frontmatter import parse_frontmatter
from infrastructure.vault.reader import VaultReader

__all__ = [
    "parse_frontmatter",
    "VaultReader",
]
