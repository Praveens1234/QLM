from fastapi import APIRouter
from backend.api import data, strategy, engine, ws

router = APIRouter()

router.include_router(data.router, prefix="/data", tags=["Data"])
router.include_router(strategy.router, prefix="/strategies", tags=["Strategies"])
router.include_router(engine.router, prefix="/backtest", tags=["Backtest"])
router.include_router(ws.router, tags=["WebSocket"])

@router.get("/")
async def root():
    return {"message": "QLM API v1"}
