from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from backend.core.engine import BacktestEngine
from backend.api.ws import manager
from typing import Dict, Any, Optional
import asyncio

router = APIRouter()
engine = BacktestEngine()

class BacktestRequest(BaseModel):
    dataset_id: str
    strategy_name: str
    version: Optional[int] = None

def run_backtest_bg(dataset_id, strategy_name, version):
    async def run_wrapper():
        try:
            # We need a sync callback that calls the async broadcast
            # But the engine is sync.
            # We can use asyncio.run_coroutine_threadsafe if we have a loop, 
            # Or just fire and forget if broadcast is async. 
            # Wait, api/ws.py broadcast is async.
            # We need to bridge sync engine to async broadcast.
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            def progress_callback(pct, msg, data):
                # This is called from sync engine loop
                payload = {
                    "type": "progress",
                    "dataset_id": dataset_id,
                    "progress": pct,
                    "message": msg,
                    "data": data
                }
                # Create a task to broadcast? Cannot create task on other loop easily.
                # Actually, wrapping the WHOLE engine run in a thread (FastAPI background task does this)
                # But we want to call async broadcast.
                # The connection manager needs to be accessed safely.
                
                # Simple hack: use asyncio.run(manager.broadcast(...))? 
                # No, manager.broadcast uses active_connections which are bound to the MAIN loop.
                # Accessing them from another thread is thread-unsafe and asyncio-unsafe.
                
                # Solution: The callback should NOT try to send WS message directly if threading is complex.
                # BUT, FastAPI BackgroundTasks run in a threadpool.
                
                # Alternative: Do NOT use BackgroundTasks. Use async endpoint and await?
                # But backtest is blocking CPU bound. It will block the event loop.
                # Using run_in_executor? Yes.
                pass

            # Redesign:
            # We'll use a wrapper that runs engine in threadpool, and uses a queue or similar to send updates?
            # Or simplest: Just make the callback do nothing for now if async is hard.
            # BUT requirement is real-time updates.
            pass
        except Exception:
            pass

# Better approach:
# Use `fastapi.concurrency.run_in_threadpool`.
# Check if we can access the loop.
# Or simpler: The callback puts messages into an asyncio.Queue, and a separate async worker consumes and broadcasts.

import asyncio
queue = asyncio.Queue()

async def listner_worker():
    while True:
        msg = await queue.get()
        await manager.broadcast(msg)
        queue.task_done()

# We need to start this worker on startup?
# Or just handle it ad-hoc.

# Let's try a simpler approach compatible with standard FastAPI usage.
# If we define the endpoint as `async def`, FastAPI runs it in the loop.
# If we call a blocking function, we block the loop. Bad.
# If we define `def`, FastAPI runs in threadpool.
# From threadpool, we cannot `await manager.broadcast`.

# Solution:
# `run_backtest` (async) calls `run_in_threadpool(engine.run, ..., callback=sync_callback)`.
# `sync_callback` uses `asyncio.run_coroutine_threadsafe` to schedule `manager.broadcast` on the main loop.

from starlette.concurrency import run_in_threadpool

@router.post("/run")
async def run_backtest(request: BacktestRequest):
    loop = asyncio.get_running_loop()
    
    def sync_callback(pct, msg, data):
        payload = {
            "type": "progress",
            "dataset_id": request.dataset_id,
            "progress": round(pct, 2),
            "message": msg,
            "details": data
        }
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)

    try:
        results = await run_in_threadpool(
            engine.run,
            dataset_id=request.dataset_id,
            strategy_name=request.strategy_name,
            version=request.version,
            callback=sync_callback
        )
        
        # Send final success
        await manager.broadcast({
            "type": "finished",
            "dataset_id": request.dataset_id,
            "results": results # Include metrics
        })
        
        return {"status": "success", "results": results}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
