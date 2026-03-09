from mcp.server import Server
from mcp.types import Tool, TextContent, Resource, Prompt, GetPromptResult, PromptMessage
import asyncio
import logging
import time
from backend.core.store import MetadataStore
from backend.core.strategy import StrategyLoader
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import Request
from backend.api.mcp_session import session_manager
from fastapi.responses import JSONResponse
from backend.api.mcp_tools import MCPTools
from backend.core.diagnostics import diagnostics, EventLevel, EventCategory

logger = logging.getLogger("QLM.MCP")

mcp_server = Server("QLM")
installed_tools = MCPTools()

@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    """
    List available tools for the MCP Client.
    """
    definitions = installed_tools.get_definitions()
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
    Has a hard 180s global timeout to prevent zombie hangs.
    """
    start_time = time.time()
    
    diagnostics.record(EventLevel.INFO, EventCategory.MCP_TOOL_CALL,
        f"Tool call received: {name}",
        details={"tool": name, "args_keys": list(arguments.keys())})
    
    try:
        result = await asyncio.wait_for(
            installed_tools.execute(name, arguments),
            timeout=180.0
        )
        
        elapsed = round((time.time() - start_time) * 1000, 1)
        
        # Format result as text
        if isinstance(result, (dict, list)):
            text = json.dumps(result, indent=2, default=str)
        else:
            text = str(result)
        
        # Check for logical errors in result
        is_error = isinstance(result, dict) and "error" in result
        
        diagnostics.record(
            EventLevel.WARNING if is_error else EventLevel.INFO,
            EventCategory.MCP_TOOL_RESULT,
            f"Tool '{name}' completed in {elapsed}ms" + (f" (with error)" if is_error else ""),
            details={"tool": name, "elapsed_ms": elapsed, "result_size": len(text), "has_error": is_error})
            
        return [TextContent(type="text", text=text)]
    
    except asyncio.TimeoutError:
        elapsed = round((time.time() - start_time) * 1000, 1)
        diagnostics.record(EventLevel.CRITICAL, EventCategory.MCP_TIMEOUT,
            f"Tool '{name}' TIMED OUT after {elapsed}ms",
            details={"tool": name, "elapsed_ms": elapsed, "timeout_limit": 180000})
        
        return [TextContent(type="text", text=json.dumps({
            "error": f"Tool '{name}' timed out after 180 seconds.",
            "code": -32004,
            "suggestion": "The operation took too long. Try with a smaller dataset or simpler parameters."
        }))]
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 1)
        diagnostics.record(EventLevel.CRITICAL, EventCategory.CRASH,
            f"Tool '{name}' CRASHED after {elapsed}ms: {type(e).__name__}: {e}",
            details={"tool": name, "elapsed_ms": elapsed},
            error=e)
        
        return [TextContent(type="text", text=json.dumps({
            "error": f"Internal error: {str(e)}",
            "code": -32603
        }))]

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
        diagnostics.record(EventLevel.INFO, EventCategory.SERVER,
            f"MCP service toggled: active={mcp_transport.active}")
        return JSONResponse({"status": "updated", "is_active": mcp_transport.active})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
