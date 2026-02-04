from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMClient(ABC):
    name: str
    model: str

    @abstractmethod
    def complete(self, prompt: str) -> str:
        raise NotImplementedError
