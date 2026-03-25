"""Provider registry and factory for embedding and LLM providers.

Uses the same registry-decorator pattern as copom-vector-pipeline so that
adding a new provider only requires creating a new module and decorating
the class — this factory file is never edited.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from copom_rag.providers.base import EmbeddingProvider, LLMProvider

_EMBEDDING_REGISTRY: dict[str, type["EmbeddingProvider"]] = {}
_LLM_REGISTRY: dict[str, type["LLMProvider"]] = {}


def register_embedding_provider(name: str):
    """Class decorator to register an EmbeddingProvider implementation."""
    def decorator(cls):
        _EMBEDDING_REGISTRY[name] = cls
        return cls
    return decorator


def register_llm_provider(name: str):
    """Class decorator to register an LLMProvider implementation."""
    def decorator(cls):
        _LLM_REGISTRY[name] = cls
        return cls
    return decorator


def _load_providers() -> None:
    """Import all provider modules so their decorators execute."""
    # Add new provider imports here — one line per provider file.
    from copom_rag.providers import gemini  # noqa: F401


def get_embedding_provider(provider_name: str | None = None) -> "EmbeddingProvider":
    """Instantiate and return the embedding provider selected by env var.

    Args:
        provider_name: Override the provider name.  If None, reads
            EMBEDDING_PROVIDER from the environment (default: "gemini").
            Must match what copom-vector-pipeline used for ingestion.
    """
    _load_providers()
    name = provider_name or os.environ.get("EMBEDDING_PROVIDER", "gemini")
    if name not in _EMBEDDING_REGISTRY:
        available = list(_EMBEDDING_REGISTRY.keys())
        raise ValueError(
            f"Unknown embedding provider '{name}'. "
            f"Available: {available}. "
            f"Check your EMBEDDING_PROVIDER environment variable."
        )
    return _EMBEDDING_REGISTRY[name]()


def get_llm_provider(provider_name: str | None = None) -> "LLMProvider":
    """Instantiate and return the LLM provider selected by env var.

    Args:
        provider_name: Override the provider name.  If None, reads
            LLM_PROVIDER from the environment (default: "gemini").
    """
    _load_providers()
    name = provider_name or os.environ.get("LLM_PROVIDER", "gemini")
    if name not in _LLM_REGISTRY:
        available = list(_LLM_REGISTRY.keys())
        raise ValueError(
            f"Unknown LLM provider '{name}'. "
            f"Available: {available}. "
            f"Check your LLM_PROVIDER environment variable."
        )
    return _LLM_REGISTRY[name]()
