"""CopomRAGService — RAG orchestrator.

Linear pipeline: embed question → retrieve chunks → (optional) LLM rerank
→ build context → generate answer.

No LangGraph is used here because the COPOM QA flow is linear (no
conditional branches or retries at the graph level).  If the workflow
needs to grow into a multi-step agentic pipeline, LangGraph can be
introduced by wrapping these steps as graph nodes.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date

from copom_rag.config.settings import CopomRAGConfig
from copom_rag.prompts.loader import PromptLoader
from copom_rag.providers.base import LLMProvider
from copom_rag.retrieval.postgres_retriever import ChunkResult, PostgresRetriever

logger = logging.getLogger(__name__)


@dataclass
class QueryFilters:
    """Optional filters applied to the vector search."""
    doc_type: str | None = None          # 'ata', 'comunicado', or 'all' / None
    date_from: date | None = None
    date_to: date | None = None


@dataclass
class SourceReference:
    """Metadata about a source chunk used in the answer."""
    title: str
    url: str
    doc_type: str
    meeting_date: str | None
    excerpt: str                         # first ~300 chars of chunk_text


@dataclass
class RAGResult:
    """Full result returned by CopomRAGService.answer()."""
    answer: str
    sources: list[SourceReference]
    processing_time_seconds: float
    chunks_retrieved: int
    chunks_used: int


class CopomRAGService:
    """Answers questions about COPOM documents using RAG.

    Args:
        retriever:       PostgresRetriever (must already be connected).
        llm_provider:    LLMProvider for answer generation (and reranking).
        config:          CopomRAGConfig instance.
        prompt_loader:   PromptLoader instance.
    """

    def __init__(
        self,
        retriever: PostgresRetriever,
        llm_provider: LLMProvider,
        config: CopomRAGConfig,
        prompt_loader: PromptLoader,
    ) -> None:
        self._retriever = retriever
        self._llm = llm_provider
        self._config = config
        self._prompts = prompt_loader

    # ──────────────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────────────

    def answer(self, question: str, filters: QueryFilters | None = None) -> RAGResult:
        """Generate an answer for the given question.

        Args:
            question: Natural language question about COPOM documents.
            filters:  Optional metadata filters (doc_type, date range).

        Returns:
            RAGResult with the generated answer, source references, and timing.
        """
        t0 = time.perf_counter()
        filters = filters or QueryFilters()

        # 1. Retrieve top-k chunks from pgvector
        chunks = self._retriever.search(
            query=question,
            top_k=self._config.retrieval_top_k,
            doc_type=filters.doc_type,
            date_from=filters.date_from,
            date_to=filters.date_to,
        )
        logger.info("Retrieved %d chunks for question: %.80s", len(chunks), question)

        if not chunks:
            return RAGResult(
                answer="Não encontrei documentos relevantes para responder a esta pergunta.",
                sources=[],
                processing_time_seconds=time.perf_counter() - t0,
                chunks_retrieved=0,
                chunks_used=0,
            )

        # 2. Optional LLM reranking
        if self._config.rerank_with_llm and len(chunks) > 1:
            chunks = self._rerank(question, chunks)

        # 3. Select top context_top_k chunks and build context string
        context_chunks = chunks[: self._config.context_top_k]
        context = self._build_context(context_chunks)

        # 4. Generate answer
        system = self._prompts.get("answer_generation_system")
        prompt = self._prompts.render(
            "answer_generation_template",
            question=question,
            context=context,
        )
        answer = self._llm.generate(prompt, system=system)

        sources = [self._to_source_ref(c) for c in context_chunks]
        elapsed = time.perf_counter() - t0
        logger.info("Answer generated in %.2fs (%d sources).", elapsed, len(sources))

        return RAGResult(
            answer=answer,
            sources=sources,
            processing_time_seconds=round(elapsed, 3),
            chunks_retrieved=len(chunks),
            chunks_used=len(context_chunks),
        )

    # ──────────────────────────────────────────────────────────────────
    #  Internal helpers
    # ──────────────────────────────────────────────────────────────────

    def _rerank(self, question: str, chunks: list[ChunkResult]) -> list[ChunkResult]:
        """Ask the LLM to reorder chunks by relevance. Falls back gracefully."""
        try:
            chunks_text = "\n\n".join(
                f"[{i}] {c.chunk_text[:400]}" for i, c in enumerate(chunks)
            )
            prompt = self._prompts.render(
                "reranking_template",
                question=question,
                chunks=chunks_text,
            )
            system = self._prompts.get("reranking_system")
            result = self._llm.generate_json(prompt, system=system)
            ranking = result.get("ranking", [])

            # Validate and apply ranking
            valid_indices = [i for i in ranking if isinstance(i, int) and 0 <= i < len(chunks)]
            seen = set()
            ordered: list[ChunkResult] = []
            for i in valid_indices:
                if i not in seen:
                    ordered.append(chunks[i])
                    seen.add(i)
            # Append any chunks not mentioned in the ranking at the end
            for i, c in enumerate(chunks):
                if i not in seen:
                    ordered.append(c)
            return ordered
        except Exception as exc:
            logger.warning("Reranking failed (%s) — using original order.", exc)
            return chunks

    def _build_context(self, chunks: list[ChunkResult]) -> str:
        """Assemble chunks into a single context string within the token budget."""
        parts = []
        approx_tokens = 0
        budget = self._config.max_context_tokens

        for chunk in chunks:
            # Rough estimate: 1 token ≈ 4 chars
            chunk_tokens = max(1, len(chunk.chunk_text) // 4)
            if approx_tokens + chunk_tokens > budget:
                break
            date_str = chunk.meeting_date.isoformat() if chunk.meeting_date else "data desconhecida"
            parts.append(
                f"### {chunk.title} ({chunk.doc_type}, {date_str})\n{chunk.chunk_text}"
            )
            approx_tokens += chunk_tokens

        return "\n\n".join(parts)

    @staticmethod
    def _to_source_ref(chunk: ChunkResult) -> SourceReference:
        return SourceReference(
            title=chunk.title,
            url=chunk.url,
            doc_type=chunk.doc_type,
            meeting_date=chunk.meeting_date.isoformat() if chunk.meeting_date else None,
            excerpt=chunk.chunk_text[:300],
        )
