from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import asyncio
import uuid
from datetime import datetime, timezone
import random

logger = logging.getLogger("QLM.Execution")

class Order:
    def __init__(self, symbol: str, quantity: float, side: str, order_type: str = "MARKET", price: Optional[float] = None):
        self.id = str(uuid.uuid4())
        self.symbol = symbol
        self.quantity = quantity
        self.side = side.upper() # BUY/SELL
        self.type = order_type.upper()
        self.price = price
        self.status = "CREATED"
        self.created_at = datetime.now(timezone.utc)
        self.filled_at = None
        self.fill_price = None
        self.commission = 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "side": self.side,
            "type": self.type,
            "price": self.price,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "fill_price": self.fill_price,
            "commission": self.commission
        }

class ExecutionHandler(ABC):
    """
    Interface for order execution (Paper or Live).
    """
    @abstractmethod
    async def submit_order(self, order: Order) -> Order:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        pass

class PaperTradingAdapter(ExecutionHandler):
    """
    Simulates order execution with configurable latency and slippage.
    """
    def __init__(self, latency_ms: int = 100, slippage_bps: int = 5, commission_pct: float = 0.1):
        self.orders: Dict[str, Order] = {}
        self.latency_ms = latency_ms
        self.slippage_bps = slippage_bps # Basis points (1/10000)
        self.commission_pct = commission_pct
        self.market_prices: Dict[str, float] = {} # Current market price cache

    def update_price(self, symbol: str, price: float):
        self.market_prices[symbol] = price

    async def submit_order(self, order: Order) -> Order:
        logger.info(f"PaperTrade: Submitting {order.side} {order.quantity} {order.symbol}")
        self.orders[order.id] = order
        order.status = "PENDING"

        # Simulate Network Latency
        await asyncio.sleep(self.latency_ms / 1000.0)

        # Execute
        return await self._execute(order)

    async def _execute(self, order: Order) -> Order:
        current_price = self.market_prices.get(order.symbol)
        if not current_price:
            logger.warning(f"PaperTrade: No price for {order.symbol}, order rejected.")
            order.status = "REJECTED"
            return order

        # Calculate Slippage
        # Random slippage between 0 and max_slippage
        slippage_pct = random.uniform(0, self.slippage_bps / 10000.0)

        if order.side == "BUY":
            fill_price = current_price * (1 + slippage_pct)
        else:
            fill_price = current_price * (1 - slippage_pct)

        # Check Limit Price
        if order.type == "LIMIT" and order.price:
            if order.side == "BUY" and fill_price > order.price:
                # Limit not met (simplification: hold it? For now reject or keep pending)
                # For this adapter, we just assume immediate fill or reject if price is bad
                # Real matching engine is complex.
                logger.info("PaperTrade: Limit price not met.")
                return order # Still PENDING
            elif order.side == "SELL" and fill_price < order.price:
                return order

        order.status = "FILLED"
        order.fill_price = fill_price
        order.filled_at = datetime.now(timezone.utc)
        order.commission = (fill_price * order.quantity) * (self.commission_pct / 100.0)

        logger.info(f"PaperTrade: Filled {order.id} @ {fill_price:.2f} (Slippage: {slippage_pct*100:.4f}%)")
        return order

    async def cancel_order(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if order and order.status == "PENDING":
            order.status = "CANCELLED"
            return True
        return False

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)
