from typing import Dict, Any, List, Callable
import logging
import asyncio

logger = logging.getLogger("QLM.Events")

class EventBus:
    """
    Simple in-memory event bus for broadcasting messages to WebSockets.
    Also handles MCP Resource Subscriptions.
    """
    def __init__(self):
        self.subscribers: List[Callable[[Dict[str, Any]], Any]] = []
        self.resource_subscribers: Dict[str, List[Callable[[str], Any]]] = {} # uri -> [callbacks]

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        self.subscribers.append(callback)

    def subscribe_resource(self, uri: str, callback: Callable[[str], Any]):
        if uri not in self.resource_subscribers:
            self.resource_subscribers[uri] = []
        self.resource_subscribers[uri].append(callback)

    async def publish(self, event_type: str, data: Dict[str, Any]):
        message = {"type": event_type, "data": data}
        for sub in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(sub):
                    await sub(message)
                else:
                    sub(message)
            except Exception as e:
                logger.error(f"EventBus dispatch failed: {e}")

    async def notify_resource_update(self, uri: str):
        """
        Notify subscribers that a specific resource has changed.
        """
        if uri in self.resource_subscribers:
            for cb in self.resource_subscribers[uri]:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(uri)
                    else:
                        cb(uri)
                except Exception as e:
                    logger.error(f"Resource notify failed: {e}")

event_bus = EventBus()
