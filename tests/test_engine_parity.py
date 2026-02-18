import pytest
import pandas as pd
import numpy as np
from backend.core.engine import BacktestEngine
from backend.core.strategy import Strategy

class ParityStrategy(Strategy):
    def define_variables(self, df): return {}
    def entry_long(self, df, vars):
        # Enter every 10th candle
        s = pd.Series([False]*len(df))
        s[::10] = True
        return s
    def entry_short(self, df, vars): return pd.Series([False]*len(df))

    # Vectorized Exit (Fast Mode)
    def exit_long_signal(self, df, vars):
        # Exit 5 candles later
        s = pd.Series([False]*len(df))
        s[5::10] = True
        return s
    def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))

    # Legacy Exit (Slow Mode)
    def exit(self, df, vars, trade):
        current_idx = trade.get('current_idx')
        # Logic matching vectorized: Exit if idx % 10 == 5
        return (current_idx % 10) == 5

    def risk_model(self, df, vars): return {}

def test_engine_parity():
    # 1. Create Data
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1min")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 100),
        "high": np.linspace(101, 111, 100),
        "low": np.linspace(99, 109, 100),
        "close": np.linspace(100.5, 110.5, 100),
        "volume": [1000]*100,
        "datetime": dates,
        "dtv": dates.astype(np.int64)
    })

    engine = BacktestEngine()

    # 2. Run Fast
    res_fast = engine._execute_fast(df, ParityStrategy())

    # 3. Run Legacy
    res_legacy = engine._execute_legacy(df, ParityStrategy())

    # 4. Compare Trades
    trades_fast = res_fast['trades']
    trades_legacy = res_legacy['trades']

    assert len(trades_fast) == len(trades_legacy)
    assert len(trades_fast) > 0

    for tf, tl in zip(trades_fast, trades_legacy):
        assert tf['entry_time'] == tl['entry_time']
        assert tf['exit_time'] == tl['exit_time']
        assert np.isclose(tf['pnl'], tl['pnl'])
        assert tf['exit_reason'] == tl['exit_reason']
