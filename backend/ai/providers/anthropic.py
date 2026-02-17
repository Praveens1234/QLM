import aiohttp
import logging
from typing import List, Dict, Any, Optional
from backend.ai.providers.base import BaseProvider
from backend.ai.models import Model
from backend.core.exceptions import SystemError

logger = logging.getLogger("QLM.AI.Anthropic")

class AnthropicProvider(BaseProvider):
    """
    Implementation for Anthropic API.
    Maps OpenAI-style messages to Anthropic format.
    """

    async def chat_completion(self, messages: List[Dict[str, str]], model: str, tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        # 1. Extract System Prompt
        system_prompt = ""
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg["content"] + "\n"
            else:
                filtered_messages.append(msg)

        # 2. Format Tools (Anthropic uses different schema, we might need a converter)
        # For this phase, we assume tools are converted or we support OpenAI format only
        # and this provider is text-only for now unless we add a converter layer.
        # Let's keep it simple: Basic chat support.

        payload = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": 4096, # Required by Anthropic
            "system": system_prompt
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Anthropic Request failed: {response.status} - {error_text}")
                        raise SystemError(f"Anthropic Error: {response.status}")

                    data = await response.json()

                    # Map back to OpenAI Format
                    content = data["content"][0]["text"]
                    return {
                        "choices": [{
                            "message": {
                                "role": "assistant",
                                "content": content
                            }
                        }]
                    }

        except Exception as e:
            logger.error(f"Anthropic Connection Error: {e}")
            raise e

    async def list_models(self) -> List[Model]:
        # Anthropic doesn't have a list_models API yet. Return hardcoded list.
        return [
            Model(id="claude-3-opus-20240229", name="Claude 3 Opus", context_window=200000),
            Model(id="claude-3-sonnet-20240229", name="Claude 3 Sonnet", context_window=200000),
            Model(id="claude-3-haiku-20240307", name="Claude 3 Haiku", context_window=200000),
        ]

    async def validate_key(self) -> bool:
        # Simple test call
        try:
            await self.chat_completion([{"role": "user", "content": "Hi"}], "claude-3-haiku-20240307")
            return True
        except:
            return False
