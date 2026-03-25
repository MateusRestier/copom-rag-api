"""RAG configuration dataclass.

Mirrors the RAGConfig pattern from rag-framework/rag_framework/config/settings.py:
a @dataclass where each field defaults to an environment variable, so all
tuning parameters are controllable from .env without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CopomRAGConfig:
    """Configuration for the COPOM RAG service.

    All fields read from environment variables with safe defaults so
    the service starts without a .env file (useful for testing).
    """

    # ── Retrieval ────────────────────────────────────────────────────
    # Total chunks fetched from pgvector before reranking
    retrieval_top_k: int = field(
        default_factory=lambda: int(os.environ.get("RETRIEVAL_TOP_K", "10"))
    )
    # Chunks passed to the LLM after reranking (must be <= retrieval_top_k)
    context_top_k: int = field(
        default_factory=lambda: int(os.environ.get("CONTEXT_TOP_K", "5"))
    )

    # ── Reranking ────────────────────────────────────────────────────
    # If True, an LLM call ranks retrieved chunks by relevance before generation
    rerank_with_llm: bool = field(
        default_factory=lambda: os.environ.get("RERANK_WITH_LLM", "true").lower() == "true"
    )

    # ── LLM generation ──────────────────────────────────────────────
    temperature: float = field(
        default_factory=lambda: float(os.environ.get("LLM_TEMPERATURE", "0.3"))
    )
    max_output_tokens: int = field(
        default_factory=lambda: int(os.environ.get("MAX_OUTPUT_TOKENS", "2048"))
    )

    # ── Context window ───────────────────────────────────────────────
    # Approximate token budget for all context chunks combined.
    # Chunks are truncated to stay within this limit.
    max_context_tokens: int = field(
        default_factory=lambda: int(os.environ.get("MAX_CONTEXT_TOKENS", "6000"))
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval_top_k": self.retrieval_top_k,
            "context_top_k": self.context_top_k,
            "rerank_with_llm": self.rerank_with_llm,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "max_context_tokens": self.max_context_tokens,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CopomRAGConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# Singleton used by the API lifespan — import this in api/main.py
COPOM_CONFIG = CopomRAGConfig()
