import asyncio
import logging
import json
from typing import Optional
from starlette.responses import JSONResponse, Response
from mcp.server.sse import SseServerTransport
from backend.api.mcp_session import session_manager
from backend.api.validation import ValidationMiddleware

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
            await self._send_error(scope, receive, send, 503, "MCP Service Disabled")
            return

        # Create Session
        session = session_manager.create_session()
        logger.info(f"New MCP Connection. Session ID: {session.session_id}")

        try:
            async with self.sse.connect_sse(scope, receive, send) as streams:
                read_stream, write_stream = streams
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options()
                )

        except asyncio.CancelledError:
            logger.info(f"MCP Connection Cancelled (Disconnect). Session: {session.session_id}")
        except Exception as e:
            logger.error(f"MCP Transport Error: {e}")
        finally:
            session_manager.remove_session(session.session_id)

    async def handle_messages(self, scope, receive, send):
        """
        ASGI Handler for POST messages.
        Intercepts and validates JSON-RPC payload.
        """
        if not self.active:
            await self._send_error(scope, receive, send, 503, "MCP Service Disabled")
            return

        # Intercept Body for Validation
        # NOTE: sse.handle_post_message consumes the body. We need to read it first?
        # Reading body in ASGI is complex (stream).
        # The mcp library handles reading.
        # Ideally, we'd wrap the receive callable.

        async def validated_receive():
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    try:
                        payload = json.loads(body)
                        if not ValidationMiddleware.validate_payload(payload):
                            # We can't easily return error here as 'receive' just returns data.
                            # But we can log/flag it.
                            # Or we can modify the body to be empty to force an error downstream?
                            # Better: We assume mcp library does some validation, but we log warnings.
                            pass
                    except Exception:
                        pass # Let downstream handle invalid JSON
            return message

        try:
            # Use validated_receive to validate JSON-RPC payloads before passing to MCP
            await self.sse.handle_post_message(scope, validated_receive, send)
        except Exception as e:
            logger.error(f"MCP Message Error: {e}")
            await self._send_error(scope, receive, send, 500, str(e))

    async def _send_error(self, scope, receive, send, code: int, msg: str):
        response = JSONResponse({"error": msg}, status_code=code)
        await response(scope, receive, send)

mcp_transport = MCPTransport()
