"""Google Gemini embedding and LLM providers.

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


def _configure_genai():
    """Configure the Gemini SDK with the API key. Raises if key is missing."""
    import google.generativeai as genai  # type: ignore

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Set it in your .env file."
        )
    genai.configure(api_key=api_key)
    return genai


@register_embedding_provider("gemini")
class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by the Google Gemini API.

    Model: text-embedding-004 (768 dimensions).
    MUST match the model used by copom-vector-pipeline during ingestion.
    """

    _DEFAULT_MODEL = "models/text-embedding-004"
    _DIMENSIONS = 768

    def __init__(self) -> None:
        self._genai = _configure_genai()
        self._model = os.environ.get("GEMINI_EMBEDDING_MODEL", self._DEFAULT_MODEL)

    def embed_text(self, text: str) -> list[float]:
        result = self._genai.embed_content(
            model=self._model,
            content=text,
            task_type="retrieval_query",  # query side (vs. retrieval_document in pipeline)
        )
        return result["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            result = self._genai.embed_content(
                model=self._model,
                content=texts,
                task_type="retrieval_query",
            )
            embeddings = result["embedding"]
            if texts and isinstance(embeddings[0], float):
                return [embeddings]
            return embeddings
        except Exception:
            return [self.embed_text(t) for t in texts]

    @property
    def dimensions(self) -> int:
        return self._DIMENSIONS


@register_llm_provider("gemini")
class GeminiLLMProvider(LLMProvider):
    """LLM provider backed by the Google Gemini API."""

    _DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self) -> None:
        import google.generativeai as genai  # type: ignore
        _configure_genai()
        model_name = os.environ.get("GEMINI_LLM_MODEL", self._DEFAULT_MODEL)
        self._model = genai.GenerativeModel(model_name)
        self._temperature = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
        self._max_tokens = int(os.environ.get("MAX_OUTPUT_TOKENS", "2048"))

    def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate a text response."""
        import google.generativeai as genai  # type: ignore

        parts = []
        if system:
            parts.append(system + "\n\n")
        parts.append(prompt)

        response = self._model.generate_content(
            "".join(parts),
            generation_config=genai.types.GenerationConfig(
                temperature=self._temperature,
                max_output_tokens=self._max_tokens,
            ),
        )
        return response.text.strip()

    def generate_json(self, prompt: str, system: str | None = None) -> dict:
        """Generate a response and parse it as JSON.

        Strips markdown code fences (```json ... ```) before parsing,
        mirroring the robustness pattern from rag-framework's
        AzureOpenAIAdapter._parse_json_response.
        """
        raw = self.generate(prompt, system=system)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(text: str) -> dict:
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Last-resort: extract the first {...} block
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse JSON from model response: {text[:200]!r}")
