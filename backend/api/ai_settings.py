from fastapi import APIRouter, HTTPException
from typing import List
from backend.ai.config_manager import AIConfigManager
from backend.ai.models import ProviderConfig, Model, AIConfig
from backend.ai.discovery import model_discovery

router = APIRouter(prefix="/settings/ai")
config_manager = AIConfigManager()

@router.get("/config", response_model=AIConfig)
async def get_global_config():
    config = config_manager.get_config()
    for p in config.providers:
        if p.api_key:
            p.api_key = "***"
    return config

@router.post("/config/active")
async def set_active_provider(payload: dict):
    provider_id = payload.get("provider_id")
    model_id = payload.get("model_id")
    if not provider_id or not model_id:
        raise HTTPException(status_code=400, detail="Missing provider_id or model_id")

    config_manager.set_active_provider(provider_id, model_id)
    return {"status": "success"}

# --- Existing Provider Routes ---
@router.get("/providers", response_model=List[ProviderConfig])
async def list_providers():
    config = config_manager.get_config()
    for p in config.providers:
        if p.api_key:
            p.api_key = "***"
    return config.providers

@router.post("/providers")
async def add_provider(provider: ProviderConfig):
    try:
        config_manager.add_provider(provider)
        if provider.api_key:
            try:
                await model_discovery.discover_models(provider.id)
            except:
                pass
        return {"status": "success", "id": provider.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str):
    config_manager.remove_provider(provider_id)
    return {"status": "success"}

@router.post("/providers/{provider_id}/refresh")
async def refresh_models(provider_id: str):
    try:
        models = await model_discovery.discover_models(provider_id)
        return {"status": "success", "models": models}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/providers/{provider_id}/models")
async def list_provider_models(provider_id: str):
    config = config_manager.get_provider_config(provider_id)
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")
    return config.models
