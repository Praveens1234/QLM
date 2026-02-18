from typing import Dict, Any
import logging
import json
from datetime import datetime, timezone
from backend.database import db
from backend.core.retry import db_retry

logger = logging.getLogger("QLM.Audit")

class AuditLogger:
    """
    Persists a secure audit trail of all MCP actions to SQLite.
    """
    def __init__(self):
        pass

    @db_retry
    def log_action(self, session_id: str, action: str, details: Dict[str, Any]):
        """
        Log an action to the audit_logs table.
        """
        try:
            # Mask sensitive fields if necessary (basic implementation)
            safe_details = details.copy()
            if "api_key" in safe_details:
                safe_details["api_key"] = "***"

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO audit_logs (id, session_id, action, details, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    str(uuid.uuid4()),
                    session_id,
                    action,
                    json.dumps(safe_details, default=str),
                    datetime.now(timezone.utc).isoformat()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

# Singleton
import uuid
audit_logger = AuditLogger()
