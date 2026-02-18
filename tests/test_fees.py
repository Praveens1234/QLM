import pytest
import pandas as pd
import numpy as np
from backend.core.engine import BacktestEngine
from backend.core.strategy import Strategy

class CommissionStrategy(Strategy):
    def define_variables(self, df): return {}
    def entry_long(self, df, vars):
        s = pd.Series([False]*len(df))
        s.iloc[0] = True
        return s
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit_long_signal(self, df, vars):
        s = pd.Series([False]*len(df))
        s.iloc[1] = True
        return s
    def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return True
    def risk_model(self, df, vars): return {}

def test_commission_impact():
    # Setup Data: Price moves from 100 to 110 (+10 profit)
    dates = pd.date_range(start="2023-01-01", periods=5, freq="1min")
    df = pd.DataFrame({
        "open": [100, 110, 110, 110, 110],
        "high": [100, 110, 110, 110, 110],
        "low": [100, 110, 110, 110, 110],
        "close": [100, 110, 110, 110, 110],
        "volume": [1000]*5,
        "datetime": dates,
        "dtv": dates.astype(np.int64)
    })

    # 1. Percent Commission
    engine = BacktestEngine()
    engine.set_commission(type="percent", value=1.0) # 1% per side

    res = engine._execute_fast(df, CommissionStrategy())
    trade = res['trades'][0]

    # Entry: 100 * 1% = 1.0
    # Exit: 110 * 1% = 1.1
    # Total Comm = 2.1
    # Gross PnL = 10.0
    # Net PnL = 7.9

    assert np.isclose(trade['gross_pnl'], 10.0)
    assert np.isclose(trade['commission'], 2.1)
    assert np.isclose(trade['pnl'], 7.9)

    # 2. Fixed Commission
    engine.set_commission(type="fixed", value=5.0) # $5 per side
    res = engine._execute_fast(df, CommissionStrategy())
    trade = res['trades'][0]

    # Total Comm = 10.0
    # Net PnL = 0.0
    assert np.isclose(trade['commission'], 10.0)
    assert np.isclose(trade['pnl'], 0.0)
