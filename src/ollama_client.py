"""
Ollama HTTP client helpers.

This module talks to a local Ollama server (default http://127.0.0.1:11434)
to list models and generate chat completions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import requests

from src.logger import get_logger


logger = get_logger()


@dataclass(frozen=True)
class OllamaChatMessage:
    role: str
    content: str


class OllamaClient:
    """Minimal Ollama client for /api/tags and /api/chat."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "",
        timeout_seconds: int = 20,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = (model or "").strip()
        self.timeout_seconds = timeout_seconds

    @property
    def tags_url(self) -> str:
        return f"{self.base_url}/api/tags"

    @property
    def chat_url(self) -> str:
        return f"{self.base_url}/api/chat"

    @property
    def embeddings_url(self) -> str:
        return f"{self.base_url}/api/embeddings"

    def list_models(self) -> List[str]:
        """Return available model names from Ollama."""
        resp = requests.get(self.tags_url, timeout=self.timeout_seconds)
        resp.raise_for_status()
        payload = resp.json() or {}
        models = payload.get("models", []) or []
        names = []
        for m in models:
            name = (m or {}).get("name")
            if name:
                names.append(str(name))
        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for n in names:
            if n not in seen:
                ordered.append(n)
                seen.add(n)
        return ordered

    @staticmethod
    def select_best_model(model_names: List[str]) -> Optional[str]:
        """
        Select a preferred model using a simple priority heuristic.

        Priority (first match wins):
        llama3.1, llama3.2, mistral, qwen2.5, phi3, gemma2
        Otherwise pick the lexicographically largest model name.
        """
        if not model_names:
            return None

        lower = [n.lower() for n in model_names]
        priorities = ["llama3.1", "llama3.2", "mistral", "qwen2.5", "phi3", "gemma2"]
        for p in priorities:
            for idx, n in enumerate(lower):
                if p in n:
                    return model_names[idx]

        # Fallback: "largest available by name order"
        return sorted(model_names)[-1]

    def resolve_model(self) -> Optional[str]:
        """Return the model to use (pinned or auto-selected)."""
        if self.model:
            return self.model
        try:
            names = self.list_models()
            chosen = self.select_best_model(names)
            if chosen:
                logger.info(f"Using Ollama model: {chosen} (auto-selected)")
            else:
                logger.warning("No Ollama models found via /api/tags")
            return chosen
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return None

    def chat(
        self,
        messages: List[OllamaChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 120,
    ) -> str:
        """Generate a chat completion and return message content."""
        resolved_model = (model or self.model or "").strip()
        if not resolved_model:
            resolved_model = self.resolve_model() or ""
        if not resolved_model:
            raise RuntimeError("Ollama model not resolved; cannot call /api/chat")

        # Ollama expects payload:
        # {model, messages:[{role,content},...], stream:false, options:{temperature}}
        payload: Dict[str, Any] = {
            "model": resolved_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": float(temperature), "num_predict": int(max_tokens)},
        }

        resp = requests.post(self.chat_url, json=payload, timeout=self.timeout_seconds)
        resp.raise_for_status()
        data = resp.json() or {}
        content = ((data.get("message") or {}).get("content")) or ""
        return str(content).strip()

    def embeddings(self, prompt: str, model: str) -> Sequence[float]:
        """
        Return embedding vector for text via Ollama /api/embeddings.

        Args:
            prompt: Text to embed
            model: Embedding model name (e.g. nomic-embed-text)

        Returns:
            List of floats
        """
        resolved_model = (model or "").strip()
        if not resolved_model:
            raise ValueError("Embedding model name is required")

        payload: Dict[str, Any] = {
            "model": resolved_model,
            "prompt": (prompt or "").strip(),
        }
        resp = requests.post(
            self.embeddings_url, json=payload, timeout=self.timeout_seconds
        )
        resp.raise_for_status()
        data = resp.json() or {}
        emb = data.get("embedding")
        if not isinstance(emb, list):
            raise RuntimeError(f"Unexpected embeddings response: {repr(data)[:500]}")
        return [float(x) for x in emb]

