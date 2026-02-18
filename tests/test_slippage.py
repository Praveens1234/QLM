import pytest
import asyncio
from backend.core.execution import PaperTradingAdapter, Order

@pytest.mark.asyncio
async def test_slippage_direction():
    # 5% Slippage (500 bps)
    adapter = PaperTradingAdapter(latency_ms=0, slippage_bps=500, commission_pct=0.0)

    # Mock Market Price
    adapter.update_price("TEST", 100.0)

    # 1. Buy Order: Should slip UP (Price > 100)
    buy_order = Order("TEST", 1, "BUY")
    filled_buy = await adapter.submit_order(buy_order)
    assert filled_buy.fill_price >= 100.0

    # 2. Sell Order: Should slip DOWN (Price < 100)
    sell_order = Order("TEST", 1, "SELL")
    filled_sell = await adapter.submit_order(sell_order)
    assert filled_sell.fill_price <= 100.0

@pytest.mark.asyncio
async def test_slippage_distribution():
    # Statistical check
    adapter = PaperTradingAdapter(latency_ms=0, slippage_bps=100, commission_pct=0.0) # 1% max
    adapter.update_price("TEST", 100.0)

    fills = []
    for _ in range(100):
        o = await adapter.submit_order(Order("TEST", 1, "BUY"))
        fills.append(o.fill_price)

    avg_fill = sum(fills) / len(fills)
    # Average slippage should be around 0.5% (uniform 0 to 1%) -> Price ~100.5
    assert 100.2 < avg_fill < 100.8
