from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.ai.agent import AIAgent
from backend.ai.config_manager import AIConfigManager
from backend.api.ws import manager
import logging
import asyncio

logger = logging.getLogger("QLM.API.AI")

router = APIRouter()
agent = AIAgent()
config_manager = AIConfigManager()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class ProviderCreate(BaseModel):
    name: str
    base_url: str
    api_key: str

class ActiveConfigSet(BaseModel):
    provider_id: str
    model_id: str

class SessionCreate(BaseModel):
    title: str

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if not request.message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        session_id = request.session_id
        if not session_id:
            session_id = agent.create_session(title=request.message[:30] + "...")

        loop = asyncio.get_running_loop()
        async def status_callback(step: str, detail: str):
            payload = {"type": "ai_status", "session_id": session_id, "step": step, "detail": detail}
            await manager.broadcast(payload)

        response = await agent.chat(request.message, session_id=session_id, on_status=status_callback)
        return {"response": response, "session_id": session_id}
    except Exception as e:
        logger.error(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/providers")
async def list_providers():
    return config_manager.get_all_providers()

@router.post("/config/providers")
async def add_provider(provider: ProviderCreate):
    pid = config_manager.add_provider(provider.name, provider.base_url, provider.api_key)
    return {"status": "success", "id": pid}

@router.post("/config/active")
async def set_active_config(config: ActiveConfigSet):
    config_manager.set_active(config.provider_id, config.model_id)
    return {"status": "success"}

@router.get("/config/active")
async def get_active_config():
    conf = config_manager.get_active_config()
    # Mask key
    if conf.get("api_key"):
        conf["api_key"] = "***"
    return conf

@router.get("/config/models/{provider_id}")
async def fetch_models(provider_id: str):
    from backend.ai.client import AIClient

    # Securely retrieve provider details (including key)
    target_p = config_manager.get_provider(provider_id)

    if not target_p:
        raise HTTPException(status_code=404, detail="Provider not found")

    if not target_p["api_key"]:
        raise HTTPException(status_code=400, detail="Provider has no API Key configured.")

    temp_client = AIClient()
    temp_client.configure(target_p["api_key"], target_p["base_url"], "")

    try:
        models = await temp_client.list_models()
        # Save these models to config
        config_manager.set_models(provider_id, models)
        return {"models": models}
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        raise HTTPException(status_code=502, detail=f"Provider Error: {str(e)}")

# Session Routes
@router.get("/sessions")
async def list_sessions(): return agent.list_sessions()

@router.post("/sessions")
async def create_session(session: SessionCreate):
    sid = agent.create_session(session.title)
    return {"id": sid, "title": session.title}

@router.get("/sessions/{session_id}/history")
async def get_history(session_id: str): return agent.get_history(session_id)

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    agent.delete_session(session_id)
    return {"status": "success"}
