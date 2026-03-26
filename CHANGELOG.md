# Changelog

All notable changes to **copom-rag-api** will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [0.3.0] — 2026-03-26

### Fixed
- `POST /ask` now returns structured 503 responses instead of generic 500 errors:
  - Gemini 429 / `RESOURCE_EXHAUSTED` → 503 with a Portuguese message explaining the
    daily quota limit and expected reset time (midnight UTC).
  - Database connection errors → 503 with a connection error message.
  - Other unexpected errors → 500 with a generic Portuguese message.

### Added
- `DEPLOYMENT.md`: guide covering Render service configuration, environment variables,
  database password rotation, UptimeRobot keep-alive setup, and troubleshooting.

## [0.2.0] — 2026-03-25

### Fixed
- Inline citations now use `[1][2]` format (never `[1, 2]`).
- `MAX_OUTPUT_TOKENS` increased to 8192 to prevent truncated answers.

### Added
- Answer generation prompt updated to require numbered inline citations referencing
  context chunk indices — e.g. `"a taxa foi mantida em 14,75% a.a.[1]"`.

## [0.1.0] — 2026-03-25

### Added
- `EmbeddingProvider` and `LLMProvider` ABCs with registry-decorator factory for
  zero-code provider switching via `EMBEDDING_PROVIDER` / `LLM_PROVIDER` env vars.
- `GeminiEmbeddingProvider`: Google Gemini `gemini-embedding-001` via `google-genai` SDK,
  with `output_dimensionality=1536` — must match the model used during ingestion.
- `GeminiLLMProvider`: Google Gemini `gemini-2.5-flash` with JSON parsing and
  markdown fence stripping.
- `PostgresRetriever`: pgvector cosine search (`<=>` operator) with HNSW index,
  `doc_type` and date range SQL filters.
- `CopomRAGService`: linear RAG orchestrator (embed -> retrieve -> rerank -> generate).
- Optional LLM-based reranking controlled by `RERANK_WITH_LLM` env var.
- `CopomRAGConfig` dataclass with env-var defaults for all tuning parameters
  (`RETRIEVAL_TOP_K`, `CONTEXT_TOP_K`, `MAX_CONTEXT_TOKENS`, etc.).
- `PromptLoader`: YAML-overridable prompt templates with Python fallbacks.
- FastAPI application with lifespan resource management and three endpoints:
  - `GET /health` — liveness + provider info
  - `GET /documents` — list ingested documents
  - `POST /ask` — RAG question answering with source citations
- Optional `X-API-Key` authentication (enabled via `COPOM_API_KEY` env var).
- Docker Compose with `pgvector/pgvector:pg16` + API service + `service_healthy` dependency.
- Dockerfile for containerized deployment.
- README, CHANGELOG, TROUBLESHOOTING (all in English).
