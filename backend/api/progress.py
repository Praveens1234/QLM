from typing import Dict, Any, Callable
import asyncio
from backend.core.events import event_bus

class ProgressReporter:
    """
    Standardized progress reporting compatible with MCP Notifications.
    """
    def __init__(self, session_id: str, task_name: str, total_steps: int = 100):
        self.session_id = session_id
        self.task_name = task_name
        self.total_steps = total_steps
        self.current_step = 0

    async def update(self, progress_pct: float, message: str, data: Dict[str, Any] = None):
        """
        Send progress update via EventBus.
        """
        self.current_step = progress_pct # Assuming simple pct mapping

        payload = {
            "jsonrpc": "2.0",
            "method": "notifications/progress",
            "params": {
                "progressToken": self.session_id, # Use session ID as token for now
                "data": {
                    "kind": "report",
                    "percentage": progress_pct,
                    "message": f"{self.task_name}: {message}",
                    "details": data
                }
            }
        }

        # Publish to event bus, which WS manager subscribes to
        # Note: WS manager needs to route this to specific client if possible,
        # or broadcast. Currently we broadcast.
        await event_bus.publish("mcp_notification", payload)

    def get_callback(self) -> Callable:
        """
        Returns a sync wrapper for the async update, suitable for BacktestEngine.
        """
        def callback(pct: float, msg: str, data: Dict):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.update(pct, msg, data))
            except RuntimeError:
                pass
        return callback
