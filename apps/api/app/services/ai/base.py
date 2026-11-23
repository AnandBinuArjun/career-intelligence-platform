from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    @abstractmethod
    async def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Return schema-validated structured output. Implement timeout and retry policy."""
        raise NotImplementedError

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError
