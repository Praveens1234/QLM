from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.engine import BacktestEngine
from backend.api.ws import manager
from typing import Optional, Dict, Any
import asyncio
from starlette.concurrency import run_in_threadpool
import logging

logger = logging.getLogger("QLM.API.Engine")

router = APIRouter()
engine = BacktestEngine()

class BacktestRequest(BaseModel):
    dataset_id: str
    strategy_name: str
    version: Optional[int] = None

@router.post("/run")
async def run_backtest(request: BacktestRequest):
    loop = asyncio.get_running_loop()
    
    def sync_callback(pct: float, msg: str, data: Dict[str, Any]):
        # Schedule the async broadcast on the main event loop
        payload = {
            "type": "progress",
            "dataset_id": request.dataset_id,
            "progress": round(pct, 2),
            "message": msg,
            "data": data
        }
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)

    try:
        # Run CPU-bound backtest in threadpool
        results = await run_in_threadpool(
            engine.run,
            dataset_id=request.dataset_id,
            strategy_name=request.strategy_name,
            version=request.version,
            callback=sync_callback
        )
        
        status = results.get("status", "success")

        if status == "failed":
            error_msg = results.get("error", "Unknown execution error")
            logger.error(f"Backtest failed gracefully: {error_msg}")

            # Broadcast failure
            await manager.broadcast({
                "type": "error",
                "dataset_id": request.dataset_id,
                "message": "Backtest Execution Failed",
                "details": error_msg
            })

            # Still return partial results? Or error?
            # Let's return the results (which contain empty trades) but with status
            return {"status": "failed", "error": error_msg, "results": results}
        
        else:
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
        logger.error(f"Backtest API Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error during Backtest")
