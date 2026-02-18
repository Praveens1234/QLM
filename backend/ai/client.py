import os
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from backend.ai.config_manager import AIConfigManager

logger = logging.getLogger("QLM.AI.Client")

class AIClient:
    """
    A generic OpenAI-compatible API client.
    Supports dynamic configuration via AIConfigManager.
    """
    def __init__(self):
        self.config_manager = AIConfigManager()
        self._reload_config()

    def _reload_config(self):
        conf = self.config_manager.get_active_config()
        self.api_key = conf.get("api_key")
        self.base_url = conf.get("base_url", "https://api.openai.com/v1").rstrip("/")
        self.model = conf.get("model", "gpt-4-turbo")

    def configure(self, api_key: str, base_url: str, model: str):
        """
        Legacy/Direct override.
        Note: This doesn't persist to the new manager structure directly unless we update the manager.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat_completion(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        self._reload_config() # Ensure latest

        if not self.api_key:
             raise ValueError("AI API Key not configured. Please check Settings.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False # Streaming handled via other means if needed, keeping simple here
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"AI Request failed: {response.status} - {error_text}")
                        raise Exception(f"AI API Error: {response.status} - {error_text}")

                    return await response.json()

        except Exception as e:
            logger.error(f"AI Client Exception: {e}")
            raise e

    async def list_models(self) -> List[str]:
        self._reload_config()
        if not self.api_key:
             return []

        url = f"{self.base_url}/models"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "data" in data:
                            return [m["id"] for m in data["data"]]
                        return []
                    else:
                        logger.warning(f"Failed to list models: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []
