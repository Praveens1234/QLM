from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone
from backend.database import db
from backend.core.retry import db_retry

logger = logging.getLogger("QLM.AI.Telemetry")

class AITelemetry:
    """
    Tracks AI Token Usage and Costs.
    """
    def __init__(self):
        self._ensure_table()

    @db_retry
    def _ensure_table(self):
        with db.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ai_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    provider TEXT,
                    model TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    cost_usd REAL
                )
            ''')
            conn.commit()

    @db_retry
    def record_usage(self, provider: str, model: str, usage: Dict[str, int], cost_estimate: float = 0.0):
        try:
            with db.get_connection() as conn:
                conn.execute('''
                    INSERT INTO ai_usage (provider, model, prompt_tokens, completion_tokens, total_tokens, cost_usd)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    provider,
                    model,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    usage.get("total_tokens", 0),
                    cost_estimate
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")

    def get_stats(self) -> Dict[str, Any]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(total_tokens), SUM(cost_usd) FROM ai_usage")
            row = cursor.fetchone()
            return {
                "total_tokens": row[0] or 0,
                "total_cost": round(row[1] or 0.0, 4)
            }

ai_telemetry = AITelemetry()
