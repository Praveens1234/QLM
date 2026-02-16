from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, Resource
from starlette.responses import JSONResponse, Response
import asyncio
import logging
from backend.ai.tools import AITools
from backend.core.store import MetadataStore
from backend.core.strategy import StrategyLoader
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger("QLM.MCP")

# 1. Define Server
mcp_server = Server("QLM-MCP-Service")

# 2. Helpers to Bridge AITools -> MCP Tools
ai_tools = AITools()
metadata_store = MetadataStore()
strategy_loader = StrategyLoader()

# --- State Management ---
class MCPState:
    def __init__(self):
        self.is_active = True
        self.activity_log: List[Dict[str, Any]] = []
        self.max_log_size = 50

    def add_log(self, action: str, details: str, status: str = "success"):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
            "status": status
        }
        self.activity_log.insert(0, log_entry)
        if len(self.activity_log) > self.max_log_size:
            self.activity_log.pop()

mcp_state = MCPState()

def _convert_schema(openai_schema: dict) -> dict:
    if "function" in openai_schema:
        return openai_schema["function"]["parameters"]
    return openai_schema.get("parameters", {})

# 3. List Tools
@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    definitions = ai_tools.get_definitions()
    mcp_tools = []

    for d in definitions:
        func_def = d.get("function", {})
        mcp_tools.append(Tool(
            name=func_def.get("name"),
            description=func_def.get("description"),
            inputSchema=_convert_schema(d)
        ))

    mcp_tools.append(Tool(
        name="consult_skill",
        description="Retrieve expert knowledge/skill documentation.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "enum": ["coding", "market_analysis", "debugging", "general", "regime"]}
            },
            "required": ["topic"]
        }
    ))
    return mcp_tools

# 4. Call Tool
@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.info(f"MCP Call: {name} {arguments}")

    try:
        # Check active state
        if not mcp_state.is_active:
             mcp_state.add_log(name, "Service Disabled", "error")
             return [TextContent(type="text", text="Error: MCP Service is currently disabled.")]

        # Skills
        if name == "consult_skill":
            topic = arguments.get("topic")
            path = os.path.join("backend", "ai", "skills", f"{topic}.md")
            if os.path.exists(path):
                with open(path, "r") as f:
                    content = f.read()
                mcp_state.add_log(name, f"Read skill: {topic}")
                return [TextContent(type="text", text=content)]

            mcp_state.add_log(name, f"Skill not found: {topic}", "error")
            return [TextContent(type="text", text="Skill topic not found.")]

        # Standard Tools
        result = await ai_tools.execute(name, arguments)

        # Log Result
        status = "success"
        if isinstance(result, dict) and "error" in result:
            status = "error"

        mcp_state.add_log(name, json.dumps(arguments), status)

        text_result = json.dumps(result, default=str, indent=2)
        return [TextContent(type="text", text=text_result)]

    except Exception as e:
        logger.error(f"MCP Tool Error: {e}")
        mcp_state.add_log(name, str(e), "crash")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

# 5. List Resources
@mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    if not mcp_state.is_active: return []

    resources = []
    strategies = strategy_loader.list_strategies()
    for s in strategies:
        resources.append(Resource(
            uri=f"qlm://strategy/{s['name']}",
            name=f"Strategy: {s['name']} (v{s['latest_version']})",
            mimeType="text/x-python"
        ))

    datasets = metadata_store.list_datasets()
    for d in datasets:
        resources.append(Resource(
            uri=f"qlm://data/{d['id']}",
            name=f"Dataset: {d['symbol']} {d['timeframe']}",
            mimeType="application/octet-stream"
        ))
    return resources

# 6. Read Resource
@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    if not mcp_state.is_active: raise ValueError("MCP Disabled")

    scheme, path = uri.split("://")
    parts = path.split("/")

    if parts[0] == "strategy":
        name = parts[1]
        code = strategy_loader.get_strategy_code(name)
        if code:
            mcp_state.add_log("read_resource", uri)
            return code
        raise ValueError("Strategy not found")

    elif parts[0] == "data":
        ds_id = parts[1]
        meta = metadata_store.get_dataset(ds_id)
        if meta:
            mcp_state.add_log("read_resource", uri)
            return json.dumps(meta, indent=2, default=str)
        raise ValueError("Dataset not found")

    raise ValueError("Invalid Resource URI")

# 7. Prompt
@mcp_server.list_prompts()
async def list_prompts():
    from mcp.types import Prompt
    return [
        Prompt(
            name="senior_quant",
            description="Act as a Senior Quantitative Researcher for QLM.",
            arguments=[]
        )
    ]

@mcp_server.get_prompt()
async def get_prompt(name: str, arguments: dict):
    from mcp.types import GetPromptResult, PromptMessage, TextContent
    from backend.ai.agent import BASE_PROMPT

    if name == "senior_quant":
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=BASE_PROMPT)
                )
            ]
        )
    raise ValueError("Unknown prompt")

# 8. Transport & Management
sse = SseServerTransport("/api/mcp/messages")

async def handle_mcp_sse(request):
    if not mcp_state.is_active:
        return Response("MCP Service Disabled", status_code=503)

    # SseServerTransport connects and runs the server loop.
    # It writes directly to the ASGI send channel.
    # We must ensure we don't return None to Starlette/FastAPI route handler
    # which expects a Response object.
    # However, since sse.connect_sse manages the lifecycle and writes to stream,
    # we can't easily return a standard Response object that Starlette will then execute.
    #
    # The fix is to treat this as an ASGI app wrapper if possible, or return a Response
    # that doesn't conflict.
    #
    # But wait, request._send is the raw ASGI send. If sse uses it, the response is started.
    # Returning a Response object afterwards will cause an error (Response already started).
    #
    # Correct approach: The handler should probably NOT be a standard route handler
    # if it consumes the ASGI stream directly.
    # But keeping the current structure, we can return a custom Response that does nothing
    # on render, assuming SSE handled it.
    #
    # Actually, sse.connect_sse is a context manager.

    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

    # If we get here, connection closed.
    # We return a dummy response to satisfy type checker, though stream is closed.
    return Response("", status_code=200)

async def handle_mcp_messages(request):
    if not mcp_state.is_active:
        return Response("MCP Service Disabled", status_code=503)

    await sse.handle_post_message(request.scope, request.receive, request._send)

    # Return a response to satisfy Starlette's requirement.
    # Since handle_post_message likely sent a response (202 Accepted),
    # we need to be careful.
    # If it sent it, we can't send another.
    # The error "NoneType is not callable" means we returned None.
    # If we return a Response, Starlette calls it.

    # If we are effectively hijacking the request via `request._send`,
    # we should return a Response that does nothing.

    # However, simpler fix that often works with these hijacked handlers:
    # Return a Response that has already "sent" or a dummy if the stream is closed?
    # But handle_post_message might NOT close the stream immediately?

    # Actually, let's verify if handle_post_message writes the response.
    # Yes it does.
    # So we need to return a Response object that informs Starlette "I'm done".
    # Starlette doesn't have a "NoOpResponse".

    # Alternative: Raise a custom exception that is handled by doing nothing?
    # Or return a Response with background task?

    # Best Fix: Define these as pure ASGI handlers and mount them, instead of
    # adding them as standard routes that wrap Request/Response.
    # But main.py uses app.add_route which supports ASGI callable.
    # If we change signature to (scope, receive, send), Starlette treats it as ASGI app.

    return Response(status_code=202) # This might cause double-send if not careful, but let's try returning it.
    # If the previous await sent the headers, this will fail.
    # But the error was "NoneType is not callable", which means we returned None.
    # If we return Response, Starlette will call response(scope, receive, send).

    # Let's try changing to ASGI signature in main.py?
    # No, let's change these functions to be ASGI compliant and use app.add_route with ASGI.
    pass

# We will redefine these to be ASGI handlers directly to avoid the Request wrapper issue.
# But we need access to mcp_state.

async def handle_mcp_sse_asgi(scope, receive, send):
    if not mcp_state.is_active:
        response = Response("MCP Service Disabled", status_code=503)
        await response(scope, receive, send)
        return

    async with sse.connect_sse(scope, receive, send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

async def handle_mcp_messages_asgi(scope, receive, send):
    logger.info(f"MCP Messages ASGI: Method={scope.get('method')}, Path={scope.get('path')}")

    if not mcp_state.is_active:
        response = Response("MCP Service Disabled", status_code=503)
        await response(scope, receive, send)
        return

    await sse.handle_post_message(scope, receive, send)

# API Endpoints for Dashboard
async def get_mcp_status():
    return {
        "is_active": mcp_state.is_active,
        "logs": mcp_state.activity_log
    }

async def toggle_mcp(payload: Dict[str, bool]):
    mcp_state.is_active = payload.get("active", True)
    return {"status": "updated", "is_active": mcp_state.is_active}
