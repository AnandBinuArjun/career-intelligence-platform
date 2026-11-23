import json
from typing import Any

import httpx

from app.core.config import settings
from app.services.ai.base import AIProvider


class ExternalOpenAIProvider(AIProvider):
    """OpenAI-compatible external inference adapter.

    Must ONLY be instantiated/called after verifying both server-side configuration
    (`EXTERNAL_AI_ENABLED=true`) and an active, purpose-specific user ConsentRecord.
    """

    async def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not settings.external_ai_enabled or not settings.external_ai_base_url or not settings.external_ai_api_key:
            raise RuntimeError("External AI provider is disabled or not configured")

        payload = {
            "model": settings.external_ai_model or "gpt-4o-mini",
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.external_ai_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{settings.external_ai_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError("External embeddings require explicit configuration.")
