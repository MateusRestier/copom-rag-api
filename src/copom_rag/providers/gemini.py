"""Google Gemini embedding and LLM providers.

Uses the current google-genai SDK (google.genai), which replaced the
deprecated google-generativeai package.

Embedding model : text-embedding-004 (768 dims, multilingual, Portuguese-capable)
LLM model       : gemini-1.5-flash (configurable via GEMINI_LLM_MODEL)

Required env vars:
    GEMINI_API_KEY          — your Google AI API key
    GEMINI_EMBEDDING_MODEL  — (optional) defaults to models/text-embedding-004
    GEMINI_LLM_MODEL        — (optional) defaults to gemini-1.5-flash
"""

from __future__ import annotations

import json
import logging
import os
import re

from copom_rag.providers.base import EmbeddingProvider, LLMProvider
from copom_rag.providers.factory import register_embedding_provider, register_llm_provider

logger = logging.getLogger(__name__)


def _make_client():
    """Create and return a google.genai Client. Raises if API key is missing."""
    from google import genai  # type: ignore

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Set it in your .env file."
        )
    return genai.Client(api_key=api_key)


@register_embedding_provider("gemini")
class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by the Google Gemini API (google-genai SDK).

    Model: text-embedding-004 (768 dimensions).
    MUST match the model used by copom-vector-pipeline during ingestion.
    """

    _DEFAULT_MODEL = "models/text-embedding-004"
    _DIMENSIONS = 768

    def __init__(self) -> None:
        self._client = _make_client()
        self._model = os.environ.get("GEMINI_EMBEDDING_MODEL", self._DEFAULT_MODEL)

    def embed_text(self, text: str) -> list[float]:
        result = self._client.models.embed_content(
            model=self._model,
            contents=text,
        )
        return list(result.embeddings[0].values)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            result = self._client.models.embed_content(
                model=self._model,
                contents=texts,
            )
            return [list(e.values) for e in result.embeddings]
        except Exception:
            return [self.embed_text(t) for t in texts]

    @property
    def dimensions(self) -> int:
        return self._DIMENSIONS


@register_llm_provider("gemini")
class GeminiLLMProvider(LLMProvider):
    """LLM provider backed by the Google Gemini API (google-genai SDK)."""

    _DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self) -> None:
        self._client = _make_client()
        self._model_name = os.environ.get("GEMINI_LLM_MODEL", self._DEFAULT_MODEL)
        self._temperature = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
        self._max_tokens = int(os.environ.get("MAX_OUTPUT_TOKENS", "2048"))

    def generate(self, prompt: str, system: str | None = None) -> str:
        from google.genai import types  # type: ignore

        contents = (system + "\n\n" + prompt) if system else prompt
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=self._temperature,
                max_output_tokens=self._max_tokens,
            ),
        )
        return response.text.strip()

    def generate_json(self, prompt: str, system: str | None = None) -> dict:
        raw = self.generate(prompt, system=system)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse JSON from model response: {text[:200]!r}")
