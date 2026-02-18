import pytest
import os
import pandas as pd
import numpy as np
from backend.core.strategy import Strategy, StrategyLoader
from backend.core.engine import BacktestEngine
from backend.core.store import MetadataStore
from backend.core.data import DataManager
from backend.database import db

class RTestStrategy(Strategy):
    def define_variables(self, df): return {}
    def entry_long(self, df, vars):
        # Enter at index 0
        s = pd.Series([False]*len(df))
        s.iloc[0] = True
        return s
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit_long_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return False
    def risk_model(self, df, vars):
        # SL 10 points below, TP 20 points above
        # If price is 100, SL=90, TP=120. Risk=10.
        sl = df['close'] - 10
        tp = df['close'] + 20
        return {"sl": sl, "tp": tp}

@pytest.fixture
def setup_r_data():
    test_db = "data/r_test.db"
    if os.path.exists(test_db): os.remove(test_db)
    db.db_path = test_db
    db._init_schema()

    # Create Data
    # 0: Close 100. (Entry Long. SL=90, TP=120)
    # 1: Close 110.
    # 2: Close 120. (Hit TP)
    # PnL = 20. Risk = 10. R = 2.0.

    dates = pd.date_range(start="2023-01-01", periods=10, freq="1min")
    df = pd.DataFrame({
        "datetime": dates, "dtv": dates.astype(int),
        "open": [100, 110, 120] + [120]*7,
        "high": [105, 115, 125] + [120]*7,
        "low": [95, 105, 115] + [120]*7,
        "close": [100, 110, 120] + [120]*7,
        "volume": [100]*10
    })

    path = "tests/r_data.parquet"
    import pyarrow as pa; import pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pandas(df), path)

    ms = MetadataStore()
    ms.add_dataset({
        "id": "r_ds", "symbol": "R", "timeframe": "1M", "detected_tf_sec": 60,
        "start_date": str(dates[0]), "end_date": str(dates[-1]), "row_count": 10,
        "file_path": path, "created_at": str(dates[0])
    })

    yield "r_ds"

    if os.path.exists(test_db): os.remove(test_db)
    if os.path.exists(path): os.remove(path)

def test_r_calculation_fast(setup_r_data):
    """Verify Numba engine calculates R-Multiple correctly."""
    engine = BacktestEngine()
    engine.set_commission("percent", 0.0)

    original_load = StrategyLoader.load_strategy_class
    StrategyLoader.load_strategy_class = lambda self, n, v: RTestStrategy

    try:
        res = engine.run("r_ds", "RStrat", use_fast=True)
        trades = res['trades']
        assert len(trades) == 1
        t = trades[0]

        # Entry 100. Exit 120. PnL 20.
        # SL 90. Risk 10.
        # R = 2.0
        assert t['entry_price'] == 100.0
        assert t['initial_risk'] == 10.0
        assert t['r_multiple'] == 2.0

        assert res['metrics']['avg_r_multiple'] == 2.0

    finally:
        StrategyLoader.load_strategy_class = original_load

def test_r_calculation_legacy(setup_r_data):
    """Verify Legacy engine calculates R-Multiple correctly."""
    engine = BacktestEngine()
    engine.set_commission("percent", 0.0)

    original_load = StrategyLoader.load_strategy_class
    StrategyLoader.load_strategy_class = lambda self, n, v: RTestStrategy

    try:
        res = engine.run("r_ds", "RStrat", use_fast=False)
        trades = res['trades']
        assert len(trades) == 1
        t = trades[0]

        # Legacy engine logic is same
        assert t['entry_price'] == 100.0
        assert t['initial_risk'] == 10.0
        assert t['r_multiple'] == 2.0

        assert res['metrics']['avg_r_multiple'] == 2.0

    finally:
        StrategyLoader.load_strategy_class = original_load
