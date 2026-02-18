import pytest
import pandas as pd
from backend.core.metrics import PerformanceEngine
from tests.reference_metrics import ReferenceMetrics

def test_drawdown_calculation():
    # Construct a specific equity curve:
    # 10000 -> 10100 (Peak 1) -> 10050 -> 10200 (Peak 2) -> 9000 (DD) -> 9500
    initial = 10000.0
    trades = [
        {"pnl": 100.0, "exit_time": "1"}, # Eq: 10100
        {"pnl": -50.0, "exit_time": "2"}, # Eq: 10050 (-50 DD from 10100)
        {"pnl": 150.0, "exit_time": "3"}, # Eq: 10200 (New Peak)
        {"pnl": -1200.0, "exit_time": "4"}, # Eq: 9000 (DD = 1200 from 10200)
        {"pnl": 500.0, "exit_time": "5"}  # Eq: 9500
    ]

    metrics = PerformanceEngine.calculate_metrics(trades, initial_capital=initial)

    # Expected Max DD: 10200 - 9000 = 1200
    assert metrics["max_drawdown"] == 1200.0

    # Expected Max DD %: (1200 / 10200) * 100 = 11.7647...
    expected_pct = (1200 / 10200) * 100
    assert abs(metrics["max_drawdown_pct"] - expected_pct) < 0.01

    # Verify against reference
    pnls = [100, -50, 150, -1200, 500]
    ref_dd = ReferenceMetrics.max_drawdown(pnls, initial)
    assert metrics["max_drawdown"] == ref_dd

def test_drawdown_at_start():
    # Immediate loss from start
    initial = 10000.0
    trades = [{"pnl": -100.0, "exit_time": "1"}]
    metrics = PerformanceEngine.calculate_metrics(trades, initial_capital=initial)
    assert metrics["max_drawdown"] == 100.0
    assert metrics["max_drawdown_pct"] == 1.0

def test_zero_drawdown():
    # Only wins
    trades = [{"pnl": 100.0, "exit_time": "1"}, {"pnl": 100.0, "exit_time": "2"}]
    metrics = PerformanceEngine.calculate_metrics(trades)
    assert metrics["max_drawdown"] == 0.0
    assert metrics["max_drawdown_pct"] == 0.0
