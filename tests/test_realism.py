"""
Tests for realistic market simulation features:
- Slippage (worsens entry/exit prices)
- Spread (bid-ask applied directionally)
- Next-bar entry (deferred to next bar's open)
- Backward compatibility (defaults produce same results)
"""
import pytest
import pandas as pd
import numpy as np
from backend.core.engine import BacktestEngine
from backend.core.strategy import Strategy


class SimpleStrategy(Strategy):
    """Enters long at bar 0, exits at bar 2 via signal."""
    def define_variables(self, df): return {}
    def entry_long(self, df, vars):
        s = pd.Series([False]*len(df))
        s.iloc[0] = True
        return s
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit_long_signal(self, df, vars):
        s = pd.Series([False]*len(df))
        s.iloc[2] = True
        return s
    def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return True
    def risk_model(self, df, vars): return {}


class ShortStrategy(Strategy):
    """Enters short at bar 0, exits at bar 2 via signal."""
    def define_variables(self, df): return {}
    def entry_long(self, df, vars): return pd.Series([False]*len(df))
    def entry_short(self, df, vars):
        s = pd.Series([False]*len(df))
        s.iloc[0] = True
        return s
    def exit_long_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit_short_signal(self, df, vars):
        s = pd.Series([False]*len(df))
        s.iloc[2] = True
        return s
    def exit(self, df, vars, trade): return True
    def risk_model(self, df, vars): return {}


def _make_df(n=5, start="2023-01-02"):
    """Create test DataFrame with known prices."""
    dates = pd.date_range(start=start, periods=n, freq="1min")
    return pd.DataFrame({
        "open":  [100, 102, 104, 106, 108],
        "high":  [101, 103, 105, 107, 109],
        "low":   [99, 101, 103, 105, 107],
        "close": [100, 102, 104, 106, 108],
        "volume": [1000]*n,
        "datetime": dates,
        "dtv": dates.astype(np.int64)
    })


# ─── Test 1: No Realism (Backward Compatible) ───
def test_no_realism_backward_compatible():
    """Default config (no slippage/spread) should produce same results as before."""
    engine = BacktestEngine()
    df = _make_df()
    
    res = engine._execute_fast(df, SimpleStrategy())
    assert len(res['trades']) == 1
    trade = res['trades'][0]
    
    # Entry at bar 0 close (100), Exit at bar 2 close (104)
    assert trade['entry_price'] == 100.0
    assert trade['exit_price'] == 104.0
    assert np.isclose(trade['gross_pnl'], 4.0)


# ─── Test 2: Fixed Slippage Worsens Prices ───
def test_slippage_worsens_prices():
    """Slippage should make entry worse (higher for long) and exit worse (lower for long)."""
    engine = BacktestEngine()
    df = _make_df()
    
    exec_config = {
        "mode": "capital", "initial_capital": 10000.0,
        "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0,
        "slippage_mode": "fixed", "slippage_value": 0.5,
    }
    
    res = engine._execute_fast(df, SimpleStrategy(), exec_config=exec_config)
    assert len(res['trades']) == 1
    trade = res['trades'][0]
    
    # Long entry: 100 + 0.5 = 100.5, Long signal exit: 104 - 0.5 = 103.5
    assert np.isclose(trade['entry_price'], 100.5)
    assert np.isclose(trade['exit_price'], 103.5)
    assert np.isclose(trade['gross_pnl'], 3.0)  # 103.5 - 100.5 = 3.0


# ─── Test 3: Spread Applied Correctly ───
def test_spread_applied():
    """Spread should widen entry/exit prices directionally."""
    engine = BacktestEngine()
    df = _make_df()
    
    exec_config = {
        "mode": "capital", "initial_capital": 10000.0,
        "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0,
        "spread_value": 1.0,  # 1.0 full spread = 0.5 half spread
    }
    
    # Long trade: entry worsened by +0.5, exit worsened by -0.5
    res = engine._execute_fast(df, SimpleStrategy(), exec_config=exec_config)
    assert len(res['trades']) == 1
    trade = res['trades'][0]
    
    assert np.isclose(trade['entry_price'], 100.5)  # 100 + 0.5
    assert np.isclose(trade['exit_price'], 103.5)    # 104 - 0.5
    assert np.isclose(trade['gross_pnl'], 3.0)


# ─── Test 4: Slippage on Short Trades ───
def test_slippage_short_direction():
    """Short trade slippage: entry worsened lower, exit worsened higher."""
    engine = BacktestEngine()
    df = _make_df()
    
    exec_config = {
        "mode": "capital", "initial_capital": 10000.0,
        "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0,
        "slippage_mode": "fixed", "slippage_value": 0.5,
    }
    
    res = engine._execute_fast(df, ShortStrategy(), exec_config=exec_config)
    assert len(res['trades']) == 1
    trade = res['trades'][0]
    
    # Short entry: 100 - 0.5 = 99.5, Short signal exit: 104 + 0.5 = 104.5
    assert np.isclose(trade['entry_price'], 99.5)
    assert np.isclose(trade['exit_price'], 104.5)
    # PnL = (99.5 - 104.5) * 1 = -5.0
    assert np.isclose(trade['gross_pnl'], -5.0)


# ─── Test 5: Next Bar Entry ───
def test_next_bar_entry():
    """When entry_on_next_bar=True, entry at next bar's open, not current close."""
    engine = BacktestEngine()
    df = _make_df()
    
    exec_config = {
        "mode": "capital", "initial_capital": 10000.0,
        "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0,
        "entry_on_next_bar": True,
    }
    
    res = engine._execute_fast(df, SimpleStrategy(), exec_config=exec_config)
    assert len(res['trades']) == 1
    trade = res['trades'][0]
    
    # Signal at bar 0, entry at bar 1 open (102)
    # Exit signal at bar 2, exit at bar 2 close (104)
    assert np.isclose(trade['entry_price'], 102.0)


# ─── Test 6: Combined Slippage + Spread + Next Bar Entry ───
def test_combined_realism():
    """All realism features combined should stack correctly."""
    engine = BacktestEngine()
    df = _make_df()
    
    exec_config = {
        "mode": "capital", "initial_capital": 10000.0,
        "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0,
        "slippage_mode": "fixed", "slippage_value": 0.5,
        "spread_value": 1.0,  # 0.5 half-spread
        "entry_on_next_bar": True,
    }
    
    res = engine._execute_fast(df, SimpleStrategy(), exec_config=exec_config)
    assert len(res['trades']) == 1
    trade = res['trades'][0]
    
    # Long entry at bar 1 open (102) + slip (0.5) + half-spread (0.5) = 103.0
    assert np.isclose(trade['entry_price'], 103.0)


# ─── Test 7: Legacy Engine Parity with Realism ───
def test_realism_engine_parity():
    """Fast and Legacy engines should produce same results with realism features."""
    # Need a strategy where exit() matches exit_long_signal (exit at bar 2)
    class ParityStrategy(Strategy):
        def define_variables(self, df): return {}
        def entry_long(self, df, vars):
            s = pd.Series([False]*len(df))
            s.iloc[0] = True
            return s
        def entry_short(self, df, vars): return pd.Series([False]*len(df))
        def exit_long_signal(self, df, vars):
            s = pd.Series([False]*len(df))
            s.iloc[2] = True
            return s
        def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))
        def exit(self, df, vars, trade):
            return trade['current_idx'] >= 2  # Exit at bar 2 (matches exit_long_signal)
        def risk_model(self, df, vars): return {}
    
    engine = BacktestEngine()
    df = _make_df()
    
    exec_config = {
        "mode": "capital", "initial_capital": 10000.0,
        "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0,
        "slippage_mode": "fixed", "slippage_value": 0.5,
        "spread_value": 1.0,
    }
    
    res_fast = engine._execute_fast(df, ParityStrategy(), exec_config=exec_config)
    res_legacy = engine._execute_legacy(df, ParityStrategy(), exec_config=exec_config)
    
    assert len(res_fast['trades']) == len(res_legacy['trades'])
    
    for tf, tl in zip(res_fast['trades'], res_legacy['trades']):
        assert np.isclose(tf['entry_price'], tl['entry_price'], atol=0.01)
        assert np.isclose(tf['exit_price'], tl['exit_price'], atol=0.01)
        assert np.isclose(tf['gross_pnl'], tl['gross_pnl'], atol=0.01)
