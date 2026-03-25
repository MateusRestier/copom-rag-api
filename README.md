# copom-rag-api

REST API for question-answering over COPOM (Comitê de Política Monetária) documents stored in PostgreSQL+pgvector.

Retrieves semantically similar chunks from the database, optionally reranks them with an LLM, and generates a grounded answer with source references.

---

## Architecture

```
POST /ask
  │
  ├── EmbeddingProvider.embed_text(question)
  │        (Gemini / pluggable)
  │
  ├── PostgresRetriever.search()    ← pgvector HNSW cosine search
  │
  ├── CopomRAGService._rerank()     ← optional LLM reranking
  │
  ├── CopomRAGService._build_context()
  │
  └── LLMProvider.generate(prompt + context)
           (Gemini / pluggable)
```

All collaborators are dependency-injected into `CopomRAGService`. Swapping any provider (embedding, LLM) requires only changing an env var.

---

## Requirements

- Python 3.11+
- Docker (for PostgreSQL + pgvector)
- Data ingested by [copom-vector-pipeline](https://github.com/<org>/copom-vector-pipeline)
- A Google Gemini API key (or another configured provider)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/<org>/copom-rag-api.git
cd copom-rag-api

# 2. Configure environment variables
cp .env.example .env
# Edit .env: set GEMINI_API_KEY and DATABASE_URL

# 3a. Run with Docker Compose (includes PostgreSQL)
docker compose up -d

# 3b. OR run locally (assumes PostgreSQL is already running)
pip install -e .
uvicorn copom_rag.api.main:app --reload
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

---

## API Endpoints

### `GET /health`
Returns service health status including database connectivity and provider names.

### `GET /documents`
Lists all ingested COPOM documents (title, type, date, URL).

### `POST /ask`
Main RAG endpoint.

**Request:**
```json
{
  "question": "Qual foi a decisão sobre a taxa Selic na reunião de março de 2024?",
  "doc_type": "ata",
  "date_from": "2024-01-01",
  "date_to": "2024-12-31"
}
```

**Response:**
```json
{
  "answer": "Na reunião de março de 2024, o Copom decidiu...",
  "sources": [
    {
      "title": "Ata da 261ª Reunião do Copom",
      "url": "https://www.bcb.gov.br/...",
      "doc_type": "ata",
      "meeting_date": "2024-03-20",
      "excerpt": "O Comitê decidiu, por unanimidade, reduzir a taxa Selic..."
    }
  ],
  "processing_time_seconds": 1.84,
  "chunks_retrieved": 10,
  "chunks_used": 3
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `EMBEDDING_PROVIDER` | No | `gemini` | Must match what copom-vector-pipeline used. |
| `LLM_PROVIDER` | No | `gemini` | LLM provider for generation and reranking. |
| `GEMINI_API_KEY` | Yes | — | Google AI API key. |
| `GEMINI_EMBEDDING_MODEL` | No | `models/text-embedding-004` | Must match ingestion model. |
| `GEMINI_LLM_MODEL` | No | `gemini-1.5-flash` | Gemini model for answer generation. |
| `DATABASE_URL` | Yes | — | PostgreSQL DSN. |
| `RETRIEVAL_TOP_K` | No | `10` | Chunks fetched from pgvector. |
| `CONTEXT_TOP_K` | No | `5` | Chunks passed to the LLM after reranking. |
| `RERANK_WITH_LLM` | No | `true` | Enable LLM-based chunk reranking. |
| `LLM_TEMPERATURE` | No | `0.3` | LLM temperature (lower = more factual). |
| `MAX_OUTPUT_TOKENS` | No | `2048` | Max tokens in LLM response. |
| `MAX_CONTEXT_TOKENS` | No | `6000` | Approximate token budget for context chunks. |
| `COPOM_API_KEY` | No | `` | Set to enable X-API-Key authentication. |
| `COPOM_PROMPTS_FILE` | No | `` | Path to YAML file with custom prompt overrides. |

---

## Customizing Prompts

Edit `prompts/answer_generation.yaml` and set `COPOM_PROMPTS_FILE=prompts/answer_generation.yaml` in `.env`. Only the keys you uncomment are overridden; the rest use Python defaults.

---

## Adding a New Provider

1. Create `src/copom_rag/providers/my_provider.py`.
2. Subclass `EmbeddingProvider` and/or `LLMProvider`.
3. Decorate with `@register_embedding_provider("name")` and/or `@register_llm_provider("name")`.
4. Add an import in `providers/factory.py` inside `_load_providers()`.
5. Set `EMBEDDING_PROVIDER=name` and/or `LLM_PROVIDER=name` in `.env`.

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/
uvicorn copom_rag.api.main:app --reload
```
