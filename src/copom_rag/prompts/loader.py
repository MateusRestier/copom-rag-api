"""Prompt template loader.

Tries to load templates from a YAML file (path set via COPOM_PROMPTS_FILE
env var).  Falls back to the Python defaults in templates.py if the file
is not configured or cannot be loaded.

YAML format:
    answer_generation_system: "..."
    answer_generation_template: "..."
    reranking_system: "..."
    reranking_template: "..."
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Mapping from logical template name to (module_attr, default_value)
_DEFAULTS: dict[str, str] = {}


def _load_defaults() -> dict[str, str]:
    from copom_rag.prompts import templates

    return {
        "answer_generation_system": templates.ANSWER_GENERATION_SYSTEM,
        "answer_generation_template": templates.ANSWER_GENERATION_TEMPLATE,
        "reranking_system": templates.RERANKING_SYSTEM,
        "reranking_template": templates.RERANKING_TEMPLATE,
    }


class PromptLoader:
    """Loads and caches prompt templates.

    If COPOM_PROMPTS_FILE points to a valid YAML file, templates from that
    file override the Python defaults.  Unknown keys in the YAML are ignored.
    """

    def __init__(self, prompts_file: str | None = None) -> None:
        self._file = prompts_file or os.environ.get("COPOM_PROMPTS_FILE") or ""
        self._templates: dict[str, str] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._templates = _load_defaults()
        if self._file:
            self._load_yaml()
        self._loaded = True

    def _load_yaml(self) -> None:
        try:
            import yaml  # type: ignore

            with open(self._file, encoding="utf-8") as f:
                overrides = yaml.safe_load(f) or {}
            for key, value in overrides.items():
                if key in self._templates:
                    self._templates[key] = str(value)
                    logger.debug("Prompt override loaded: %s", key)
                else:
                    logger.debug("Unknown prompt key in YAML (ignored): %s", key)
            logger.info("Prompts loaded from %s", self._file)
        except FileNotFoundError:
            logger.warning("COPOM_PROMPTS_FILE not found: %s — using defaults.", self._file)
        except Exception as exc:
            logger.warning("Failed to load prompts YAML: %s — using defaults.", exc)

    def get(self, name: str) -> str:
        """Return the template string for the given name."""
        self._ensure_loaded()
        if name not in self._templates:
            raise KeyError(f"Unknown prompt template: '{name}'. Available: {list(self._templates)}")
        return self._templates[name]

    def render(self, name: str, **kwargs: str) -> str:
        """Return the template with placeholders filled in."""
        return self.get(name).format_map(kwargs)
