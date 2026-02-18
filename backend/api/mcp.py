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
from starlette.responses import JSONResponse
from backend.api.mcp_session import session_manager
from backend.api.transport import mcp_transport

logger = logging.getLogger("QLM.MCP")

# 1. Define Server
mcp_server = Server("QLM-MCP-Service")

# 2. Helpers
ai_tools = AITools()
metadata_store = MetadataStore()
strategy_loader = StrategyLoader()

def _convert_schema(openai_schema: dict) -> dict:
    if "function" in openai_schema:
        return openai_schema["function"]["parameters"]
    return openai_schema.get("parameters", {})

# 3. List Tools
@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    try:
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
                "properties": {"topic": {"type": "string", "enum": ["coding", "market_analysis", "debugging", "general", "regime"]}},
                "required": ["topic"]
            }
        ))
        return mcp_tools
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return []

# 4. Call Tool
@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # logger.info(f"MCP Call: {name} {arguments}") # Removed verbose log

    # Ideally, we get session ID from context, but MCP lib doesn't pass request context yet.
    # We log to global dashboard for now.
    session_manager.log_global({"action": name, "args": arguments, "timestamp": datetime.now(timezone.utc).isoformat()})

    try:
        if name == "consult_skill":
            topic = arguments.get("topic")
            path = os.path.join("backend", "ai", "skills", f"{topic}.md")
            if os.path.exists(path):
                with open(path, "r") as f:
                    return [TextContent(type="text", text=f.read())]
            return [TextContent(type="text", text="Skill topic not found.")]

        result = await ai_tools.execute(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, default=str, indent=2))]

    except Exception as e:
        logger.error(f"MCP Tool Error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

# 5. List Resources
@mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    try:
        resources = []
        strategies = await asyncio.to_thread(strategy_loader.list_strategies)
        for s in strategies:
            resources.append(Resource(
                uri=f"qlm://strategy/{s['name']}",
                name=f"Strategy: {s['name']} (v{s['latest_version']})",
                mimeType="text/x-python"
            ))
        datasets = await asyncio.to_thread(metadata_store.list_datasets)
        for d in datasets:
            resources.append(Resource(
                uri=f"qlm://data/{d['id']}",
                name=f"Dataset: {d['symbol']} {d['timeframe']}",
                mimeType="application/octet-stream"
            ))
        return resources
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        return []

# 6. Read Resource
@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    try:
        scheme, path = uri.split("://")
        parts = path.split("/")
        if parts[0] == "strategy":
            code = strategy_loader.get_strategy_code(parts[1])
            if code: return code
            raise ValueError("Strategy not found")
        elif parts[0] == "data":
            meta = metadata_store.get_dataset(parts[1])
            if meta: return json.dumps(meta, indent=2, default=str)
            raise ValueError("Dataset not found")
        raise ValueError("Invalid Resource URI")
    except Exception as e:
         logger.error(f"Error reading resource {uri}: {e}")
         raise e

# 7. Prompt
@mcp_server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [Prompt(name="senior_quant", description="Act as a Senior Quantitative Researcher.", arguments=[])]

@mcp_server.get_prompt()
async def get_prompt(name: str, arguments: dict) -> GetPromptResult:
    from backend.ai.agent import BASE_PROMPT
    if name == "senior_quant":
        return GetPromptResult(messages=[PromptMessage(role="user", content=TextContent(type="text", text=BASE_PROMPT))])
    raise ValueError("Unknown prompt")

# 8. ASGI Handlers (Delegated to Transport)
async def handle_mcp_sse(scope, receive, send):
    await mcp_transport.handle_sse(scope, receive, send, mcp_server)

async def handle_mcp_messages(scope, receive, send):
    await mcp_transport.handle_messages(scope, receive, send)

# API Endpoints
async def get_mcp_status(request):
    return JSONResponse({
        "is_active": mcp_transport.active,
        "logs": session_manager.global_log
    })

async def toggle_mcp(request):
    try:
        payload = await request.json()
        mcp_transport.active = payload.get("active", True)
        return JSONResponse({"status": "updated", "is_active": mcp_transport.active})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
