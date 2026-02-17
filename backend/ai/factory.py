from typing import Dict, Type, Optional
from backend.ai.providers.base import BaseProvider
from backend.ai.providers.openai import OpenAIProvider
from backend.ai.providers.anthropic import AnthropicProvider
from backend.ai.providers.generic import GenericProvider
from backend.ai.models import ProviderConfig

class ProviderFactory:
    """
    Factory to instantiate AI providers based on configuration.
    """

    _REGISTRY: Dict[str, Type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "generic": GenericProvider
    }

    @staticmethod
    def get_provider(config: ProviderConfig) -> BaseProvider:
        provider_class = ProviderFactory._REGISTRY.get(config.type)
        if not provider_class:
            raise ValueError(f"Unknown provider type: {config.type}")

        return provider_class(config)

    @staticmethod
    def register_provider(type_name: str, provider_class: Type[BaseProvider]):
        ProviderFactory._REGISTRY[type_name] = provider_class
