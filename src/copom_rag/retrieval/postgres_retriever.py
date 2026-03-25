"""PostgreSQL + pgvector similarity search for the COPOM RAG API.

Uses the `<=>` cosine distance operator with the HNSW index created by
copom-vector-pipeline.  Metadata filters (doc_type, date range) are
translated to SQL WHERE clauses.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    """A single retrieved chunk with its document metadata."""
    chunk_id: int
    document_id: int
    chunk_text: str
    title: str
    url: str
    doc_type: str
    meeting_date: date | None
    similarity: float          # 1 - cosine_distance, range [0, 1]
    chunk_index: int


class PostgresRetriever:
    """Retrieves semantically similar chunks from PostgreSQL+pgvector.

    Args:
        dsn:                PostgreSQL connection string.
        embedding_provider: Provider used to embed the query.
    """

    def __init__(self, dsn: str | None, embedding_provider) -> None:
        self._dsn = dsn or os.environ.get("DATABASE_URL")
        if not self._dsn:
            raise EnvironmentError("DATABASE_URL environment variable is not set.")
        self._embedding = embedding_provider
        self._conn = None

    # ──────────────────────────────────────────────────────────────────
    #  Connection lifecycle
    # ──────────────────────────────────────────────────────────────────

    def connect(self) -> None:
        import psycopg2  # type: ignore
        from pgvector.psycopg2 import register_vector  # type: ignore

        self._conn = psycopg2.connect(self._dsn)
        register_vector(self._conn)
        logger.info("PostgresRetriever connected.")

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    # ──────────────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ChunkResult]:
        """Search for the most similar chunks to `query`.

        Args:
            query:     Natural language question.
            top_k:     Number of results to return.
            doc_type:  Filter by document type ('ata', 'comunicado').
                       If None or 'all', no filter is applied.
            date_from: Only include documents on or after this date.
            date_to:   Only include documents on or before this date.

        Returns:
            List of ChunkResult ordered by descending similarity.
        """
        import numpy as np

        embedding = self._embedding.embed_text(query)
        vec = np.array(embedding, dtype=np.float32)

        # Build WHERE clause dynamically
        conditions = []
        params: list = [vec]

        if doc_type and doc_type != "all":
            conditions.append("d.doc_type = %s")
            params.append(doc_type)

        if date_from:
            conditions.append("d.meeting_date >= %s")
            params.append(date_from)

        if date_to:
            conditions.append("d.meeting_date <= %s")
            params.append(date_to)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # pgvector cosine distance: <=> returns distance (0 = identical).
        # similarity = 1 - distance.
        sql = f"""
            SELECT
                c.id            AS chunk_id,
                c.document_id,
                c.chunk_text,
                c.chunk_index,
                d.title,
                d.url,
                d.doc_type,
                d.meeting_date,
                1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            {where_clause}
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s;
        """
        # Add vec again for ORDER BY and top_k for LIMIT
        params.extend([vec, top_k])

        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        return [
            ChunkResult(
                chunk_id=row[0],
                document_id=row[1],
                chunk_text=row[2],
                chunk_index=row[3],
                title=row[4],
                url=row[5],
                doc_type=row[6],
                meeting_date=row[7],
                similarity=float(row[8]),
            )
            for row in rows
        ]

    def list_documents(self, limit: int = 200) -> list[dict]:
        """Return a list of ingested documents (for the /documents endpoint)."""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, doc_type, meeting_date, url
                FROM documents
                ORDER BY meeting_date DESC NULLS LAST
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [
            {"id": r[0], "title": r[1], "doc_type": r[2],
             "meeting_date": r[3].isoformat() if r[3] else None, "url": r[4]}
            for r in rows
        ]

    def is_healthy(self) -> bool:
        """Return True if the database connection is alive."""
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1;")
            return True
        except Exception:
            return False
