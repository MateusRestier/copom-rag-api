# Troubleshooting

Common issues and solutions for **copom-rag-api**.

---

## Database connection errors

### `EnvironmentError: DATABASE_URL environment variable is not set`

**Fix**:
```bash
cp .env.example .env
# Set DATABASE_URL=postgresql://copom:copom@localhost:5432/copom_rag
```

---

### `psycopg2.OperationalError: could not connect to server`

**Cause**: PostgreSQL is not running or not yet healthy.

**Fix**:
```bash
docker compose up -d
docker compose ps  # wait for postgres to be healthy
```

---

### `relation "chunks" does not exist`

**Cause**: The database schema was not applied.  Run copom-vector-pipeline first, or apply the schema manually from that repo:
```bash
docker exec -i copom_pgvector psql -U copom -d copom_rag < path/to/copom-vector-pipeline/scripts/create_schema.sql
```

---

### `SELECT count(*) FROM chunks` returns 0

**Cause**: No documents have been ingested yet.

**Fix**: Run the copom-vector-pipeline:
```bash
copom-pipeline --doc-type all
```

---

## Provider errors

### `EnvironmentError: GEMINI_API_KEY environment variable is not set`

**Fix**: Add `GEMINI_API_KEY=your-key-here` to your `.env` file.

---

### `ValueError: Unknown embedding provider 'openai'`

**Cause**: `EMBEDDING_PROVIDER=openai` is set but no OpenAI provider is registered.

**Fix**: Either set `EMBEDDING_PROVIDER=gemini`, or implement an OpenAI provider — see [README.md](README.md#adding-a-new-provider).

---

### Embedding dimension mismatch

**Symptom**: Queries return no results or incorrect results even though chunks exist in the database.

**Cause**: `GEMINI_EMBEDDING_MODEL` in the API differs from what copom-vector-pipeline used during ingestion.

**Fix**: Ensure both repos use the same value for `GEMINI_EMBEDDING_MODEL`. The default is `models/text-embedding-004`.

---

## API errors

### `403 Forbidden: Invalid or missing API key`

**Cause**: `COPOM_API_KEY` is set in `.env` but the request does not include the `X-API-Key` header.

**Fix**:
```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/ask ...
```
Or leave `COPOM_API_KEY=` empty in `.env` to disable auth for local development.

---

### `500 Internal error while generating answer`

**Cause**: An unhandled exception in the RAG pipeline. Check the server logs for details.

**Fix**:
```bash
docker compose logs copom-rag-api
# or
uvicorn copom_rag.api.main:app --log-level debug
```

---

### `/ask` returns `"Não encontrei documentos relevantes"`

**Cause**: The vector search returned no results. Possible reasons:
1. No documents ingested — run copom-vector-pipeline.
2. `doc_type` filter too restrictive.
3. `date_from`/`date_to` range excludes all documents.
4. Embedding model mismatch (see above).

**Fix**: Try `POST /ask` with no filters first:
```json
{"question": "Selic"}
```

---

## Reranking issues

### `RERANK_WITH_LLM=true` causes slow responses

**Cause**: Each `/ask` call makes an extra LLM API request for reranking.

**Fix**: Set `RERANK_WITH_LLM=false` to disable reranking and use raw vector similarity order.

---

### Reranking returns wrong order

**Cause**: The reranking prompt may not be well-suited to your use case.

**Fix**: Override the reranking prompt via `COPOM_PROMPTS_FILE`. See `prompts/reranking.yaml` for the format.

---

## Docker issues

### API container starts before PostgreSQL is ready

**Symptom**: `copom-rag-api` container crashes immediately with a connection error.

**Cause**: Docker healthcheck took longer than expected.

**Fix**: Increase the `retries` value in `docker-compose.yml`:
```yaml
healthcheck:
  retries: 20
```
Or restart the API container after PostgreSQL is healthy:
```bash
docker compose restart copom-rag-api
```
