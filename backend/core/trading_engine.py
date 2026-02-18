import asyncio
import logging
from typing import Dict, Optional, List
from backend.core.execution import ExecutionHandler, Order, Position
from backend.core.execution_live import LiveExecutionHandler
from backend.core.risk_manager import RiskManager
from backend.database import db

logger = logging.getLogger("QLM.TradingEngine")

class TradingEngine:
    """
    Central Orchestrator for Live Trading.
    Manages:
    - Execution Handler lifecycle (Connect/Disconnect)
    - Strategy State (Start/Stop)
    - System Recovery (Load state on startup)
    - Safety Circuit Breakers
    """

    def __init__(self, mode: str = "PAPER", exchange_config: Dict = None):
        self.mode = mode.upper()
        self.config = exchange_config or {}
        self.execution_handler: Optional[ExecutionHandler] = None
        self.risk_manager: Optional[RiskManager] = None
        self.is_running = False
        self.error_count = 0
        self.max_errors = 5

    async def initialize(self):
        """Initialize components and recover state."""
        try:
            logger.info(f"Initializing Trading Engine in {self.mode} mode...")
            self.risk_manager = RiskManager(self.config.get("risk", {}))

            if self.mode == "LIVE":
                if not self.config:
                    raise ValueError("Exchange config required for LIVE mode")
                self.execution_handler = LiveExecutionHandler(
                    exchange_id=self.config.get('exchange_id'),
                    api_key=self.config.get('api_key'),
                    secret=self.config.get('secret'),
                    sandbox=self.config.get('sandbox', True)
                )
                await self.execution_handler.initialize()
            else:
                from backend.core.execution import PaperTradingAdapter
                self.execution_handler = PaperTradingAdapter()

            # State Recovery is handled inside ExecutionHandler._load_state()
            # But we can add high-level checks here (e.g. check open positions vs equity)

            self.is_running = True
            logger.info("Trading Engine Initialized Successfully.")

        except Exception as e:
            logger.critical(f"Engine Initialization Failed: {e}")
            raise e

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down Trading Engine...")
        self.is_running = False

        # Kill Switch: Cancel all orders
        if self.execution_handler and hasattr(self.execution_handler, 'cancel_all'):
             logger.warning("Kill Switch: Cancelling all open orders...")
             try:
                 await self.execution_handler.cancel_all()
             except Exception as e:
                 logger.error(f"Failed to cancel orders on shutdown: {e}")

        if self.execution_handler and hasattr(self.execution_handler, 'close'):
            if asyncio.iscoroutinefunction(self.execution_handler.close):
                await self.execution_handler.close()
            else:
                self.execution_handler.close()

    async def submit_order(self, order: Order):
        """
        Submit an order after validating risk.
        """
        if not self.is_running:
             logger.warning("Order rejected: Engine is stopped.")
             return None

        # Gather Portfolio State
        portfolio_state = {
            "total_pnl": self.execution_handler.get_total_pnl() if self.execution_handler else 0.0,
            "positions_count": len(self.execution_handler.positions) if self.execution_handler else 0,
            "active_symbols": list(self.execution_handler.positions.keys()) if self.execution_handler else [],
            "current_price": order.price # Basic assumption if limit
        }

        # Risk Check
        is_valid, reason = self.risk_manager.validate_order(order, portfolio_state)
        if not is_valid:
            logger.warning(f"Order rejected by Risk Manager: {reason}")
            # Broadcast rejection?
            return None

        # Execute
        return await self.execution_handler.submit_order(order)

    async def run_loop(self):
        """Main Event Loop."""
        # Local import to avoid circular dependency
        from backend.api.ws import manager

        while self.is_running:
            try:
                # 1. Check Circuit Breaker
                if self.error_count >= self.max_errors:
                    logger.critical("Circuit Breaker Tripped! Halting Trading.")
                    await manager.broadcast({"type": "error", "message": "Circuit Breaker Tripped. Trading Halted."})
                    self.is_running = False
                    break

                # 2. Sync State (if live)
                if self.mode == "LIVE" and hasattr(self.execution_handler, 'sync_orders'):
                     await self.execution_handler.sync_orders()

                # Broadcast Status Heartbeat (every 5s roughly?)
                # Actually, only on change is better. But keeping simple.
                # await manager.broadcast({"type": "trade_status", "data": self.get_status()})

                # 3. Strategy Logic (Placeholder for strategy execution)
                # In a real system, we'd iterate over active strategies and call .next()

                await asyncio.sleep(1) # 1s loop

            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5) # Backoff

    def get_status(self):
        orders_count = len(self.execution_handler.orders) if self.execution_handler and hasattr(self.execution_handler, 'orders') else 0
        positions_count = len(self.execution_handler.positions) if self.execution_handler and hasattr(self.execution_handler, 'positions') else 0
        pnl = self.execution_handler.get_total_pnl() if self.execution_handler and hasattr(self.execution_handler, 'get_total_pnl') else 0.0

        orders = [o.to_dict() for o in self.execution_handler.orders.values()] if self.execution_handler and hasattr(self.execution_handler, 'orders') else []
        # Filter for active orders? Or all? Usually dashboard shows pending.
        active_orders = [o for o in orders if o['status'] in ['PENDING', 'SUBMITTED', 'PARTIALLY_FILLED']]

        positions = []
        if self.execution_handler and hasattr(self.execution_handler, 'positions'):
             for p in self.execution_handler.positions.values():
                 pos_dict = {
                     "symbol": p.symbol,
                     "quantity": p.quantity,
                     "entry_price": p.entry_price,
                     "current_price": p.current_price,
                     "unrealized_pnl": p.unrealized_pnl,
                     "realized_pnl": p.realized_pnl
                 }
                 positions.append(pos_dict)

        return {
            "mode": self.mode,
            "running": self.is_running,
            "orders_count": orders_count,
            "positions_count": positions_count,
            "pnl": pnl,
            "error_count": self.error_count,
            "orders": active_orders,
            "positions": positions
        }
