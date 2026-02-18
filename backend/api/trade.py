from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.api.trade_manager import trading_engine
from typing import Optional, Dict

router = APIRouter()

class StartRequest(BaseModel):
    mode: str = "PAPER" # PAPER or LIVE
    exchange_config: Optional[Dict] = None

@router.post("/start")
async def start_trading(request: StartRequest):
    if trading_engine.is_running:
        return {"status": "already_running"}

    try:
        trading_engine.mode = request.mode
        trading_engine.config = request.exchange_config or {}
        await trading_engine.initialize()
        # Start loop in background (not implemented in this stub, usually via asyncio.create_task)
        # For now, we just initialize. The loop logic needs to be hooked up to `app.on_event("startup")` or similar
        # or we start a task here.
        import asyncio
        asyncio.create_task(trading_engine.run_loop())

        return {"status": "started", "mode": request.mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_trading():
    if not trading_engine.is_running:
        return {"status": "stopped"}

    await trading_engine.shutdown()
    return {"status": "stopped"}

@router.get("/status")
async def get_status():
    return trading_engine.get_status()
