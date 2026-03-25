"""Abstract base classes for pluggable LLM and embedding providers.

To add a new provider:
1. Create a new file in this package (e.g. openai.py).
2. Subclass EmbeddingProvider and/or LLMProvider and implement all abstract methods.
3. Decorate each class with the appropriate register decorator.
4. Import the module in factory.py inside _load_providers().
5. Set EMBEDDING_PROVIDER and/or LLM_PROVIDER in .env — no other changes needed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Interface every embedding provider must satisfy."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Return the embedding vector for a single text string."""
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a list of text strings."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Dimensionality of vectors produced by this provider."""
        ...


class LLMProvider(ABC):
    """Interface every LLM provider must satisfy.

    The interface is intentionally minimal: generate() and generate_json().
    Logging, retry, and prompt formatting are handled in the calling layer
    (rag_service.py), keeping this ABC clean and easy to implement.
    """

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate a text response for the given prompt.

        Args:
            prompt: The user/task prompt.
            system: Optional system instruction.

        Returns:
            The model's response as a plain string.
        """
        ...

    @abstractmethod
    def generate_json(self, prompt: str, system: str | None = None) -> dict:
        """Generate a response and parse it as JSON.

        Implementations should strip markdown code fences before parsing
        and handle malformed responses gracefully.

        Returns:
            Parsed JSON as a dict.  Raises ValueError on parse failure.
        """
        ...
