import pytest
import pandas as pd
import numpy as np
from backend.core.engine import BacktestEngine
from backend.core.strategy import Strategy

class ExcursionStrategy(Strategy):
    def define_variables(self, df): return {}
    def entry_long(self, df, vars):
        # Enter at index 0 (Price 100)
        s = pd.Series([False]*len(df))
        s.iloc[0] = True
        return s
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit_long_signal(self, df, vars):
        # Exit at index 2 (Price 100)
        s = pd.Series([False]*len(df))
        s.iloc[2] = True
        return s
    def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return True
    def risk_model(self, df, vars): return {}

def test_mae_mfe_accuracy():
    dates = pd.date_range(start="2023-01-01", periods=3, freq="1min")
    # 0: Entry @ 100
    # 1: High 120 (MFE +20), Low 80 (MAE -20), Close 100
    # 2: Exit @ 100
    df = pd.DataFrame({
        "open": [100, 100, 100],
        "high": [105, 120, 105],
        "low": [95, 80, 95],
        "close": [100, 100, 100],
        "volume": [1000]*3,
        "datetime": dates,
        "dtv": dates.astype(np.int64)
    })

    engine = BacktestEngine()
    res = engine._execute_fast(df, ExcursionStrategy())
    trade = res['trades'][0]

    # Entry Price: 100
    # Max High during trade (Index 1): 120 -> MFE = 20
    # Max Low during trade (Index 1): 80 -> MAE = 20
    # Note: Index 0 (Entry bar) high/low might participate depending on implementation?
    # Usually intrabar MFE/MAE on entry bar is calculated from Entry price to High/Low.
    # Numba engine logic:
    # On entry bar: MFE/MAE reset to 0.
    # But wait, logic is inside the loop.
    # If entry happens, active_idx becomes i.
    # Then NEXT iteration (i+1) checks exit and updates MAE/MFE.
    # What about the entry bar itself?
    # Current Numba: `curr_mae = 0.0`. It does NOT scan the entry bar rest-of-bar.
    # Ideally it should: High[i] - Entry, Entry - Low[i].

    # Let's check result for Index 1 (Middle bar).
    # It should definitely catch 120 and 80.

    assert np.isclose(trade['mfe'], 20.0)
    assert np.isclose(trade['mae'], 20.0)
