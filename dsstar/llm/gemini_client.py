from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Optional

from dsstar.llm.base import LLMClient


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        self.api_key = api_key
        self.model = model or "gemini-1.5-flash"
        self.name = "gemini"

    def complete(self, prompt: str) -> str:
        base = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        url = f"{base}?{urllib.parse.urlencode({'key': self.api_key})}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0},
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["candidates"][0]["content"]["parts"][0]["text"]
