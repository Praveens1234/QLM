from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

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

# MCP Transport
from backend.api.mcp import handle_mcp_sse, handle_mcp_messages
app.add_route("/api/mcp/sse", handle_mcp_sse)
app.add_route("/api/mcp/messages", handle_mcp_messages, methods=["POST"])

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
