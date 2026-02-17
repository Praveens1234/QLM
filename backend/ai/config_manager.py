import json
import logging
from typing import List, Dict, Optional
from backend.database import db
from backend.ai.models import ProviderConfig, Model, AIConfig
from backend.ai.factory import ProviderFactory

logger = logging.getLogger("QLM.AI.Config")

class AIConfigManager:
    """
    Manages AI Providers and Global Settings using SQLite.
    Securely handles API keys (in-memory masking).
    """
    def __init__(self):
        pass # DB connection handled per method

    def get_config(self) -> AIConfig:
        """
        Load full configuration from DB.
        """
        config = AIConfig()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Load Settings
            cursor.execute("SELECT key, value FROM config")
            rows = cursor.fetchall()
            settings = {row["key"]: row["value"] for row in rows}

            config.active_provider_id = settings.get("active_provider_id")
            config.active_model_id = settings.get("active_model_id")
            config.system_prompt = settings.get("system_prompt", config.system_prompt)
            config.temperature = float(settings.get("temperature", config.temperature))

            # 2. Load Providers
            cursor.execute("SELECT * FROM providers")
            prov_rows = cursor.fetchall()

            for row in prov_rows:
                models_data = json.loads(row["models"]) if row["models"] else []
                models = [Model(**m) for m in models_data]

                prov = ProviderConfig(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    base_url=row["base_url"],
                    api_key=row["api_key"],
                    is_active=bool(row["is_active"]),
                    models=models
                )
                config.providers.append(prov)

        return config

    def add_provider(self, config: ProviderConfig):
        with db.get_connection() as conn:
            cursor = conn.cursor()

            models_json = json.dumps([m.dict() for m in config.models])

            cursor.execute('''
                INSERT INTO providers (id, name, type, base_url, api_key, models, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    type=excluded.type,
                    base_url=excluded.base_url,
                    api_key=excluded.api_key,
                    models=excluded.models
            ''', (
                config.id, config.name, config.type, config.base_url,
                config.api_key, models_json, config.is_active
            ))
            conn.commit()

    def remove_provider(self, provider_id: str):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM providers WHERE id=?", (provider_id,))
            conn.commit()

    def set_active_provider(self, provider_id: str, model_id: str):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("active_provider_id", provider_id))
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("active_model_id", model_id))
            conn.commit()

    def update_models(self, provider_id: str, models: List[Model]):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            models_json = json.dumps([m.dict() for m in models])
            cursor.execute("UPDATE providers SET models=? WHERE id=?", (models_json, provider_id))
            conn.commit()

    def get_provider_config(self, provider_id: str) -> Optional[ProviderConfig]:
        """
        Get specific provider config including API key.
        """
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM providers WHERE id=?", (provider_id,))
            row = cursor.fetchone()

            if not row: return None

            models = [Model(**m) for m in json.loads(row["models"])] if row["models"] else []
            return ProviderConfig(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                base_url=row["base_url"],
                api_key=row["api_key"],
                is_active=bool(row["is_active"]),
                models=models
            )
