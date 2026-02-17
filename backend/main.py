from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Route, Mount
import os
import traceback
from pydantic import BaseModel

from backend.core.exceptions import QLMError, StrategyError, DataError, SystemError, OptimizationError
from backend.utils.logging import configure_logging, get_logger

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

# Global Exception Handler
@app.exception_handler(QLMError)
async def qlm_exception_handler(request: Request, exc: QLMError):
    logger.error("QLM Error", error=str(exc), type=exc.__class__.__name__, details=exc.details)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": str(exc), "type": exc.__class__.__name__, "details": exc.details},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Global Unhandled Exception", error=str(exc), traceback=traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal Server Error", "message": str(exc)},
    )

# API Router
from backend.api import router as api_router
from backend.api import dashboard
from backend.api import ai_settings # New Settings API

app.include_router(api_router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(ai_settings.router, prefix="/api")

# MCP Transport & Management
from backend.api.mcp import handle_mcp_sse, handle_mcp_messages, get_mcp_status, toggle_mcp

class ASGIWrapper:
    """Helper to expose a raw ASGI handler as a Starlette endpoint."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)

# Add MCP Routes
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
