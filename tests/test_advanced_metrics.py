import pandas as pd
import numpy as np
import logging
from backend.core.engine import BacktestEngine
from backend.core.strategy import Strategy
from backend.core.metrics import PerformanceEngine
from unittest.mock import MagicMock

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Test_Metrics")

class MockStrategy(Strategy):
    def define_variables(self, df: pd.DataFrame) -> dict:
        return {}

    def entry_long(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        # Buy on index 1, 4
        s = pd.Series(False, index=df.index)
        s.iloc[1] = True
        s.iloc[4] = True
        return s

    def entry_short(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        # Short on index 7
        s = pd.Series(False, index=df.index)
        s.iloc[7] = True
        return s

    def exit(self, df: pd.DataFrame, vars: dict, trade: dict) -> bool:
        # Simple Logic: Exit on specific indices
        idx = trade.get('current_idx')
        if idx in [3, 6, 9]:
            return True
        return False

    def risk_model(self, df: pd.DataFrame, vars: dict) -> dict:
        # Handled in monkey patch
        return {}

    def position_size(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        return pd.Series(1.0, index=df.index)

def test_metrics():
    # 1. Create Data
    dates = pd.date_range(start="2024-01-01", periods=15, freq="D")
    df = pd.DataFrame({
        "open": [100.0]*15,
        "high": [104.0]*15, # Safe High (below 105)
        "low": [96.0]*15, # Safe Low (above 95)
        "close": [100.0]*15,
        "volume": [1000]*15,
        "datetime": dates,
        "dtv": dates.astype('int64')
    })

    # Manipulate prices to create outcomes

    # Trade 1: Long at idx 1. Entry 100. SL 95. TP 110.
    # Exit at idx 3.
    # Let's make it a WIN via Signal.
    df.loc[2, 'high'] = 104 # Safe
    df.loc[2, 'low'] = 96   # Safe
    df.loc[3, 'close'] = 108 # Exit at 108. PnL +8.
    df.loc[3, 'high'] = 109 # Safe (TP 110)

    # Trade 2: Long at idx 4. Entry 100. SL 95.
    # Exit at idx 6.
    # LOSS. Price drops.
    df.loc[5, 'low'] = 92 # Drop below SL? 92 < 95. SL Hit!
    # Wait, if SL Hit at 95, exit is 95.
    # Test expects PnL < 0. Status Unprofitable.
    # If SL Hit, exit is SL (95). PnL -5.

    # Trade 3: Short at idx 7. Entry 100. SL 105. TP 90.
    # Exit at idx 9.
    # WIN via Signal.
    df.loc[8, 'high'] = 104 # Safe (SL 105)
    df.loc[8, 'low'] = 96 # Safe
    df.loc[9, 'close'] = 92 # Exit at 92. Short from 100 -> +8.
    df.loc[9, 'low'] = 91 # Safe (TP 90)


    sl_series = pd.Series([np.nan]*15)
    tp_series = pd.Series([np.nan]*15)

    # Longs at 1, 4
    sl_series[1] = 95.0
    tp_series[1] = 110.0
    sl_series[4] = 95.0
    tp_series[4] = 110.0

    # Short at 7
    sl_series[7] = 105.0
    tp_series[7] = 90.0

    strategy = MockStrategy()
    # Monkey patch the risk model to return our crafted series
    strategy.risk_model = lambda df, v: {'sl': sl_series, 'tp': tp_series}

    # 2. Run Engine
    engine = BacktestEngine()

    # Engine._execute takes an instance. Access it directly.
    results = engine._execute(df, strategy)

    # 3. Verify Trades
    trades = results['trades']
    logger.info(f"Trades Generated: {len(trades)}")

    assert len(trades) == 3

    # Trade 1 (Long Win)
    t1 = trades[0]
    assert t1['direction'] == 'long'
    assert t1['pnl'] > 0
    assert t1['status'] == 'Profitable' # Signal Exit
    assert t1['initial_risk'] == 5.0 # 100 - 95
    # R = 8 / 5 = 1.6

    # Trade 2 (Long Loss)
    t2 = trades[1]
    assert t2['direction'] == 'long'
    assert t2['pnl'] < 0
    assert t2['status'] == 'SL Hit'
    assert t2['initial_risk'] == 5.0
    # R = -5 / 5 = -1.0 (SL Hit at 95)

    # Trade 3 (Short Win)
    t3 = trades[2]
    assert t3['direction'] == 'short'
    assert t3['pnl'] > 0
    assert t3['status'] == 'Profitable'
    assert t3['initial_risk'] == 5.0 # |100 - 105|
    # R = 8 / 5 = 1.6

    # 4. Verify Metrics
    metrics = results['metrics']
    logger.info(f"Metrics: {metrics}")

    assert metrics['total_trades'] == 3
    assert metrics['win_rate'] == 66.67 # 2/3
    assert metrics['win_rate_long'] == 50.0 # 1/2
    assert metrics['win_rate_short'] == 100.0 # 1/1
    assert metrics['net_profit'] == 11.0 # 8 - 5 + 8 = 11

    # 5. Verify CSV
    csv_str = PerformanceEngine.generate_csv(trades)
    logger.info(f"CSV Output:\n{csv_str}")

    assert "entry_time,exit_time" in csv_str
    assert "100.0" in csv_str # Prices
    assert "Profitable" in csv_str

    print("✅ Test Passed Successfully")

if __name__ == "__main__":
    test_metrics()
