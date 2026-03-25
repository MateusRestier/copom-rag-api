"""Pydantic request and response models for the COPOM RAG API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Request body for POST /ask."""

    question: str = Field(..., min_length=1, description="Question about COPOM documents.")
    doc_type: Literal["ata", "comunicado", "all"] | None = Field(
        default="all",
        description="Filter by document type. 'all' searches across both types.",
    )
    date_from: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Only consider documents from this date (YYYY-MM-DD).",
    )
    date_to: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Only consider documents up to this date (YYYY-MM-DD).",
    )


class SourceReference(BaseModel):
    """A source document chunk cited in the answer."""

    title: str
    url: str
    doc_type: str
    meeting_date: str | None
    excerpt: str = Field(..., description="First ~300 characters of the relevant chunk.")


class AskResponse(BaseModel):
    """Response body for POST /ask."""

    answer: str
    sources: list[SourceReference]
    processing_time_seconds: float
    chunks_retrieved: int
    chunks_used: int


class DocumentSummary(BaseModel):
    """A single document entry returned by GET /documents."""

    id: int
    title: str
    doc_type: str
    meeting_date: str | None
    url: str


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: Literal["ok", "degraded"]
    database: Literal["ok", "error"]
    embedding_provider: str
    llm_provider: str
    message: str | None = None
