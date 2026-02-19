from mcp.server import Server
from mcp.types import Tool, TextContent, Resource, Prompt, GetPromptResult, PromptMessage
import asyncio
import logging
from backend.ai.tools import AITools
from backend.core.store import MetadataStore
from backend.core.strategy import StrategyLoader
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import Request
from backend.api.mcp_session import session_manager
from fastapi.responses import JSONResponse # Assuming JSONResponse is imported from fastapi.responses

logger = logging.getLogger("QLM.MCP")

mcp_server = Server("QLM")
ai_tools = AITools()

@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    """
    List available tools for the MCP Client.
    """
    definitions = ai_tools.get_definitions()
    tools = []
    for d in definitions:
        func = d["function"]
        tools.append(Tool(
            name=func["name"],
            description=func["description"],
            inputSchema=func["parameters"]
        ))
    return tools

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """
    Execute a tool call from the MCP Client.
    """
    try:
        result = await ai_tools.execute(name, arguments)
        
        # Format result as text
        if isinstance(result, (dict, list)):
            text = json.dumps(result, indent=2, default=str)
        else:
            text = str(result)
            
        return [TextContent(type="text", text=text)]
    except Exception as e:
        logger.error(f"MCP Tool Execution Error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def handle_mcp_sse(scope, receive, send):
    from backend.api.transport import mcp_transport
    await mcp_transport.handle_sse(scope, receive, send, mcp_server)

async def handle_mcp_messages(scope, receive, send):
    from backend.api.transport import mcp_transport
    await mcp_transport.handle_messages(scope, receive, send)

# API Endpoints
async def get_mcp_status(request: Request):
    from backend.api.transport import mcp_transport
    return JSONResponse({
        "is_active": mcp_transport.active,
        "logs": session_manager.global_log
    })

async def toggle_mcp(request: Request):
    try:
        from backend.api.transport import mcp_transport
        payload = await request.json()
        mcp_transport.active = payload.get("active", True)
        return JSONResponse({"status": "updated", "is_active": mcp_transport.active})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
