from __future__ import annotations

from dataclasses import dataclass

from dsstar.llm.base import LLMClient


@dataclass
class LocalStubClient(LLMClient):
    name: str = "local"
    model: str = "local-stub"

    def complete(self, prompt: str) -> str:
        raise RuntimeError(
            "Local provider is not configured. Install and configure a local "
            "LLM server (e.g., vLLM/Ollama/Transformers) and wire it into this adapter."
        )
