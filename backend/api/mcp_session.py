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
        self.last_accessed = self.created_at
        self.activity_log: List[Dict[str, Any]] = []
        self.max_log_size = 100
        self.context: Dict[str, Any] = {} # Isolated variable storage if needed

    def touch(self):
        self.last_accessed = datetime.now(timezone.utc)

    def add_log(self, action: str, details: str, status: str = "success"):
        self.touch()
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
    Includes auto-cleanup of inactive sessions.
    """
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.global_log: List[Dict[str, Any]] = [] # For dashboard visibility of all actions
        self.max_global_log = 200
        self._cleanup_task = None

    async def start_cleanup_loop(self):
        """Starts background cleanup task."""
        if self._cleanup_task: return
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())

    async def _cleanup_worker(self):
        while True:
            await asyncio.sleep(300) # Check every 5 minutes
            try:
                now = datetime.now(timezone.utc)
                to_remove = []
                for sid, sess in self.sessions.items():
                    if (now - sess.last_accessed).total_seconds() > 3600: # 1 Hour Timeout
                        to_remove.append(sid)

                for sid in to_remove:
                    self.remove_session(sid)
                    logger.info(f"Auto-removed inactive session: {sid}")
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")

    def create_session(self) -> Session:
        sid = str(uuid.uuid4())
        session = Session(sid)
        self.sessions[sid] = session
        logger.info(f"MCP Session Created: {sid}")
        # Ensure cleanup is running
        if not self._cleanup_task:
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_worker())
            except RuntimeError:
                pass # Loop not started yet
        return session

    def get_session(self, sid: str) -> Optional[Session]:
        sess = self.sessions.get(sid)
        if sess: sess.touch()
        return sess

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
