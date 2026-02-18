import pytest
import numpy as np
from backend.core.metrics import PerformanceEngine
from tests.reference_metrics import ReferenceMetrics

def test_sharpe_ratio():
    # Scenario: Steady returns
    trades = [
        {"pnl": 10.0, "exit_time": "1", "duration": 1},
        {"pnl": 10.0, "exit_time": "2", "duration": 1},
        {"pnl": 10.0, "exit_time": "3", "duration": 1},
    ]
    metrics = PerformanceEngine.calculate_metrics(trades)
    # StdDev is 0, so Sharpe should be 0 (handled gracefully)
    assert metrics["sharpe_ratio"] == 0.0

    # Scenario: Volatile returns
    trades_vol = [
        {"pnl": 100.0, "exit_time": "1", "duration": 1},
        {"pnl": -50.0, "exit_time": "2", "duration": 1},
        {"pnl": 20.0, "exit_time": "3", "duration": 1},
    ]
    pnls = [100.0, -50.0, 20.0]
    metrics = PerformanceEngine.calculate_metrics(trades_vol)

    ref_sharpe = ReferenceMetrics.sharpe_ratio(pnls)
    assert np.isclose(metrics["sharpe_ratio"], ref_sharpe, atol=0.01)

def test_sortino_ratio():
    # Scenario: Only upside volatility (Sortino should be inf or high, but we handle div/0)
    trades = [
        {"pnl": 10.0, "exit_time": "1", "duration": 1},
        {"pnl": 20.0, "exit_time": "2", "duration": 1},
    ]
    metrics = PerformanceEngine.calculate_metrics(trades)
    assert metrics["sortino_ratio"] == 0.0 # Downside std is 0

    # Scenario: Downside volatility
    trades_down = [
        {"pnl": 100.0, "exit_time": "1", "duration": 1},
        {"pnl": -50.0, "exit_time": "2", "duration": 1},
        {"pnl": -10.0, "exit_time": "3", "duration": 1},
    ]
    pnls = [100.0, -50.0, -10.0]
    metrics = PerformanceEngine.calculate_metrics(trades_down)

    ref_sortino = ReferenceMetrics.sortino_ratio(pnls)
    assert np.isclose(metrics["sortino_ratio"], ref_sortino, atol=0.01)

def test_sqn_logic():
    # SQN = sqrt(N) * (Mean / Std)
    trades = [
        {"pnl": 10.0, "exit_time": "1", "duration": 1},
        {"pnl": -10.0, "exit_time": "2", "duration": 1},
        {"pnl": 30.0, "exit_time": "3", "duration": 1},
        {"pnl": 10.0, "exit_time": "4", "duration": 1}
    ]
    # Mean = 10, Std ~ 16.32
    metrics = PerformanceEngine.calculate_metrics(trades)

    pnls = [10.0, -10.0, 30.0, 10.0]
    n = len(pnls)
    mean = np.mean(pnls)
    std = np.std(pnls, ddof=1)
    expected_sqn = (n**0.5) * (mean / std)

    assert np.isclose(metrics["sqn"], expected_sqn, atol=0.01)
