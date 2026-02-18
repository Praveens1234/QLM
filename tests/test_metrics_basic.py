import pytest
from backend.core.metrics import PerformanceEngine
from tests.reference_metrics import ReferenceMetrics

def test_basic_metrics():
    # Scenario 1: Mixed trades
    trades = [
        {"pnl": 100.0, "exit_time": "2023-01-01", "duration": 60},
        {"pnl": -50.0, "exit_time": "2023-01-02", "duration": 60},
        {"pnl": 200.0, "exit_time": "2023-01-03", "duration": 60},
        {"pnl": -100.0, "exit_time": "2023-01-04", "duration": 60}
    ]
    pnls = [100.0, -50.0, 200.0, -100.0]

    metrics = PerformanceEngine.calculate_metrics(trades)

    # Assert against Reference Implementation
    assert metrics["net_profit"] == ReferenceMetrics.net_profit(pnls)
    assert metrics["win_rate"] == ReferenceMetrics.win_rate(pnls)
    assert metrics["profit_factor"] == ReferenceMetrics.profit_factor(pnls)

    # Manual Checks
    assert metrics["total_trades"] == 4
    assert metrics["net_profit"] == 150.0
    assert metrics["win_rate"] == 50.0 # 2 wins / 4
    assert metrics["profit_factor"] == 2.0 # 300 / 150

def test_all_loss():
    trades = [{"pnl": -10.0, "exit_time": "1", "duration": 1}] * 5
    metrics = PerformanceEngine.calculate_metrics(trades)
    assert metrics["win_rate"] == 0.0
    assert metrics["profit_factor"] == 0.0
    assert metrics["net_profit"] == -50.0

def test_all_win():
    trades = [{"pnl": 10.0, "exit_time": "1", "duration": 1}] * 5
    metrics = PerformanceEngine.calculate_metrics(trades)
    assert metrics["win_rate"] == 100.0
    assert metrics["profit_factor"] == float('inf')
    assert metrics["net_profit"] == 50.0

def test_empty_trades():
    metrics = PerformanceEngine.calculate_metrics([])
    assert metrics["total_trades"] == 0
    assert metrics["net_profit"] == 0.0
