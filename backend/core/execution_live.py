import ccxt.async_support as ccxt
import ccxt as ccxt_sync # For exception classes
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import pandas as pd
from backend.core.execution import ExecutionHandler, Order, Position
from backend.database import db
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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

    @retry(
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt_sync.RateLimitExceeded, ccxt_sync.DDoSProtection)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _execute_ccxt_order(self, symbol, type_, side, amount, price, params):
        return await self.exchange.create_order(symbol, type_, side, amount, price, params)

    async def submit_order(self, order: Order) -> Order:
        """
        Submit an order to the exchange.
        Handles rate limits and network errors with automatic retries via tenacity.
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

            # Execute with Retry
            response = await self._execute_ccxt_order(symbol, type_, side, amount, price, params)

            # Update Order with Exchange ID
            order.external_id = response['id']
            self._update_order_from_exchange(order, response)

            logger.info(f"Order submitted successfully. Exchange ID: {order.external_id}")
            return order

        except (ccxt.NetworkError, ccxt_sync.RateLimitExceeded, ccxt_sync.DDoSProtection) as e:
            logger.error(f"Network/RateLimit Error after retries: {e}")
            # Order status remains PENDING.
            # Reconciliation loop will attempt to find it or mark as FAILED eventually.
            raise e

        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient Funds: {e}")
            order.status = "REJECTED"
            order.save()
            raise e

        except ccxt.ExchangeError as e:
            logger.error(f"Exchange Error (Non-Retryable): {e}")
            order.status = "REJECTED"
            order.save()
            raise e

        except Exception as e:
            logger.error(f"Unexpected Error during submission: {e}")
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
        """Fetch and sync single order status from Exchange."""
        order = self.orders.get(order_id)
        if not order:
            return None

        if not order.external_id:
            return order # Can't sync without external ID

        try:
            # Fetch from exchange
            response = await self.exchange.fetch_order(order.external_id, order.symbol)
            self._update_order_from_exchange(order, response)
            return order
        except Exception as e:
            logger.error(f"Failed to fetch order status {order_id}: {e}")
            return order

    async def sync_orders(self):
        """
        Reconciliation Loop:
        Fetch open orders from exchange and match with local pending orders.
        Updates status of all OPEN/PENDING orders.
        """
        try:
            # 1. Get all local active orders
            active_orders = [o for o in self.orders.values() if o.status in ["OPEN", "PENDING", "PARTIAL"]]
            if not active_orders:
                return

            # 2. Fetch all open orders from exchange (for all symbols involved)
            # Optimization: If many symbols, fetch per symbol or use fetch_open_orders() if exchange supports all
            # Assuming fetch_open_orders() works for all symbols (most exchanges support this)
            try:
                exchange_open_orders = await self.exchange.fetch_open_orders()
            except Exception as e:
                logger.warning(f"Failed to fetch open orders: {e}")
                return # Retry next tick

            exchange_orders_map = {o['id']: o for o in exchange_open_orders}

            # 3. Reconcile
            for order in active_orders:
                if not order.external_id:
                    # Stale pending order? Log warning
                    if (datetime.now(timezone.utc) - order.created_at).total_seconds() > 60:
                         logger.warning(f"Order {order.id} is PENDING > 60s without External ID. Marking FAILED.")
                         order.status = "FAILED"
                         order.save()
                    continue

                if order.external_id in exchange_orders_map:
                    # Still open, update filled amount
                    exch_order = exchange_orders_map[order.external_id]
                    self._update_order_from_exchange(order, exch_order)
                else:
                    # Not in open orders -> It's Closed (Filled, Canceled, Expired)
                    # Need to fetch details to know which one
                    try:
                        closed_order = await self.exchange.fetch_order(order.external_id, order.symbol)
                        self._update_order_from_exchange(order, closed_order)
                    except Exception as e:
                        logger.error(f"Order {order.external_id} not found in Open and failed to fetch: {e}")

        except Exception as e:
            logger.error(f"Sync Orders loop failed: {e}")

    def _update_order_from_exchange(self, order: Order, response: Dict[str, Any]):
        """Helper to map CCXT response to Order model."""
        status_map = {
            'open': 'OPEN',
            'closed': 'FILLED', # CCXT closed usually means filled (or canceled if canceled status)
            'canceled': 'CANCELED',
            'expired': 'EXPIRED',
            'rejected': 'REJECTED'
        }

        ccxt_status = response.get('status', 'open')
        new_status = status_map.get(ccxt_status, 'OPEN')

        # CCXT 'closed' can mean Filled or Canceled depending on exchange, but usually check 'filled' qty
        filled = float(response.get('filled', 0.0))
        amount = float(response.get('amount', 0.0))

        # Logic for Partial Fills
        if filled > 0 and filled < amount:
            if new_status == 'OPEN':
                new_status = 'PARTIAL'
            elif new_status == 'FILLED':
                # Filled status usually implies full fill, but if amount mismatch:
                # Some exchanges mark 'filled' even if partial? Rare.
                # Trust 'filled' qty.
                new_status = 'PARTIAL'

        if new_status == 'FILLED' and filled == 0:
             new_status = 'CANCELED' # Closed but 0 filled usually means canceled

        order.status = new_status

        if 'price' in response and response['price']:
            order.fill_price = float(response['price']) # Average fill price
        elif 'average' in response and response['average']:
             order.fill_price = float(response['average'])

        if 'fee' in response and response['fee']:
            order.commission = float(response['fee']['cost'])

        if new_status in ['FILLED', 'CANCELED', 'EXPIRED', 'REJECTED']:
             if not order.filled_at:
                  order.filled_at = datetime.now(timezone.utc)

        order.save()
        logger.debug(f"Synced Order {order.id}: {order.status} ({filled}/{amount})")

    async def get_balance(self):
        return await self.exchange.fetch_balance()

    async def sync_positions(self) -> Dict[str, float]:
        """
        Fetch current positions from exchange and log them.
        Returns a dict of symbol -> quantity for non-zero positions.
        """
        try:
            balance = await self.exchange.fetch_balance()
            positions = {}

            # 1. Spot Balances
            if 'total' in balance:
                for currency, amount in balance['total'].items():
                    if amount > 0:
                        positions[currency] = amount

            # 2. Future/Swap Positions (if supported/applicable)
            # Some exchanges return this in 'info' or specific 'fetch_positions'
            # For now, we focus on spot balances as primary

            logger.info(f"Exchange Positions: {positions}")
            return positions

        except Exception as e:
            logger.error(f"Failed to sync positions: {e}")
            return {}
