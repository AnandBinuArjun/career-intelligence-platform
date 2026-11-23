from typing import Any

import httpx

from app.core.config import settings
from app.services.ai.base import AIProvider


class OllamaProvider(AIProvider):
    async def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = {
            "model": settings.ollama_model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        timeout = httpx.Timeout(connect=2.0, read=60.0, write=10.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            import json
            return json.loads(data["message"]["content"])

    async def embed(self, text: str) -> list[float]:
        # Configure and pin an embedding model before enabling semantic search.
        raise NotImplementedError("Embedding model selection is a Phase 2 decision.")
