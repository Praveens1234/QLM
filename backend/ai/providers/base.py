from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from backend.ai.models import ProviderConfig, Model

class BaseProvider(ABC):
    """
    Abstract Base Class for AI Model Providers.
    """

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], model: str, tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Send a chat completion request to the provider.
        Must return a standardized OpenAI-like response dictionary.
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[Model]:
        """
        Fetch available models from the provider's API.
        """
        pass

    @abstractmethod
    async def validate_key(self) -> bool:
        """
        Check if the API key/connection is valid.
        """
        pass
