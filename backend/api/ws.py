from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import logging
import asyncio
import json
from backend.core.events import event_bus

logger = logging.getLogger("QLM.API.WS")

router = APIRouter()

class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # Subscribe to EventBus
        event_bus.subscribe(self.broadcast_event)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WS Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast_event(self, message: Dict[str, Any]):
        """
        Callback for EventBus.
        """
        await self.broadcast(message)

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected clients.
        Optimized with asyncio.gather.
        """
        if not self.active_connections:
            return

        async def send_safe(connection):
            try:
                await connection.send_json(message)
                return True
            except Exception as e:
                return connection

        # Run all sends concurrently
        results = await asyncio.gather(*(send_safe(conn) for conn in self.active_connections))

        # Cleanup dead connections
        for res in results:
            if res is not True: # It's a dead connection object
                self.disconnect(res)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive / Handle incoming
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WS Endpoint Error: {e}")
        manager.disconnect(websocket)
