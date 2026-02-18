import json
import os
import logging
from typing import List, Dict, Any, Optional
from backend.database import db
from backend.core.config import settings

logger = logging.getLogger("QLM.AI.Config")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

class AIConfigManager:
    """
    Manages AI Providers, Models, and Defaults using SQLite.
    Falls back to Environment Variables via `backend.core.config.settings` if DB is empty.
    Migrates from legacy JSON if present.
    """
    def __init__(self):
        self._ensure_migration()
        self._ensure_env_defaults()

    def _ensure_env_defaults(self):
        """
        Populate DB with providers from environment variables if not present.
        """
        # OpenAI
        if settings.OPENAI_API_KEY:
            self.add_provider("OpenAI", "https://api.openai.com/v1", settings.OPENAI_API_KEY)

        # Anthropic
        if settings.ANTHROPIC_API_KEY:
            self.add_provider("Anthropic", "https://api.anthropic.com", settings.ANTHROPIC_API_KEY)

    def _ensure_migration(self):
        """
        Migrate legacy JSON config to SQLite if needed.
        """
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)

                # Check if DB is empty
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM providers")
                    if cursor.fetchone()[0] == 0:
                        logger.info("Migrating legacy config.json to SQLite...")

                        # Handle old schema (flat) vs new schema (providers list)
                        if "providers" in data:
                            for p in data["providers"]:
                                cursor.execute('''
                                    INSERT INTO providers (id, name, base_url, api_key, models, is_active)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (
                                    p["id"], p["name"], p["base_url"], p["api_key"],
                                    json.dumps(p.get("available_models", [])),
                                    False
                                ))

                            # Set active
                            self._set_active_internal(cursor, data.get("active_provider_id", ""), data.get("active_model_id", ""))

                        elif "api_key" in data: # Very old flat schema
                            prov_id = "default"
                            cursor.execute('''
                                INSERT INTO providers (id, name, base_url, api_key, models, is_active)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (
                                prov_id, "Default Provider", data.get("base_url"), data.get("api_key"),
                                json.dumps([data.get("model")] if data.get("model") else []),
                                True
                            ))
                            self._set_active_internal(cursor, prov_id, data.get("model", ""))

                    conn.commit()

                # Rename legacy file to avoid re-migration
                os.rename(CONFIG_PATH, CONFIG_PATH + ".bak")

            except Exception as e:
                logger.error(f"Migration failed: {e}")

    def add_provider(self, name: str, base_url: str, api_key: str) -> str:
        provider_id = name.lower().replace(" ", "_")

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Upsert
            cursor.execute('''
                INSERT INTO providers (id, name, base_url, api_key, models)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    base_url=excluded.base_url,
                    api_key=excluded.api_key
            ''', (provider_id, name, base_url, api_key, json.dumps([])))

            # If no active provider, set this one
            cursor.execute("SELECT value FROM config WHERE key='active_provider_id'")
            if not cursor.fetchone():
                self._set_active_internal(cursor, provider_id, "")

            conn.commit()

        return provider_id

    def set_models(self, provider_id: str, models: List[str]):
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Update models
            cursor.execute("UPDATE providers SET models=? WHERE id=?", (json.dumps(models), provider_id))

            if cursor.rowcount == 0:
                 raise ValueError("Provider not found")

            # Auto-set active model if current active provider has no model set
            cursor.execute("SELECT value FROM config WHERE key='active_provider_id'")
            row = cursor.fetchone()
            active_pid = row[0] if row else None

            cursor.execute("SELECT value FROM config WHERE key='active_model_id'")
            row_m = cursor.fetchone()
            active_mid = row_m[0] if row_m else ""

            if active_pid == provider_id and not active_mid and models:
                self._set_active_internal(cursor, provider_id, models[0])

            conn.commit()

    def _set_active_internal(self, cursor, provider_id: str, model_id: str):
        # Check provider exists
        cursor.execute("SELECT models FROM providers WHERE id=?", (provider_id,))
        row = cursor.fetchone()
        if not row:
            if not provider_id: pass
            else: logger.warning(f"Setting active provider {provider_id} but it doesn't exist in DB.")

        cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("active_provider_id", provider_id))
        cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("active_model_id", model_id))

    def set_active(self, provider_id: str, model_id: str):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            self._set_active_internal(cursor, provider_id, model_id)
            conn.commit()

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full provider details (including API Key).
        Use internally only.
        """
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, base_url, api_key, models FROM providers WHERE id=?", (provider_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "base_url": row["base_url"],
                    "api_key": row["api_key"],
                    "models": json.loads(row["models"]) if row["models"] else []
                }
        return None

    def get_active_config(self) -> Dict[str, str]:
        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM config WHERE key='active_provider_id'")
            pid_row = cursor.fetchone()
            pid = pid_row[0] if pid_row else None

            cursor.execute("SELECT value FROM config WHERE key='active_model_id'")
            mid_row = cursor.fetchone()
            mid = mid_row[0] if mid_row else ""

            if not pid:
                return {}

            cursor.execute("SELECT name, base_url, api_key FROM providers WHERE id=?", (pid,))
            p_row = cursor.fetchone()

            if not p_row:
                return {}

            return {
                "base_url": p_row["base_url"],
                "api_key": p_row["api_key"],
                "model": mid,
                "provider_name": p_row["name"]
            }

    def get_all_providers(self) -> List[Dict]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, base_url, api_key, models FROM providers")
            rows = cursor.fetchall()

            safe_providers = []
            for row in rows:
                safe_providers.append({
                    "id": row["id"],
                    "name": row["name"],
                    "base_url": row["base_url"],
                    "models": json.loads(row["models"]) if row["models"] else [],
                    "has_key": bool(row["api_key"])
                })
            return safe_providers
