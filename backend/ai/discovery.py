import logging
from typing import List
from backend.ai.config_manager import AIConfigManager
from backend.ai.factory import ProviderFactory
from backend.ai.models import Model

logger = logging.getLogger("QLM.AI.Discovery")

class ModelDiscoveryService:
    """
    Service to fetch available models from providers and update the config.
    """
    def __init__(self):
        self.config_manager = AIConfigManager()

    async def discover_models(self, provider_id: str) -> List[Model]:
        """
        Fetch models from the provider API and save to DB.
        """
        config = self.config_manager.get_provider_config(provider_id)
        if not config:
            raise ValueError(f"Provider {provider_id} not found")

        try:
            provider = ProviderFactory.get_provider(config)
            models = await provider.list_models()

            if models:
                self.config_manager.update_models(provider_id, models)
                logger.info(f"Discovered {len(models)} models for {provider_id}")

            return models
        except Exception as e:
            logger.error(f"Model discovery failed for {provider_id}: {e}")
            raise e

# Singleton
model_discovery = ModelDiscoveryService()
