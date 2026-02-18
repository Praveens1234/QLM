from fastapi import APIRouter
from backend.api import data, strategy, engine, ws, ai, trade

router = APIRouter()

router.include_router(data.router, prefix="/data", tags=["Data"])
router.include_router(strategy.router, prefix="/strategies", tags=["Strategies"])
router.include_router(engine.router, prefix="/backtest", tags=["Backtest"])
router.include_router(trade.router, prefix="/trade", tags=["Live Trading"])
router.include_router(ws.router, tags=["WebSocket"])
router.include_router(ai.router, prefix="/ai", tags=["AI Agent"])

@router.get("/")
async def root():
    return {"message": "QLM API v1"}
