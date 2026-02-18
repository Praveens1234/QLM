import pytest
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.core.execution_live import LiveExecutionHandler
from backend.core.execution import Order
from backend.database import db

@pytest.fixture
def setup_db():
    test_db = "data/live_test.db"
    if os.path.exists(test_db): os.remove(test_db)
    db.db_path = test_db
    db._init_schema()
    yield
    if os.path.exists(test_db): os.remove(test_db)

@pytest.mark.asyncio
async def test_live_execution_submit(setup_db):
    # Mock CCXT
    with patch("ccxt.async_support.binance") as MockExchange:
        # Setup Mock instance
        mock_ex = AsyncMock()
        MockExchange.return_value = mock_ex

        # Setup create_order response
        mock_ex.create_order.return_value = {
            "id": "external_123",
            "status": "closed",
            "price": 150.0,
            "fee": {"cost": 0.15}
        }

        handler = LiveExecutionHandler("binance", "key", "secret")

        order = Order("BTC/USDT", 0.1, "BUY", "MARKET")
        submitted_order = await handler.submit_order(order)

        # Verify calls
        mock_ex.create_order.assert_called_once()

        # Verify Order State
        assert submitted_order.status == "FILLED"
        assert submitted_order.external_id == "external_123"
        assert submitted_order.fill_price == 150.0
        assert submitted_order.commission == 0.15

        # Verify Persistence
        loaded = Order.load(submitted_order.id)
        assert loaded.external_id == "external_123"
        assert loaded.status == "FILLED"

@pytest.mark.asyncio
async def test_live_execution_cancel(setup_db):
    with patch("ccxt.async_support.binance") as MockExchange:
        mock_ex = AsyncMock()
        MockExchange.return_value = mock_ex

        handler = LiveExecutionHandler("binance", "key", "secret")

        # Create an order manually in DB with external ID
        order = Order("BTC/USDT", 0.1, "BUY", "LIMIT", price=100.0)
        order.external_id = "ext_cancel_1"
        order.status = "OPEN"
        order.save()
        handler.orders[order.id] = order

        # Cancel
        success = await handler.cancel_order(order.id)

        assert success is True
        mock_ex.cancel_order.assert_called_with("ext_cancel_1", "BTC/USDT")

        # Verify DB status
        loaded = Order.load(order.id)
        assert loaded.status == "CANCELLED"
