
import os
import aiohttp
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator

logger = logging.getLogger("QLM.AI.Client")

class AIClient:
    """
    A generic OpenAI-compatible API client.
    Supports streaming and non-streaming chat completions.
    """
    def __init__(self, api_key: str = None, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model
        
    def configure(self, api_key: str, base_url: str, model: str):
        """Update client configuration at runtime."""
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        logger.info(f"AI Client configured: Model={self.model}, BaseURL={self.base_url}")

    async def chat_completion(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None, stream: bool = False) -> Dict[str, Any]:
        """
        Send a chat completion request.
        """
        if not self.api_key:
             # For some local LLMs, API key might not be strictly required, but usually is. 
             # We'll warn but proceed if it's missing, or maybe use a dummy.
             pass

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
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
                    
                    if stream:
                        # For now, we will just return the response object for the caller to iterate
                        # But typically this method might yield. 
                        # To keep it simple for the first pass, let's implement non-streaming first thoroughly.
                        raise NotImplementedError("Streaming not yet implemented in basic client wrapper")
                    else:
                        return await response.json()
                        
        except Exception as e:
            logger.error(f"AI Client Exception: {e}")
            raise e

    async def list_models(self) -> List[str]:
        """
        Fetch available models from the provider.
        """
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
                        # OpenAI format: {"data": [{"id": "model-id", ...}, ...]}
                        if "data" in data:
                            return [m["id"] for m in data["data"]]
                        return []
                    else:
                        logger.warning(f"Failed to list models: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []
