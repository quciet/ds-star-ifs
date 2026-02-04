"""LLM client adapters."""

from dsstar.llm.base import LLMClient
from dsstar.llm.registry import get_client

__all__ = ["LLMClient", "get_client"]
