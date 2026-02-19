import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from backend.core.execution_live import LiveExecutionHandler, Order
from backend.core.exceptions import QLMSystemError
import ccxt.async_support as ccxt
import ccxt as ccxt_sync

class TestLiveExecutionMock(unittest.IsolatedAsyncioTestCase):

    @patch('backend.core.execution_live.ccxt') # Patches ccxt.async_support
    @patch('backend.core.execution_live.ccxt_sync') # Patches ccxt_sync
    async def test_submit_order_retry(self, mock_ccxt_sync, mock_ccxt_async):
        # Setup Exceptions
        mock_ccxt_async.NetworkError = ccxt.NetworkError
        mock_ccxt_sync.RateLimitExceeded = ccxt_sync.RateLimitExceeded
        mock_ccxt_sync.DDoSProtection = ccxt_sync.DDoSProtection

        # Setup Mock Exchange
        mock_exchange = AsyncMock()
        # set_sandbox_mode is synchronous
        mock_exchange.set_sandbox_mode = MagicMock()

        mock_exchange_class = MagicMock(return_value=mock_exchange)
        mock_ccxt_async.binance = mock_exchange_class

        # Initialize Handler
        handler = LiveExecutionHandler("binance", "key", "secret")

        # Create Order
        order = Order("BTC/USDT", 0.1, "BUY")

        # Setup Retry Behavior: Fail twice, succeed on third
        mock_exchange.create_order.side_effect = [
            ccxt.NetworkError("Fail 1"),
            ccxt.NetworkError("Fail 2"),
            {'id': '12345', 'status': 'closed', 'filled': 0.1, 'amount': 0.1, 'price': 50000.0}
        ]

        # Execute
        result_order = await handler.submit_order(order)

        # Verify
        self.assertEqual(result_order.external_id, '12345')
        self.assertEqual(result_order.status, 'FILLED')
        self.assertEqual(mock_exchange.create_order.call_count, 3)

    @patch('backend.core.execution_live.ccxt')
    @patch('backend.core.execution_live.ccxt_sync')
    async def test_submit_order_fail(self, mock_ccxt_sync, mock_ccxt_async):
        # Setup Exceptions
        mock_ccxt_async.NetworkError = ccxt.NetworkError
        mock_ccxt_async.ExchangeError = ccxt.ExchangeError
        mock_ccxt_async.InsufficientFunds = ccxt.InsufficientFunds # Added this
        mock_ccxt_sync.RateLimitExceeded = ccxt_sync.RateLimitExceeded
        mock_ccxt_sync.DDoSProtection = ccxt_sync.DDoSProtection

        # Setup Mock Exchange
        mock_exchange = AsyncMock()
        mock_exchange.set_sandbox_mode = MagicMock()
        mock_exchange_class = MagicMock(return_value=mock_exchange)
        mock_ccxt_async.binance = mock_exchange_class

        handler = LiveExecutionHandler("binance", "key", "secret")
        order = Order("BTC/USDT", 0.1, "BUY")

        # Fail immediately with ExchangeError (non-retryable)
        mock_exchange.create_order.side_effect = ccxt.ExchangeError("Invalid Symbol")

        with self.assertRaises(ccxt.ExchangeError):
            await handler.submit_order(order)

        self.assertEqual(mock_exchange.create_order.call_count, 1)
        self.assertEqual(order.status, 'REJECTED')

    @patch('backend.core.execution_live.ccxt')
    @patch('backend.core.execution_live.ccxt_sync')
    async def test_sync_orders(self, mock_ccxt_sync, mock_ccxt_async):
        # Setup Mock
        mock_exchange = AsyncMock()
        mock_exchange.set_sandbox_mode = MagicMock()
        mock_exchange_class = MagicMock(return_value=mock_exchange)
        mock_ccxt_async.binance = mock_exchange_class

        handler = LiveExecutionHandler("binance", "key", "secret")

        # Create Dummy Local Orders
        o1 = Order("BTC/USDT", 0.1, "BUY", id="local_1")
        o1.external_id = "ex_1"
        o1.status = "OPEN"
        handler.orders["local_1"] = o1

        # Mock fetch_open_orders
        # Return status 'open' but filled > 0 -> Should be PARTIAL
        mock_exchange.fetch_open_orders.return_value = [
            {'id': 'ex_1', 'status': 'open', 'filled': 0.05, 'amount': 0.1} # Partial fill
        ]

        # Run Sync
        await handler.sync_orders()

        self.assertEqual(o1.status, 'PARTIAL')

if __name__ == '__main__':
    unittest.main()
