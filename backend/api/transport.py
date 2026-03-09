import asyncio
import logging
import json
from typing import Optional
from starlette.responses import JSONResponse, Response
from mcp.server.sse import SseServerTransport
from backend.api.mcp_session import session_manager
from backend.api.validation import ValidationMiddleware
from backend.core.diagnostics import diagnostics, EventLevel, EventCategory

logger = logging.getLogger("QLM.MCP.Transport")

class MCPTransport:
    """
    Encapsulates the MCP Server-Sent Events (SSE) transport logic.
    Handles connection lifecycle, session creation, and keep-alives.
    """

    def __init__(self, endpoint_url: str = "/api/mcp/messages"):
        self.sse = SseServerTransport(endpoint_url)
        self.active = True

    async def handle_sse(self, scope, receive, send, mcp_server):
        """
        ASGI Handler for SSE connection (GET).
        """
        if not self.active:
            diagnostics.record(EventLevel.WARNING, EventCategory.MCP_TRANSPORT,
                "SSE rejected: MCP service is disabled")
            await self._send_error(scope, receive, send, 503, "MCP Service Disabled")
            return

        # Create Session
        session = session_manager.create_session()
        diagnostics.record(EventLevel.INFO, EventCategory.MCP_TRANSPORT,
            f"SSE connection opened",
            details={"session_id": session.session_id})

        try:
            async with self.sse.connect_sse(scope, receive, send) as streams:
                read_stream, write_stream = streams
                diagnostics.record(EventLevel.INFO, EventCategory.MCP_TRANSPORT,
                    f"SSE streams established, running MCP server",
                    details={"session_id": session.session_id})
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options()
                )

        except asyncio.CancelledError:
            diagnostics.record(EventLevel.INFO, EventCategory.MCP_TRANSPORT,
                f"SSE connection cancelled (client disconnect)",
                details={"session_id": session.session_id})
        except Exception as e:
            diagnostics.record(EventLevel.ERROR, EventCategory.MCP_TRANSPORT,
                f"SSE transport crash: {type(e).__name__}: {e}",
                details={"session_id": session.session_id},
                error=e)
        finally:
            session_manager.remove_session(session.session_id)
            diagnostics.record(EventLevel.INFO, EventCategory.MCP_TRANSPORT,
                f"SSE connection closed, session cleaned up",
                details={"session_id": session.session_id})

    async def handle_messages(self, scope, receive, send):
        """
        ASGI Handler for POST messages.
        Intercepts and validates JSON-RPC payload.
        """
        if not self.active:
            diagnostics.record(EventLevel.WARNING, EventCategory.MCP_TRANSPORT,
                "POST message rejected: MCP service is disabled")
            await self._send_error(scope, receive, send, 503, "MCP Service Disabled")
            return

        captured_method = None

        async def validated_receive():
            nonlocal captured_method
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    try:
                        payload = json.loads(body)
                        captured_method = payload.get("method", "unknown")
                        if not ValidationMiddleware.validate_payload(payload):
                            diagnostics.record(EventLevel.WARNING, EventCategory.MCP_TRANSPORT,
                                f"Invalid JSON-RPC payload received",
                                details={"method": captured_method, "payload_size": len(body)})
                    except Exception as e:
                        diagnostics.record(EventLevel.WARNING, EventCategory.MCP_TRANSPORT,
                            f"Failed to parse incoming message: {e}",
                            details={"body_size": len(body)})
            return message

        try:
            await self.sse.handle_post_message(scope, validated_receive, send)
            diagnostics.record(EventLevel.DEBUG, EventCategory.MCP_TRANSPORT,
                f"POST message handled successfully",
                details={"method": captured_method})
        except Exception as e:
            diagnostics.record(EventLevel.ERROR, EventCategory.MCP_TRANSPORT,
                f"POST message handler crash: {type(e).__name__}: {e}",
                details={"method": captured_method},
                error=e)
            try:
                await self._send_error(scope, receive, send, 500, str(e))
            except Exception:
                diagnostics.record(EventLevel.ERROR, EventCategory.MCP_TRANSPORT,
                    "Failed to send error response (connection may already be closed)")

    async def _send_error(self, scope, receive, send, code: int, msg: str):
        response = JSONResponse({"error": msg}, status_code=code)
        await response(scope, receive, send)

mcp_transport = MCPTransport()
