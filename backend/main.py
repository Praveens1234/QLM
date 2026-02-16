from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from pydantic import BaseModel

app = FastAPI(title="QuantLogic Framework (QLM)", version="1.0.0")

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
from backend.api.mcp import handle_mcp_sse_asgi, handle_mcp_messages_asgi, get_mcp_status, toggle_mcp

class ToggleRequest(BaseModel):
    active: bool

# We use the raw ASGI handlers to avoid Starlette Response wrapping issues with SSE
# To ensure Starlette detects these as ASGI apps and allows method filtering,
# we wrap them in a class instance. This bypasses the isfunction() check that might
# incorrectly trigger request-response wrapping.

class ASGIWrapper:
    def __init__(self, handler):
        self.handler = handler
    async def __call__(self, scope, receive, send):
        await self.handler(scope, receive, send)

app.add_route("/api/mcp/sse", ASGIWrapper(handle_mcp_sse_asgi), methods=["GET"])
app.add_route("/api/mcp/messages", ASGIWrapper(handle_mcp_messages_asgi), methods=["POST"])
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
