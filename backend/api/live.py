from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.core.execution_live import LiveExecutionHandler
from backend.database import db
from backend.core.config import settings

router = APIRouter()

# Singleton Handler (Lazy Init)
_live_handler = None

def get_live_handler():
    global _live_handler
    if not _live_handler:
        # In production, credentials would come from secured config
        # For now, we assume paper trading or env vars
        # NOTE: This route should ideally be protected or use configured keys
        _live_handler = LiveExecutionHandler("binance", "mock_key", "mock_secret", sandbox=True)
    return _live_handler

@router.get("/status")
async def get_live_status():
    """Returns active orders and positions."""
    try:
        # Fetch from DB directly for persistence view
        with db.get_connection() as conn:
            orders = conn.execute("SELECT * FROM orders WHERE status IN ('OPEN', 'PENDING', 'PARTIAL') ORDER BY created_at DESC").fetchall()
            positions = conn.execute("SELECT * FROM positions WHERE status = 'OPEN'").fetchall()

            # Simple PnL calc
            total_pnl = sum([p['unrealized_pnl'] for p in positions])

            return {
                "active_orders": [dict(row) for row in orders],
                "positions": [dict(row) for row in positions],
                "total_pnl": total_pnl,
                "status": "online"
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}
