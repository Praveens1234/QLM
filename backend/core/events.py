from typing import List, Dict, Any, Callable
import logging
import asyncio

logger = logging.getLogger("QLM.Events")

class EventBus:
    """
    Simple in-memory event bus for broadcasting messages to WebSockets.
    """
    def __init__(self):
        self.subscribers: List[Callable[[Dict[str, Any]], Any]] = []

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        self.subscribers.append(callback)

    async def publish(self, event_type: str, data: Dict[str, Any]):
        message = {"type": event_type, "data": data}
        # Run callbacks (fire and forget usually, but here we await if async)
        for sub in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(sub):
                    await sub(message)
                else:
                    sub(message)
            except Exception as e:
                logger.error(f"EventBus dispatch failed: {e}")

event_bus = EventBus()
