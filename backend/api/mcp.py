from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, Resource
import asyncio
import logging
from backend.ai.tools import AITools
from backend.core.store import MetadataStore
from backend.core.strategy import StrategyLoader
import os
import json

logger = logging.getLogger("QLM.MCP")

# 1. Define Server
mcp_server = Server("QLM-MCP-Service")

# 2. Helpers to Bridge AITools -> MCP Tools
ai_tools = AITools()
metadata_store = MetadataStore()
strategy_loader = StrategyLoader()

def _convert_schema(openai_schema: dict) -> dict:
    """
    Convert OpenAI tool schema to MCP input schema.
    OpenAI: { "type": "function", "function": { "name": "...", "parameters": {...} } }
    MCP: { "type": "object", "properties": {...}, "required": [...] }
    """
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

    # Add Skills Access Tool
    mcp_tools.append(Tool(
        name="consult_skill",
        description="Retrieve expert knowledge/skill documentation (e.g., coding, market_analysis).",
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
        # Handle Special Skills Tool
        if name == "consult_skill":
            topic = arguments.get("topic")
            path = os.path.join("backend", "ai", "skills", f"{topic}.md")
            if os.path.exists(path):
                with open(path, "r") as f:
                    content = f.read()
                return [TextContent(type="text", text=content)]
            return [TextContent(type="text", text="Skill topic not found.")]

        # Handle Standard AITools
        result = await ai_tools.execute(name, arguments)

        # Convert result to string/json
        text_result = json.dumps(result, default=str, indent=2)
        return [TextContent(type="text", text=text_result)]

    except Exception as e:
        logger.error(f"MCP Tool Error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

# 5. List Resources (Strategies & Data)
@mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    resources = []

    # List Strategies
    strategies = strategy_loader.list_strategies()
    for s in strategies:
        resources.append(Resource(
            uri=f"qlm://strategy/{s['name']}",
            name=f"Strategy: {s['name']} (v{s['latest_version']})",
            mimeType="text/x-python"
        ))

    # List Datasets
    datasets = metadata_store.list_datasets()
    for d in datasets:
        resources.append(Resource(
            uri=f"qlm://data/{d['id']}",
            name=f"Dataset: {d['symbol']} {d['timeframe']}",
            mimeType="application/octet-stream" # Parquet
        ))

    return resources

# 6. Read Resource
@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    scheme, path = uri.split("://")
    parts = path.split("/")

    if parts[0] == "strategy":
        name = parts[1]
        code = strategy_loader.get_strategy_code(name)
        if code:
            return code
        raise ValueError("Strategy not found")

    elif parts[0] == "data":
        # We probably shouldn't dump binary parquet to text, return metadata instead?
        # Or return a sample.
        ds_id = parts[1]
        meta = metadata_store.get_dataset(ds_id)
        if meta:
            return json.dumps(meta, indent=2, default=str)
        raise ValueError("Dataset not found")

    raise ValueError("Invalid Resource URI")

# 7. Prompt (Persona)
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

# 8. Transport Object (to be used by FastAPI)
sse = SseServerTransport("/api/mcp/messages")

async def handle_mcp_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

async def handle_mcp_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)
