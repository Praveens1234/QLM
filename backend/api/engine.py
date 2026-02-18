from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.engine import BacktestEngine
from backend.api.ws import manager
from backend.ai.analytics import optimize_strategy, optimize_strategy_genetic
from typing import Optional, Dict, Any, List
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

class OptimizeRequest(BaseModel):
    dataset_id: str
    strategy_name: str
    method: str = "grid" # grid, genetic
    target_metric: str = "net_profit"
    params: Optional[Dict[str, List[Any]]] = None

@router.post("/optimize")
async def run_optimization(request: OptimizeRequest):
    try:
        # Default Param Grid for Demo if not provided
        # In a real app, frontend would inspect strategy and build this.
        param_grid = request.params
        if not param_grid:
            # Simple demo grid
            param_grid = {
                "ma_fast": [5, 10, 20],
                "ma_slow": [30, 50, 100],
                "rsi_period": [14, 21],
                "rsi_overbought": [70, 80],
                "rsi_oversold": [20, 30]
            }

        if request.method == "genetic":
            result = await run_in_threadpool(
                optimize_strategy_genetic,
                request.strategy_name,
                request.dataset_id,
                param_grid,
                population_size=20,
                generations=5,
                target_metric=request.target_metric
            )
        else:
            result = await run_in_threadpool(
                optimize_strategy,
                request.strategy_name,
                request.dataset_id,
                param_grid,
                request.target_metric
            )

        return {"status": "success", "results": result}

    except Exception as e:
        logger.error(f"Optimization API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
