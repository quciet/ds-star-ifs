from __future__ import annotations

from typing import Optional

from dsstar.config import get_env
from dsstar.llm.base import LLMClient
from dsstar.llm.deepseek_client import DeepSeekClient
from dsstar.llm.gemini_client import GeminiClient
from dsstar.llm.local_stub import LocalStubClient
from dsstar.llm.mock_client import MockClient
from dsstar.llm.openai_client import OpenAIClient


def _warn(message: str) -> None:
    print(f"[warn] {message}")


def get_client(provider: str, model: Optional[str] = None, timeout_sec: int = 60) -> LLMClient:
    # Reuse CLI timeout for provider HTTP calls to keep request timing behavior consistent.
    provider = provider.lower()
    if provider == "mock":
        return MockClient()
    if provider == "openai":
        api_key = get_env("OPENAI_API_KEY")
        if not api_key:
            _warn("OPENAI_API_KEY missing; falling back to mock provider.")
            return MockClient()
        return OpenAIClient(api_key=api_key, model=model or get_env("OPENAI_MODEL"), timeout_sec=timeout_sec)
    if provider == "deepseek":
        api_key = get_env("DEEPSEEK_API_KEY")
        if not api_key:
            _warn("DEEPSEEK_API_KEY missing; falling back to mock provider.")
            return MockClient()
        return DeepSeekClient(
            api_key=api_key,
            model=model or get_env("DEEPSEEK_MODEL"),
            base_url=get_env("DEEPSEEK_BASE_URL"),
            timeout_sec=timeout_sec,
        )
    if provider == "gemini":
        api_key = get_env("GEMINI_API_KEY")
        if not api_key:
            _warn("GEMINI_API_KEY missing; falling back to mock provider.")
            return MockClient()
        return GeminiClient(api_key=api_key, model=model or get_env("GEMINI_MODEL"), timeout_sec=timeout_sec)
    if provider == "local":
        return LocalStubClient(name="local", model=model or get_env("LOCAL_LLM_MODEL") or "local-stub")
    _warn(f"Unknown provider '{provider}', falling back to mock.")
    return MockClient()
