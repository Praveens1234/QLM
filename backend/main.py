from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import asyncio
import traceback
from pydantic import BaseModel

from backend.core.exceptions import QLMError, StrategyError, DataError, QLMSystemError, OptimizationError
from backend.core.logging import configure_logging, get_logger
from backend.api.error_handler import global_exception_handler as detailed_exception_handler
from backend.core.diagnostics import diagnostics, EventLevel, EventCategory

# Configure Logging
configure_logging()
logger = get_logger("QLM.Main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup/shutdown events."""
    diagnostics.record(EventLevel.INFO, EventCategory.SERVER, "QLM Server starting up")
    asyncio.create_task(diagnostics.start_health_monitor(interval=30))
    yield

app = FastAPI(title="QuantLogic Framework (QLM)", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use centralized exception handler
app.add_exception_handler(Exception, detailed_exception_handler)

# API Router
from backend.api import router as api_router
from backend.api import dashboard
app.include_router(api_router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")

# MCP Transport & Management
from backend.api.mcp import handle_mcp_sse, handle_mcp_messages, get_mcp_status, toggle_mcp

class ASGIWrapper:
    """Helper to expose a raw ASGI handler as a Starlette endpoint."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)

# Add MCP Routes using ASGIWrapper via add_route (prevents auto-wrapping in Request/Response)
app.add_route("/api/mcp/sse", ASGIWrapper(handle_mcp_sse), methods=["GET"])
app.add_route("/api/mcp/messages", ASGIWrapper(handle_mcp_messages), methods=["POST"])

# Standard API routes for MCP Status
app.add_api_route("/api/mcp/status", get_mcp_status, methods=["GET"])
app.add_api_route("/api/mcp/toggle", toggle_mcp, methods=["POST"])

# Diagnostics API
async def get_diagnostics(request: Request):
    """Get system diagnostics summary and recent events."""
    summary = diagnostics.get_summary()
    return JSONResponse(summary)

async def get_diagnostics_events(request: Request):
    """Get filtered diagnostic events."""
    limit = int(request.query_params.get("limit", 50))
    level = request.query_params.get("level", None)
    category = request.query_params.get("category", None)
    events = diagnostics.get_events(limit=limit, level=level, category=category)
    return JSONResponse({"events": events, "total": len(events)})

app.add_api_route("/api/diagnostics", get_diagnostics, methods=["GET"])
app.add_api_route("/api/diagnostics/events", get_diagnostics_events, methods=["GET"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "system": "QLM"}

# Serve Frontend
if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    # CRITICAL: reload=True causes ZOMBIE DEADLOCKS when MCP clients are connected.
    # Any .py file written to strategies/ (via create_strategy, validate_strategy)
    # triggers uvicorn reload, which blocks on the SSE connection that can't close.
    # On Windows, watchfiles ignores reload_dirs and monitors the full CWD.
    # Use QLM_DEV_RELOAD=1 env var ONLY for local dev WITHOUT MCP clients.
    dev_reload = os.environ.get("QLM_DEV_RELOAD", "0") == "1"
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8010,
        reload=dev_reload,
        reload_dirs=["backend"] if dev_reload else [],
    )
