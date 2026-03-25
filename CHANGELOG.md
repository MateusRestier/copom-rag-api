# Changelog

All notable changes to **copom-rag-api** will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [0.1.0] — 2026-03-25

### Added
- Initial project structure with full package scaffolding.
- `EmbeddingProvider` and `LLMProvider` ABCs with registry-decorator factory.
- `GeminiEmbeddingProvider`: Google Gemini `text-embedding-004` (768 dims).
- `GeminiLLMProvider`: Google Gemini `gemini-1.5-flash` with JSON parsing.
- `PostgresRetriever`: pgvector cosine search (`<=>` operator) with HNSW index, doc_type and date range filters.
- `CopomRAGService`: linear RAG orchestrator (embed → retrieve → rerank → generate).
- Optional LLM-based reranking via `RERANK_WITH_LLM` env var.
- `CopomRAGConfig` dataclass with env-var defaults for all tuning parameters.
- `PromptLoader`: YAML-overridable prompt templates with Python fallbacks.
- FastAPI application with `/health`, `/documents`, `/ask` endpoints.
- Optional `X-API-Key` authentication (enabled via `COPOM_API_KEY` env var).
- Docker Compose with `pgvector/pgvector:pg16` + API service + `service_healthy` dependency.
- Dockerfile for containerized deployment.
- README, CHANGELOG, TROUBLESHOOTING (all in English).
