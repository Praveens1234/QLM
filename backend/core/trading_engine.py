import asyncio
import logging
from typing import Dict, Optional, List
from backend.core.execution import ExecutionHandler, Order, Position
from backend.core.execution_live import LiveExecutionHandler
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
        self.is_running = False
        self.error_count = 0
        self.max_errors = 5

    async def initialize(self):
        """Initialize components and recover state."""
        try:
            logger.info(f"Initializing Trading Engine in {self.mode} mode...")

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
        if self.execution_handler and hasattr(self.execution_handler, 'close'):
            if asyncio.iscoroutinefunction(self.execution_handler.close):
                await self.execution_handler.close()
            else:
                self.execution_handler.close()

    async def run_loop(self):
        """Main Event Loop."""
        while self.is_running:
            try:
                # 1. Check Circuit Breaker
                if self.error_count >= self.max_errors:
                    logger.critical("Circuit Breaker Tripped! Halting Trading.")
                    self.is_running = False
                    break

                # 2. Sync State (if live)
                if self.mode == "LIVE" and hasattr(self.execution_handler, 'sync_orders'):
                     await self.execution_handler.sync_orders()

                # 3. Strategy Logic (Placeholder for strategy execution)
                # In a real system, we'd iterate over active strategies and call .next()

                await asyncio.sleep(1) # 1s loop

            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5) # Backoff

    def get_status(self):
        return {
            "mode": self.mode,
            "running": self.is_running,
            "orders_count": len(self.execution_handler.orders) if self.execution_handler else 0,
            "error_count": self.error_count
        }
