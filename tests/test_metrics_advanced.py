import pytest
from backend.core.metrics import PerformanceEngine
import pandas as pd
import numpy as np

def test_duration_metrics():
    trades = [
        {"pnl": 100, "duration": 10.0, "exit_time": "2023-01-01 10:10:00", "mae": 0.0, "mfe": 0.0},
        {"pnl": -50, "duration": 20.0, "exit_time": "2023-01-01 10:20:00", "mae": 0.0, "mfe": 0.0},
        {"pnl": 100, "duration": 30.0, "exit_time": "2023-01-02 10:30:00", "mae": 0.0, "mfe": 0.0}
    ]

    metrics = PerformanceEngine.calculate_metrics(trades)

    assert metrics['avg_duration'] == 20.0 # (10+20+30)/3
    assert metrics['max_duration'] == 30.0
    assert metrics['min_duration'] == 10.0

def test_time_analysis_metrics():
    # 2 trades, 1 day apart (approx)
    # Trade 1 exit: Jan 1
    # Trade 2 exit: Jan 2
    # Delta days = 1
    # Trades per day = 2 / 1 = 2.0

    trades = [
        {"pnl": 10, "duration": 1, "exit_time": "2023-01-01 10:00:00"},
        {"pnl": 10, "duration": 1, "exit_time": "2023-01-02 10:00:00"}
    ]

    metrics = PerformanceEngine.calculate_metrics(trades)

    assert metrics['trades_per_day'] == 2.0

    # 2 trades same day
    trades_same_day = [
        {"pnl": 10, "duration": 1, "exit_time": "2023-01-01 10:00:00"},
        {"pnl": 10, "duration": 1, "exit_time": "2023-01-01 12:00:00"}
    ]
    metrics2 = PerformanceEngine.calculate_metrics(trades_same_day)
    # Delta days = 0. Trades per day = total trades = 2.0
    assert metrics2['trades_per_day'] == 2.0

    # 3 trades over 2 days (Jan 1 to Jan 3) -> 2 days diff
    trades_spread = [
        {"pnl": 10, "duration": 1, "exit_time": "2023-01-01 10:00:00"},
        {"pnl": 10, "duration": 1, "exit_time": "2023-01-02 10:00:00"},
        {"pnl": 10, "duration": 1, "exit_time": "2023-01-03 10:00:00"}
    ]
    metrics3 = PerformanceEngine.calculate_metrics(trades_spread)
    # Delta days = 2.
    # Trades per day = 3 / 2 = 1.5
    assert metrics3['trades_per_day'] == 1.5

def test_mae_mfe_metrics():
    trades = [
        {"pnl": 10, "duration": 1, "exit_time": "2023-01-01", "mae": 5.0, "mfe": 10.0},
        {"pnl": 10, "duration": 1, "exit_time": "2023-01-02", "mae": 10.0, "mfe": 20.0}
    ]

    metrics = PerformanceEngine.calculate_metrics(trades)

    assert metrics['avg_mae'] == 7.5
    assert metrics['avg_mfe'] == 15.0
