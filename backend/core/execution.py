from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import asyncio
import uuid
from datetime import datetime, timezone
import random
import pandas as pd
from backend.database import db

logger = logging.getLogger("QLM.Execution")

class Order:
    def __init__(self, symbol: str, quantity: float, side: str, order_type: str = "MARKET", price: Optional[float] = None, id: str = None):
        self.id = id or str(uuid.uuid4())
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
        self.external_id = None

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
            "commission": self.commission,
            "external_id": self.external_id
        }

    def save(self):
        """Persist order to database."""
        try:
            created_at_str = self.created_at.isoformat() if self.created_at else None
            filled_at_str = self.filled_at.isoformat() if self.filled_at else None

            with db.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO orders (id, symbol, quantity, side, type, price, status, created_at, filled_at, fill_price, commission, external_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.id, self.symbol, self.quantity, self.side, self.type, self.price, self.status,
                    created_at_str, filled_at_str, self.fill_price, self.commission, self.external_id
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save order {self.id}: {e}")

    @classmethod
    def load(cls, order_id: str):
        try:
            with db.get_connection() as conn:
                row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
                if row:
                    order = cls(
                        symbol=row['symbol'],
                        quantity=row['quantity'],
                        side=row['side'],
                        order_type=row['type'],
                        price=row['price'],
                        id=row['id']
                    )
                    order.status = row['status']
                    order.created_at = pd.to_datetime(row['created_at']) if row['created_at'] else None
                    order.filled_at = pd.to_datetime(row['filled_at']) if row['filled_at'] else None
                    order.fill_price = row['fill_price']
                    order.commission = row['commission']
                    order.external_id = row['external_id']
                    return order
        except Exception as e:
            logger.error(f"Failed to load order {order_id}: {e}")
        return None

class Position:
    def __init__(self, symbol: str, quantity: float, entry_price: float, id: str = None):
        self.id = id or str(uuid.uuid4())
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price = entry_price
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        self.status = "OPEN"
        self.opened_at = datetime.now(timezone.utc)
        self.closed_at = None

    def update_price(self, price: float):
        self.current_price = price
        # PnL logic (Long only for simplicity or signed qty?)
        # Let's assume signed quantity: +Long, -Short
        self.unrealized_pnl = (self.current_price - self.entry_price) * self.quantity

    def save(self):
        try:
            opened_at_str = self.opened_at.isoformat() if self.opened_at else None
            closed_at_str = self.closed_at.isoformat() if self.closed_at else None

            with db.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO positions (id, symbol, quantity, entry_price, current_price, unrealized_pnl, realized_pnl, status, opened_at, closed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.id, self.symbol, self.quantity, self.entry_price, self.current_price,
                    self.unrealized_pnl, self.realized_pnl, self.status, opened_at_str, closed_at_str
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save position {self.id}: {e}")

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

    async def cancel_all(self):
        """Default implementation: Iterate and cancel."""
        # This might be slow for many orders, overridden in live implementations usually.
        # But we need access to active orders.
        # Abstract base class doesn't store orders.
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        pass

class PaperTradingAdapter(ExecutionHandler):
    """
    Simulates order execution with configurable latency and slippage.
    Persists state to SQLite via Order.save().
    """
    def __init__(self, latency_ms: int = 100, slippage_bps: int = 5, commission_pct: float = 0.1):
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.latency_ms = latency_ms
        self.slippage_bps = slippage_bps # Basis points (1/10000)
        self.commission_pct = commission_pct
        self.market_prices: Dict[str, float] = {} # Current market price cache
        self._load_state()

    def _load_state(self):
        """Load pending orders and open positions from DB."""
        try:
            with db.get_connection() as conn:
                # Load Orders
                rows = conn.execute("SELECT * FROM orders WHERE status = 'PENDING'").fetchall()
                for row in rows:
                    order = Order(
                        symbol=row['symbol'], quantity=row['quantity'], side=row['side'],
                        order_type=row['type'], price=row['price'], id=row['id']
                    )
                    order.status = row['status']
                    order.created_at = pd.to_datetime(row['created_at'])
                    self.orders[order.id] = order

                # Load Positions
                pos_rows = conn.execute("SELECT * FROM positions WHERE status = 'OPEN'").fetchall()
                for row in pos_rows:
                    pos = Position(
                        symbol=row['symbol'], quantity=row['quantity'], entry_price=row['entry_price'], id=row['id']
                    )
                    pos.current_price = row['current_price']
                    pos.unrealized_pnl = row['unrealized_pnl']
                    pos.realized_pnl = row['realized_pnl']
                    pos.opened_at = pd.to_datetime(row['opened_at'])
                    self.positions[pos.symbol] = pos

            logger.info(f"Loaded {len(self.orders)} pending orders and {len(self.positions)} open positions from persistence.")
        except Exception as e:
            logger.error(f"Failed to load persistence state: {e}")

    def get_total_pnl(self) -> float:
        """Calculate total PnL (Realized + Unrealized)"""
        pnl = 0.0
        for pos in self.positions.values():
            pnl += pos.realized_pnl + pos.unrealized_pnl
        return round(pnl, 2)

    def update_price(self, symbol: str, price: float):
        self.market_prices[symbol] = price

    async def submit_order(self, order: Order) -> Order:
        logger.info(f"PaperTrade: Submitting {order.side} {order.quantity} {order.symbol}")
        self.orders[order.id] = order
        order.status = "PENDING"
        order.save()

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

        # Update Position
        self._update_position(order)

        order.save()
        logger.info(f"PaperTrade: Filled {order.id} @ {fill_price:.2f} (Slippage: {slippage_pct*100:.4f}%)")
        return order

    def _update_position(self, order: Order):
        """Update position based on filled order."""
        symbol = order.symbol
        qty = order.quantity if order.side == "BUY" else -order.quantity
        price = order.fill_price

        if symbol not in self.positions:
            # New Position
            if qty == 0: return
            pos = Position(symbol, qty, price)
            self.positions[symbol] = pos
            pos.save()
        else:
            pos = self.positions[symbol]

            # Check if closing or flipping
            if (pos.quantity > 0 and qty < 0) or (pos.quantity < 0 and qty > 0):
                # Closing part/all
                closing_qty = min(abs(pos.quantity), abs(qty)) * (1 if qty > 0 else -1)
                remaining_qty = pos.quantity + qty

                # Realized PnL on closed portion
                # Profit = (Exit Price - Entry Price) * Qty
                # If Long (pos > 0) and Sell (qty < 0): (Price - Entry) * Abs(qty)
                # If Short (pos < 0) and Buy (qty > 0): (Entry - Price) * Abs(qty)

                if pos.quantity > 0: # Long closing
                    pnl = (price - pos.entry_price) * abs(closing_qty)
                else: # Short closing
                    pnl = (pos.entry_price - price) * abs(closing_qty)

                pos.realized_pnl += pnl
                pos.quantity += qty # Update quantity

                if pos.quantity == 0:
                    pos.status = "CLOSED"
                    pos.closed_at = datetime.now(timezone.utc)
                    del self.positions[symbol]
                elif (pos.quantity > 0 and remaining_qty < 0) or (pos.quantity < 0 and remaining_qty > 0):
                    # Flipped position: Close current fully and open new with remainder
                    if pos.quantity > 0: # Long -> Short
                        pnl = (price - pos.entry_price) * abs(pos.quantity)
                    else: # Short -> Long
                        pnl = (pos.entry_price - price) * abs(pos.quantity)

                    pos.realized_pnl += pnl

                    # Open new position with remainder
                    pos.quantity = remaining_qty
                    pos.entry_price = price
                    # pos.status remains OPEN

            else:
                # Increasing position
                # Weighted Average Entry Price
                total_val = (pos.quantity * pos.entry_price) + (qty * price)
                new_qty = pos.quantity + qty
                pos.entry_price = total_val / new_qty if new_qty != 0 else 0
                pos.quantity = new_qty

            pos.save()

    async def cancel_order(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if order and order.status == "PENDING":
            order.status = "CANCELLED"
            order.save()
            return True
        return False

    async def cancel_all(self):
        """Cancel all pending orders."""
        for order in list(self.orders.values()):
            if order.status == "PENDING":
                await self.cancel_order(order.id)

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)
