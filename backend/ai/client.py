import logging
from typing import List, Dict, Any, Optional
from backend.ai.config_manager import AIConfigManager
from backend.ai.factory import ProviderFactory
from backend.core.exceptions import SystemError
from backend.ai.resilience import ai_retry

logger = logging.getLogger("QLM.AI.Client")

class AIClient:
    """
    Unified AI Client acting as a gateway to multiple providers.
    Handles dynamic routing based on active configuration.
    Includes Resilience Layer.
    """
    def __init__(self):
        self.config_manager = AIConfigManager()

    @ai_retry
    async def chat_completion(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Route request to the active provider with automatic retries.
        """
        config = self.config_manager.get_config()

        if not config.active_provider_id:
            raise SystemError("No active AI provider configured.")

        provider_conf = next((p for p in config.providers if p.id == config.active_provider_id), None)
        if not provider_conf:
            raise SystemError(f"Active provider {config.active_provider_id} not found in configuration.")

        model = config.active_model_id
        if not model and provider_conf.models:
            model = provider_conf.models[0].id

        if not model:
             raise SystemError(f"No model selected for provider {provider_conf.name}.")

        try:
            provider = ProviderFactory.get_provider(provider_conf)
            logger.info(f"Sending request to {provider_conf.name} ({model})...")
            response = await provider.chat_completion(messages, model, tools)
            return response

        except Exception as e:
            logger.warning(f"Unified Client Request Failed: {e}")
            raise e # Trigger retry

    async def list_models(self) -> List[str]:
        """
        List models for the *active* provider (Legacy compatibility).
        """
        config = self.config_manager.get_config()
        provider_conf = next((p for p in config.providers if p.id == config.active_provider_id), None)
        if not provider_conf: return []
        
        return [m.id for m in provider_conf.models]
