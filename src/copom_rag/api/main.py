"""FastAPI application for the COPOM RAG API.

Endpoints:
    GET  /health      — liveness + dependency status
    GET  /documents   — list ingested documents
    POST /ask         — main RAG question-answering endpoint

Authentication:
    Optional X-API-Key header.  Set COPOM_API_KEY in .env to enable.
    Leave COPOM_API_KEY empty (default) to disable auth for local development.

Startup:
    All expensive resources (DB connection, provider initialization) are
    created once in the lifespan context manager, mirroring the pattern in
    rag-framework/api/main.py.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import date

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from copom_rag.api.models import (
    AskRequest,
    AskResponse,
    DocumentSummary,
    HealthResponse,
    SourceReference,
)
from copom_rag.config.settings import COPOM_CONFIG
from copom_rag.core.rag_service import CopomRAGService, QueryFilters
from copom_rag.prompts.loader import PromptLoader
from copom_rag.providers.factory import get_embedding_provider, get_llm_provider
from copom_rag.retrieval.postgres_retriever import PostgresRetriever

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")

# ──────────────────────────────────────────────────────────────────
#  Authentication
# ──────────────────────────────────────────────────────────────────
_API_KEY = os.environ.get("COPOM_API_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def _verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Dependency that enforces X-API-Key when COPOM_API_KEY is set."""
    if not _API_KEY:
        return  # auth disabled
    if api_key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key.",
        )


# ──────────────────────────────────────────────────────────────────
#  Application lifespan
# ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all resources on startup, clean up on shutdown."""
    logger.info("Starting COPOM RAG API…")

    embedding_provider = get_embedding_provider()
    llm_provider = get_llm_provider()

    dsn = os.environ.get("DATABASE_URL")
    retriever = PostgresRetriever(dsn=dsn, embedding_provider=embedding_provider)
    retriever.connect()

    prompt_loader = PromptLoader()

    app.state.service = CopomRAGService(
        retriever=retriever,
        llm_provider=llm_provider,
        config=COPOM_CONFIG,
        prompt_loader=prompt_loader,
    )
    app.state.retriever = retriever
    app.state.embedding_provider = type(embedding_provider).__name__
    app.state.llm_provider = type(llm_provider).__name__

    logger.info("COPOM RAG API ready.")
    yield

    retriever.close()
    logger.info("COPOM RAG API shut down.")


# ──────────────────────────────────────────────────────────────────
#  FastAPI app
# ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="COPOM RAG API",
    description="Question-answering API over COPOM meeting minutes and policy communications.",
    version="0.1.0",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    """Return service health status."""
    db_ok = app.state.retriever.is_healthy()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="ok" if db_ok else "error",
        embedding_provider=app.state.embedding_provider,
        llm_provider=app.state.llm_provider,
        message=None if db_ok else "Database connection lost.",
    )


@app.get("/documents", response_model=list[DocumentSummary], tags=["documents"])
async def list_documents(_: None = Depends(_verify_api_key)) -> list[DocumentSummary]:
    """List all ingested COPOM documents."""
    docs = app.state.retriever.list_documents()
    return [DocumentSummary(**d) for d in docs]


@app.post("/ask", response_model=AskResponse, tags=["rag"])
async def ask(
    request: AskRequest,
    _: None = Depends(_verify_api_key),
) -> AskResponse:
    """Answer a question about COPOM documents using RAG."""
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question must not be empty.")

    filters = QueryFilters(
        doc_type=request.doc_type,
        date_from=date.fromisoformat(request.date_from) if request.date_from else None,
        date_to=date.fromisoformat(request.date_to) if request.date_to else None,
    )

    try:
        result = app.state.service.answer(question=request.question, filters=filters)
    except Exception as exc:
        exc_str = str(exc)
        if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
            logger.warning("Gemini rate limit hit on /ask: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=(
                    "O limite diario de requisicoes da API de embeddings foi atingido. "
                    "O servico sera restabelecido automaticamente a meia-noite (UTC). "
                    "Tente novamente mais tarde."
                ),
            )
        if "database" in exc_str.lower() or "connection" in exc_str.lower() or "psycopg" in exc_str.lower():
            logger.exception("Database error on /ask: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Erro de conexao com o banco de dados. Tente novamente em alguns instantes.",
            )
        logger.exception("Unexpected error on /ask: %s", exc)
        raise HTTPException(status_code=500, detail="Erro interno ao gerar a resposta. Tente novamente.")

    return AskResponse(
        answer=result.answer,
        sources=[
            SourceReference(
                title=s.title,
                url=s.url,
                doc_type=s.doc_type,
                meeting_date=s.meeting_date,
                excerpt=s.excerpt,
            )
            for s in result.sources
        ],
        processing_time_seconds=result.processing_time_seconds,
        chunks_retrieved=result.chunks_retrieved,
        chunks_used=result.chunks_used,
    )
