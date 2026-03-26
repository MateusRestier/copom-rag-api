# Deployment Guide — copom-rag-api

The API is deployed as a Docker container on [Render](https://render.com) (free tier).
It connects to the Neon PostgreSQL database shared with `copom-vector-pipeline`.

---

## Production Stack

| Component | Service | URL |
|-----------|---------|-----|
| API hosting | [Render](https://render.com) (free tier) | `https://copom-rag-api.onrender.com` |
| Vector database | [Neon](https://neon.tech) (free tier) | PostgreSQL 17 + pgvector |
| LLM | Google Gemini (`gemini-2.5-flash`) | via Gemini API |
| Embedding model | Google Gemini (`gemini-embedding-001`) | 1536-dim output |

---

## Render Service Configuration

| Setting | Value |
|---------|-------|
| Runtime | Docker (uses `./Dockerfile`) |
| Branch | `main` |
| Region | Oregon (US West) |
| Instance type | Free |
| Auto-deploy | On commit (deploys automatically on every push to `main`) |
| Health check path | `/health` |

---

## Environment Variables

All secrets are set in the Render dashboard under **Environment → Environment Variables**.
They are never stored in the repository.

| Variable | Description |
|----------|-------------|
| `EMBEDDING_PROVIDER` | `gemini` |
| `LLM_PROVIDER` | `gemini` |
| `GEMINI_API_KEY` | Google AI API key |
| `GEMINI_EMBEDDING_MODEL` | `models/gemini-embedding-001` — must match what the pipeline used |
| `EMBEDDING_DIMENSIONS` | `1536` — must match the pipeline and database schema |
| `GEMINI_LLM_MODEL` | `gemini-2.5-flash` |
| `DATABASE_URL` | Neon connection string (see below) |
| `RETRIEVAL_TOP_K` | `20` — chunks retrieved from pgvector per query |
| `CONTEXT_TOP_K` | `5` — chunks sent to the LLM after reranking |
| `RERANK_WITH_LLM` | `true` |
| `LLM_TEMPERATURE` | `0.3` |
| `MAX_OUTPUT_TOKENS` | `8192` |
| `MAX_CONTEXT_TOKENS` | `6000` |
| `COPOM_API_KEY` | Leave empty to disable auth, or set a secret string to enable `X-API-Key` header auth |

---

## Updating an Environment Variable

1. Go to [render.com](https://render.com) → service `copom-rag-api`
2. Left sidebar → **Environment**
3. Edit the variable and click **Save Changes**
4. Render will automatically redeploy the service with the new value

---

## Rotating the Database Password

If the Neon password is rotated, update `DATABASE_URL` here:

1. Get the new connection string from Neon (see [copom-vector-pipeline DEPLOYMENT.md](../copom-vector-pipeline/DEPLOYMENT.md#getting-the-neon-connection-string))
2. In Render: Environment → find `DATABASE_URL` → update the value → Save Changes
3. Render redeploys automatically

---

## Manual Redeploy

If you need to force a redeploy without a code change:

1. Render dashboard → service `copom-rag-api`
2. Top right → **Manual Deploy** → **Deploy latest commit**

---

## Free Tier Limitations

**Spin-down after inactivity:** The free tier stops the container after 15 minutes without
requests. The next request after a sleep period takes 30–60 seconds to respond (cold start).

**Recommended mitigation:** Use [UptimeRobot](https://uptimerobot.com) (free) to ping
`https://copom-rag-api.onrender.com/health` every 14 minutes. This keeps the service
warm without any cost.

Setup:
1. Create account at uptimerobot.com
2. New Monitor → type: HTTP(s)
3. URL: `https://copom-rag-api.onrender.com/health`
4. Monitoring interval: 14 minutes

---

## Verifying the Deployment

```bash
# Health check — returns provider info and DB connectivity status
curl https://copom-rag-api.onrender.com/health

# List ingested documents
curl https://copom-rag-api.onrender.com/documents

# Ask a question
curl -X POST https://copom-rag-api.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual foi a decisao do Copom sobre a taxa Selic em 2026?"}'
```

---

## Troubleshooting

### Build fails on Render

Check the build logs in the Render dashboard (Deploys tab). Common causes:
- Missing system dependency: the `Dockerfile` installs `libpq-dev` and `gcc` for psycopg2
- `pyproject.toml` syntax error

### API returns 500 on `/ask`

1. Check logs in Render dashboard → Logs tab
2. Common causes: `GEMINI_API_KEY` invalid, `DATABASE_URL` wrong, embedding dimension mismatch

### `EMBEDDING_DIMENSIONS` mismatch

If the pipeline was run with a different `EMBEDDING_DIMENSIONS` value than the API is
configured with, vector search will fail. Both must be `1536`. The database schema also
uses `vector(1536)`. Changing this requires dropping and recreating the `chunks` table
and re-ingesting all documents.
