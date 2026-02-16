from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("QLM.Main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("QLM System Starting...")
    yield
    # Shutdown
    logger.info("QLM System Shutting Down...")

app = FastAPI(title="QuantLogic Framework (QLM)", version="2.0.0", lifespan=lifespan)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
from backend.api import router as api_router
app.include_router(api_router, prefix="/api")

# MCP Transport & Management
from backend.api.mcp import handle_mcp_sse, handle_mcp_messages, get_mcp_status, toggle_mcp

class ToggleRequest(BaseModel):
    active: bool

app.add_route("/api/mcp/sse", handle_mcp_sse)
app.add_route("/api/mcp/messages", handle_mcp_messages, methods=["POST"])
app.add_api_route("/api/mcp/status", get_mcp_status, methods=["GET"])
app.add_api_route("/api/mcp/toggle", toggle_mcp, methods=["POST"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "system": "QLM"}

# Serve Frontend
# Ensure frontend directory exists
if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    # Updated to 0.0.0.0 and port 8010 as requested
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8010, reload=True)
