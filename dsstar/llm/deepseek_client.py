from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from dsstar.llm.base import LLMClient


class DeepSeekClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_sec: int = 60,
    ) -> None:
        # Initialize dataclass fields via the base class for a consistent LLMClient contract.
        super().__init__(name="deepseek", model=(model or "deepseek-reasoner"))
        self.api_key = api_key
        self.base_url = base_url or "https://api.deepseek.com"
        self.name = "deepseek"

    def _chat_completions_url(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self._chat_completions_url(),
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek API error ({error.code}): {details}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"DeepSeek request failed: {error.reason}") from error
        return body["choices"][0]["message"]["content"]
