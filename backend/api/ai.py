
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.ai.agent import AIAgent
import logging

logger = logging.getLogger("QLM.API.AI")

router = APIRouter()

# Global Agent Instance (Single session for local desktop app)
agent = AIAgent()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class ConfigRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None

class SessionCreate(BaseModel):
    title: str

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI agent.
    """
    try:
        if not request.message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        logger.info(f"User Message: {request.message}")

        # If no session ID, create one
        session_id = request.session_id
        if not session_id:
            session_id = agent.create_session(title=request.message[:30] + "...")

        response = await agent.chat(request.message, session_id=session_id)
        return {"response": response, "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Chat API Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def list_sessions():
    """
    List all chat sessions.
    """
    return agent.list_sessions()

@router.post("/sessions")
async def create_session(session: SessionCreate):
    """
    Create a new chat session.
    """
    session_id = agent.create_session(session.title)
    return {"id": session_id, "title": session.title}

@router.get("/sessions/{session_id}/history")
async def get_history(session_id: str):
    """
    Get chat history for a session.
    """
    return agent.get_history(session_id)

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a chat session.
    """
    agent.delete_session(session_id)
    return {"status": "success"}

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
