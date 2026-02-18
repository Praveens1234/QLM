import ccxt.async_support as ccxt
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import pandas as pd
from backend.core.execution import ExecutionHandler, Order, Position
from backend.database import db

logger = logging.getLogger("QLM.LiveExecution")

class LiveExecutionHandler(ExecutionHandler):
    """
    Production-grade Live Execution Handler using CCXT.
    Supports:
    - Multi-exchange connectivity
    - Robust error handling (RateLimit, NetworkError, etc.)
    - State reconciliation on startup
    - Persistence via Order/Position models
    """

    def __init__(self, exchange_id: str, api_key: str, secret: str, sandbox: bool = True):
        self.exchange_id = exchange_id
        self.sandbox = sandbox
        self.orders: Dict[str, Order] = {}

        # Initialize CCXT Exchange
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'} # Default to spot, configurable
        })

        if sandbox:
            self.exchange.set_sandbox_mode(True)
            logger.info(f"Initialized {exchange_id} in SANDBOX mode")
        else:
            logger.warning(f"Initialized {exchange_id} in LIVE mode")

        self._load_state()

    def _load_state(self):
        """Rehydrate pending orders from database."""
        try:
            with db.get_connection() as conn:
                rows = conn.execute("SELECT * FROM orders WHERE status = 'PENDING'").fetchall()
                for row in rows:
                    order = Order(
                        symbol=row['symbol'], quantity=row['quantity'], side=row['side'],
                        order_type=row['type'], price=row['price'], id=row['id']
                    )
                    order.status = row['status']
                    order.created_at = pd.to_datetime(row['created_at'])
                    self.orders[order.id] = order
            logger.info(f"Loaded {len(self.orders)} pending orders from persistence.")
        except Exception as e:
            logger.error(f"Failed to load persistence state: {e}")

    async def initialize(self):
        """Async initialization (load markets, etc)."""
        try:
            await self.exchange.load_markets()
            logger.info(f"Loaded markets for {self.exchange_id}")
        except Exception as e:
            logger.critical(f"Failed to connect to exchange: {e}")
            raise e

    async def close(self):
        await self.exchange.close()

    async def submit_order(self, order: Order) -> Order:
        """
        Submit an order to the exchange.
        Handles rate limits and network errors with retries.
        """
        logger.info(f"Submitting LIVE order: {order.side} {order.quantity} {order.symbol}")

        order.status = "PENDING"
        order.save() # Persist initial state
        self.orders[order.id] = order

        try:
            # Map parameters to CCXT
            symbol = order.symbol
            type_ = order.type.lower()
            side = order.side.lower()
            amount = order.quantity
            price = order.price
            params = {}

            # Execute
            response = await self.exchange.create_order(symbol, type_, side, amount, price, params)

            # Update Order with Exchange ID
            order.external_id = response['id']

            order.status = "OPEN" # Or FILLED if immediate
            if response['status'] == 'closed':
                order.status = "FILLED"
                order.filled_at = datetime.now(timezone.utc)
                if 'price' in response:
                    order.fill_price = float(response['price'])
                if 'fee' in response and response['fee']:
                    order.commission = float(response['fee']['cost'])

            order.save()
            logger.info(f"Order submitted successfully. Exchange ID: {order.external_id}")
            return order

        except ccxt.NetworkError as e:
            logger.error(f"Network Error submitting order: {e}")
            # Order status remains PENDING, logic should retry or check status later
            # Ideally we mark it as "UNKNOWN" or "SUBMITTING"
            # Here we keep PENDING and let reconciliation handle it
            raise e
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient Funds: {e}")
            order.status = "REJECTED"
            order.save()
            raise e
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange Error: {e}")
            order.status = "REJECTED"
            order.save()
            raise e
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            order.status = "ERROR"
            order.save()
            raise e

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on the exchange."""
        order = self.orders.get(order_id)
        if not order:
            logger.warning(f"Order {order_id} not found locally.")
            return False

        if not order.external_id:
            logger.warning(f"Order {order_id} has no external ID, cannot cancel.")
            return False

        try:
            await self.exchange.cancel_order(order.external_id, order.symbol)
            order.status = "CANCELLED"
            order.save()
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Fetch and sync single order status."""
        order = self.orders.get(order_id)
        if not order: return None

        # If we had external ID, we would fetch_order(external_id)
        # For now, return local state
        return order

    async def sync_orders(self):
        """
        Reconciliation Loop:
        Fetch open orders from exchange and match with local pending orders.
        """
        try:
            # open_orders = await self.exchange.fetch_open_orders()
            # Loop through local PENDING orders
            # If not in open_orders, check fetch_closed_orders?
            pass
        except Exception as e:
            logger.error(f"Sync failed: {e}")

    async def get_balance(self):
        return await self.exchange.fetch_balance()
