"""
QLM API — Backtest Engine Endpoints.

Provides endpoints for:
  POST /backtest/run          — Run a backtest
  POST /backtest/export-csv   — Export trade ledger as CSV
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from backend.core.engine import BacktestEngine
from backend.core.exceptions import BacktestError, SanitizationError, QLMSystemError
from backend.api.ws import manager
from typing import Optional, Dict, Any, List
import asyncio
import io
import csv
import math
from starlette.concurrency import run_in_threadpool
import logging

logger = logging.getLogger("QLM.API.Engine")

router = APIRouter()
engine = BacktestEngine()


class BacktestRequest(BaseModel):
    dataset_id: str
    strategy_name: str
    version: Optional[int] = None
    # Capital / RRR Mode
    mode: str = "capital"
    initial_capital: float = 10000.0
    leverage: float = 1.0
    position_sizing: str = "fixed"
    fixed_size: float = 1.0
    risk_per_trade: float = 0.01
    # Realistic Market Simulation
    slippage_mode: str = "none"
    slippage_value: float = 0.0
    spread_value: float = 0.0
    entry_on_next_bar: bool = False
    skip_weekend_trades: bool = True

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v not in ("capital", "rrr"):
            raise ValueError("mode must be 'capital' or 'rrr'")
        return v

    @field_validator("slippage_mode")
    @classmethod
    def validate_slippage_mode(cls, v):
        if v not in ("none", "fixed", "percent", "random"):
            raise ValueError("slippage_mode must be one of: none, fixed, percent, random")
        return v

    @field_validator("leverage")
    @classmethod
    def validate_leverage(cls, v):
        if v < 1.0:
            raise ValueError("leverage must be >= 1.0")
        return v

    @field_validator("slippage_value", "spread_value")
    @classmethod
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError("Value must be >= 0")
        return v

    @field_validator("initial_capital")
    @classmethod
    def validate_capital(cls, v):
        if v <= 0:
            raise ValueError("initial_capital must be > 0")
        return v


class ExportRequest(BaseModel):
    trades: List[Dict[str, Any]]
    mode: str = "capital"


def _sanitize_json(obj):
    """Recursively replace NaN/Inf with None for JSON serialisation."""
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    loop = asyncio.get_running_loop()

    def sync_callback(pct: float, msg: str, data: Dict[str, Any]):
        payload = {
            "type": "progress",
            "dataset_id": request.dataset_id,
            "progress": round(pct, 2),
            "message": msg,
            "data": data or {},
        }
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)

    try:
        results = await run_in_threadpool(
            engine.run,
            dataset_id=request.dataset_id,
            strategy_name=request.strategy_name,
            version=request.version,
            callback=sync_callback,
            mode=request.mode,
            initial_capital=request.initial_capital,
            leverage=request.leverage,
            position_sizing=request.position_sizing,
            fixed_size=request.fixed_size,
            risk_per_trade=request.risk_per_trade,
            slippage_mode=request.slippage_mode,
            slippage_value=request.slippage_value,
            spread_value=request.spread_value,
            entry_on_next_bar=request.entry_on_next_bar,
            skip_weekend_trades=request.skip_weekend_trades,
        )

        # Sanitise for JSON (no NaN/Inf)
        results = _sanitize_json(results)

        status = results.get("status", "success")

        if status == "failed":
            error_msg = results.get("error", "Unknown execution error")
            logger.error(f"Backtest failed: {error_msg}")
            await manager.broadcast({
                "type": "error",
                "dataset_id": request.dataset_id,
                "message": "Backtest Execution Failed",
                "details": error_msg,
            })
            return {"status": "failed", "error": error_msg, "results": results}
        else:
            await manager.broadcast({
                "type": "finished",
                "dataset_id": request.dataset_id,
                "results": results,
            })
            return {"status": "success", "results": results}

    except (BacktestError, SanitizationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except QLMSystemError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Backtest API Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error during Backtest")


@router.post("/export-csv")
async def export_trades_csv(request: ExportRequest):
    """Export trade ledger as a downloadable CSV file."""
    try:
        trades = request.trades
        if not trades:
            raise HTTPException(status_code=400, detail="No trades to export")

        pnl_label = "PnL (USD)" if request.mode == "capital" else "PnL (R)"

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Entry DT", "DIR", "Entry Price", "Exit Price", "Exit DT",
            pnl_label, "RRR", "SL", "TP", "MAE", "MFE",
            "Holding Time (min)", "Status",
        ])

        for t in trades:
            writer.writerow([
                t.get("entry_time", ""),
                t.get("direction", ""),
                t.get("entry_price", ""),
                t.get("exit_price", ""),
                t.get("exit_time", ""),
                round(t.get("pnl", 0), 2),
                round(t.get("r_multiple", 0), 4),
                t.get("sl", ""),
                t.get("tp", ""),
                round(t.get("mae", 0), 2),
                round(t.get("mfe", 0), 2),
                round(t.get("duration", 0), 2),
                t.get("exit_reason", ""),
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=trade_ledger.csv"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV Export Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
