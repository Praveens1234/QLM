from backend.ai.providers.openai import OpenAIProvider
import logging

logger = logging.getLogger("QLM.AI.Generic")

class GenericProvider(OpenAIProvider):
    """
    Implementation for generic OpenAI-compatible APIs (Ollama, LM Studio, vLLM).
    Inherits from OpenAIProvider but allows looser validation.
    """

    async def validate_key(self) -> bool:
        # Many local providers don't require a real key, just connectivity.
        try:
            # Try listing models
            models = await self.list_models()
            return True # If we get a response (even empty list), it's reachable
        except Exception:
            return False
