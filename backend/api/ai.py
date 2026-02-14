
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.ai.agent import AIAgent
import logging

logger = logging.getLogger("QLM.API.AI")

router = APIRouter()

# Global Agent Instance (Single session for local desktop app)
agent = AIAgent()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class ConfigRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI agent.
    """
    try:
        if not request.message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        logger.info(f"User Message: {request.message}")
        response = await agent.chat(request.message)
        return {"response": response}
        
    except Exception as e:
        logger.error(f"Chat API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config")
async def configure_agent(request: ConfigRequest):
    """
    Update AI Agent configuration (API Key, Model, URL).
    """
    try:
        agent.update_config(request.api_key, request.base_url, request.model)
        return {"status": "success", "message": "AI Agent configured successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def get_models():
    """
    Fetch available models from the provider.
    """
    models = await agent.get_available_models()
    return {"models": models}

@router.get("/config")
async def get_config():
    """
    Get current configuration.
    """
    return {
        "api_key": agent.client.api_key, # In prod, mask this!
        "base_url": agent.client.base_url,
        "model": agent.client.model
    }

@router.delete("/history")
async def clear_history():
    """
    Clear conversation history.
    """
    agent.clear_history()
    return {"status": "success", "message": "Conversation history cleared."}
