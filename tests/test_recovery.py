import pytest
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.core.trading_engine import TradingEngine
from backend.core.execution import Order
from backend.database import db

@pytest.fixture
def setup_db():
    test_db = "data/recovery_test.db"
    if os.path.exists(test_db): os.remove(test_db)
    db.db_path = test_db
    db._init_schema()
    yield
    if os.path.exists(test_db): os.remove(test_db)

@pytest.mark.asyncio
async def test_engine_recovery(setup_db):
    """Verify that Trading Engine initializes and recovers persistent state."""

    # 1. Pre-seed DB with an active order (simulating a crash)
    order = Order("BTC/USDT", 0.1, "BUY", "LIMIT", price=50000)
    order.status = "PENDING"
    order.save()

    # 2. Initialize Engine (Paper Mode)
    engine = TradingEngine(mode="PAPER")
    await engine.initialize()

    # 3. Verify Order is loaded
    handler = engine.execution_handler
    assert len(handler.orders) == 1
    assert order.id in handler.orders
    assert handler.orders[order.id].status == "PENDING"

    # 4. Cleanup
    await engine.shutdown()

@pytest.mark.asyncio
async def test_live_engine_initialization(setup_db):
    """Verify Live Engine init loads CCXT and connects."""
    config = {"exchange_id": "binance", "api_key": "k", "secret": "s", "sandbox": True}

    # Patch the class where it is IMPORTED in trading_engine
    with patch("backend.core.trading_engine.LiveExecutionHandler") as MockHandler:
        mock_instance = AsyncMock()
        MockHandler.return_value = mock_instance

        engine = TradingEngine(mode="LIVE", exchange_config=config)
        await engine.initialize()

        MockHandler.assert_called_once()
        mock_instance.initialize.assert_called_once()

        await engine.shutdown()
