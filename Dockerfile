FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

# Copy prompt YAML files (optional customization)
COPY prompts/ prompts/

EXPOSE 8000

CMD ["uvicorn", "copom_rag.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
