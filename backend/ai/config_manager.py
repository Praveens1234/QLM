import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("QLM.AI.Config")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

class AIConfigManager:
    """
    Manages AI Providers, Models, and Defaults.
    Schema:
    {
        "active_provider_id": "nvidia",
        "active_model_id": "minimaxai/minimax-m2.1",
        "providers": [
            {
                "id": "nvidia",
                "name": "NVIDIA NIM",
                "base_url": "https://integrate.api.nvidia.com/v1",
                "api_key": "...",
                "available_models": ["minimaxai/minimax-m2.1", ...]
            }
        ]
    }
    """
    def __init__(self):
        self.config = {
            "active_provider_id": "",
            "active_model_id": "",
            "providers": []
        }
        self._load()

    def _load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    # Migrate old config if needed
                    if "api_key" in data and "providers" not in data:
                        self.config["providers"] = [{
                            "id": "default",
                            "name": "Default Provider",
                            "base_url": data.get("base_url"),
                            "api_key": data.get("api_key"),
                            "available_models": [data.get("model")] if data.get("model") else []
                        }]
                        self.config["active_provider_id"] = "default"
                        self.config["active_model_id"] = data.get("model", "")
                    else:
                        self.config = data
            except Exception as e:
                logger.error(f"Failed to load AI config: {e}")

    def _save(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4)

    def add_provider(self, name: str, base_url: str, api_key: str) -> str:
        provider_id = name.lower().replace(" ", "_")

        # Check if exists
        for p in self.config["providers"]:
            if p["id"] == provider_id:
                p["base_url"] = base_url
                p["api_key"] = api_key
                self._save()
                return provider_id

        self.config["providers"].append({
            "id": provider_id,
            "name": name,
            "base_url": base_url,
            "api_key": api_key,
            "available_models": []
        })

        if not self.config["active_provider_id"]:
            self.config["active_provider_id"] = provider_id

        self._save()
        return provider_id

    def set_models(self, provider_id: str, models: List[str]):
        for p in self.config["providers"]:
            if p["id"] == provider_id:
                p["available_models"] = models
                # If active provider has no active model, set first
                if self.config["active_provider_id"] == provider_id and not self.config["active_model_id"] and models:
                    self.config["active_model_id"] = models[0]
                self._save()
                return
        raise ValueError("Provider not found")

    def set_active(self, provider_id: str, model_id: str):
        # Validate
        valid = False
        for p in self.config["providers"]:
            if p["id"] == provider_id:
                if model_id in p["available_models"]:
                    valid = True
                break

        if not valid:
            # Allow setting if model list is empty (manual override) or strict?
            # Let's allow manual model setting even if not in list, but provider must exist
            pass

        self.config["active_provider_id"] = provider_id
        self.config["active_model_id"] = model_id
        self._save()

    def get_active_config(self) -> Dict[str, str]:
        aid = self.config.get("active_provider_id")
        mid = self.config.get("active_model_id")

        for p in self.config["providers"]:
            if p["id"] == aid:
                return {
                    "base_url": p["base_url"],
                    "api_key": p["api_key"],
                    "model": mid,
                    "provider_name": p["name"],
                    "provider_id": p["id"]
                }
        return {}

    def get_all_providers(self) -> List[Dict]:
        # Return safe view (masked keys?)
        safe_providers = []
        for p in self.config["providers"]:
            safe_providers.append({
                "id": p["id"],
                "name": p["name"],
                "base_url": p["base_url"],
                "models": p["available_models"],
                "has_key": bool(p["api_key"])
            })
        return safe_providers
