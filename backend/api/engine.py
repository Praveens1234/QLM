from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.engine import BacktestEngine
from backend.api.ws import manager
from typing import Optional
import asyncio
from starlette.concurrency import run_in_threadpool

router = APIRouter()
engine = BacktestEngine()

class BacktestRequest(BaseModel):
    dataset_id: str
    strategy_name: str
    version: Optional[int] = None

@router.post("/run")
async def run_backtest(request: BacktestRequest):
    loop = asyncio.get_running_loop()
    
    def sync_callback(pct, msg, data):
        # We need a sync callback that calls the async broadcast
        # Using run_coroutine_threadsafe to schedule on the main loop
        payload = {
            "type": "progress",
            "dataset_id": request.dataset_id,
            "progress": round(pct, 2),
            "message": msg,
            "data": data
        }
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)

    try:
        # Run the CPU-bound backtest in a threadpool to avoid blocking the async loop
        results = await run_in_threadpool(
            engine.run,
            dataset_id=request.dataset_id,
            strategy_name=request.strategy_name,
            version=request.version,
            callback=sync_callback
        )
        
        # Broadcast completion
        await manager.broadcast({
            "type": "finished",
            "dataset_id": request.dataset_id,
            "results": results
        })
        
        return {"status": "success", "results": results}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
