from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import traceback
from pydantic import BaseModel

from backend.core.exceptions import QLMError, StrategyError, DataError, SystemError, OptimizationError
from backend.utils.logging import configure_logging, get_logger
from backend.api.error_handler import global_exception_handler as detailed_exception_handler

# Configure Logging
configure_logging()
logger = get_logger("QLM.Main")

app = FastAPI(title="QuantLogic Framework (QLM)", version="1.0.0")

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

@app.get("/health")
async def health_check():
    return {"status": "ok", "system": "QLM"}

# Serve Frontend
if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8010, reload=True)
