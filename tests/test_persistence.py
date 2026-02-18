import pytest
import os
import asyncio
from backend.core.execution import PaperTradingAdapter, Order
from backend.database import db

@pytest.fixture
def setup_db():
    test_db = "data/persist_test.db"
    if os.path.exists(test_db): os.remove(test_db)
    db.db_path = test_db
    db._init_schema()
    yield
    if os.path.exists(test_db): os.remove(test_db)

@pytest.mark.asyncio
async def test_order_persistence(setup_db):
    # 1. Create Adapter 1
    adapter1 = PaperTradingAdapter(latency_ms=0)

    # 2. Submit Order (remains PENDING because no price update -> rejected? No.)
    # Wait, PaperTradingAdapter _execute checks price.
    # If no price, it sets status REJECTED immediately.
    # We want PENDING.
    # Submit -> latency -> _execute.
    # If we want it to stay pending, we must interrupt it?
    # Or we can just manually save an order to DB to simulate a crash before execution?

    # Let's create an order manually and save it.
    order = Order("AAPL", 10, "BUY", "MARKET", id="test_order_1")
    order.status = "PENDING"
    order.save()

    # 3. Create Adapter 2 (Simulate Restart)
    adapter2 = PaperTradingAdapter(latency_ms=0)

    # 4. Verify Order Loaded
    assert "test_order_1" in adapter2.orders
    loaded_order = adapter2.orders["test_order_1"]
    assert loaded_order.symbol == "AAPL"
    assert loaded_order.quantity == 10
    assert loaded_order.status == "PENDING"

@pytest.mark.asyncio
async def test_order_execution_persistence(setup_db):
    # Test full cycle
    adapter = PaperTradingAdapter(latency_ms=0)
    adapter.update_price("AAPL", 150.0)

    order = Order("AAPL", 10, "BUY", "MARKET")
    await adapter.submit_order(order)

    assert order.status == "FILLED"

    # Verify DB
    loaded = Order.load(order.id)
    assert loaded is not None
    assert loaded.status == "FILLED"
    assert loaded.fill_price is not None
