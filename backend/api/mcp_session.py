from typing import Dict, Any, List, Optional
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger("QLM.MCP.Session")

class Session:
    """
    Represents a single MCP client connection/session.
    Isolates state, logs, and context.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now(timezone.utc)
        self.activity_log: List[Dict[str, Any]] = []
        self.max_log_size = 100
        self.context: Dict[str, Any] = {} # Isolated variable storage if needed

    def add_log(self, action: str, details: str, status: str = "success"):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
            "status": status,
            "session_id": self.session_id
        }
        self.activity_log.insert(0, log_entry)
        if len(self.activity_log) > self.max_log_size:
            self.activity_log.pop()

class SessionManager:
    """
    Manages active MCP sessions.
    """
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.global_log: List[Dict[str, Any]] = [] # For dashboard visibility of all actions
        self.max_global_log = 200

    def create_session(self) -> Session:
        sid = str(uuid.uuid4())
        session = Session(sid)
        self.sessions[sid] = session
        logger.info(f"MCP Session Created: {sid}")
        return session

    def get_session(self, sid: str) -> Optional[Session]:
        return self.sessions.get(sid)

    def remove_session(self, sid: str):
        if sid in self.sessions:
            del self.sessions[sid]
            logger.info(f"MCP Session Removed: {sid}")

    def log_global(self, entry: Dict[str, Any]):
        """Append to global dashboard log."""
        self.global_log.insert(0, entry)
        if len(self.global_log) > self.max_global_log:
            self.global_log.pop()

# Singleton
session_manager = SessionManager()
