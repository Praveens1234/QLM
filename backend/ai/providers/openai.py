import aiohttp
import logging
from typing import List, Dict, Any, Optional
from backend.ai.providers.base import BaseProvider
from backend.ai.models import Model
from backend.core.exceptions import SystemError

logger = logging.getLogger("QLM.AI.OpenAI")

class OpenAIProvider(BaseProvider):
    """
    Implementation for OpenAI and OpenAI-compatible APIs.
    """

    async def chat_completion(self, messages: List[Dict[str, str]], model: str, tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7 # Could be configurable
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenAI Request failed: {response.status} - {error_text}")
                        # Raise specific errors based on status code
                        if response.status == 401:
                            raise SystemError("Invalid API Key.")
                        elif response.status == 429:
                            raise SystemError("Rate limit exceeded.")
                        else:
                            raise SystemError(f"AI Provider Error: {response.status}")

                    return await response.json()

        except Exception as e:
            logger.error(f"OpenAI Connection Error: {e}")
            raise e

    async def list_models(self) -> List[Model]:
        url = f"{self.config.base_url.rstrip('/')}/models"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = []
                        if "data" in data:
                            for m in data["data"]:
                                models.append(Model(
                                    id=m["id"],
                                    name=m.get("id", "Unknown"),
                                    # Heuristic or map known models to context window
                                    context_window=128000 if "gpt-4" in m["id"] else 16000
                                ))
                        return models
                    else:
                        logger.warning(f"Failed to list models: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []

    async def validate_key(self) -> bool:
        try:
            models = await self.list_models()
            return len(models) > 0
        except:
            return False
