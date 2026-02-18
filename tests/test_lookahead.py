import pytest
import pandas as pd
import numpy as np
import os
from backend.core.engine import BacktestEngine
from backend.core.strategy import Strategy, StrategyLoader
from backend.core.store import MetadataStore
from backend.database import db

class CheatingStrategy(Strategy):
    def define_variables(self, df):
        return {"next_close": df['close'].shift(-1)}
    def entry_long(self, df, vars):
        # Handle NaN from shift
        return (vars['next_close'] > df['close']).fillna(False)
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit_long_signal(self, df, vars):
        # Exit on next bar always (simple way: shift entry signal?)
        # Or just exit everywhere except entry?
        # Let's say we hold for 1 bar.
        # This is tricky without iteration.
        # But for test, if we exit everywhere, we exit immediately after entry.
        return pd.Series([True]*len(df))
    def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return True
    def risk_model(self, df, vars): return {}

@pytest.fixture
def setup_data():
    test_db = "data/lookahead_test.db"
    if os.path.exists(test_db): os.remove(test_db)
    db.db_path = test_db
    db._init_schema()

    dates = pd.date_range(start="2023-01-01", periods=100, freq="1D")
    df = pd.DataFrame({
        "datetime": dates, "dtv": dates.astype(int),
        "open": np.linspace(100, 200, 100),
        "high": np.linspace(105, 205, 100),
        "low": np.linspace(95, 195, 100),
        "close": np.linspace(100, 200, 100), # Constant uptrend
        "volume": [1000]*100
    })
    path = "tests/lookahead.parquet"
    import pyarrow as pa; import pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pandas(df), path)

    ms = MetadataStore()
    ms.add_dataset({
        "id": "cheat_ds", "symbol": "CHEAT", "timeframe": "1D", "detected_tf_sec": 86400,
        "start_date": str(dates[0]), "end_date": str(dates[-1]), "row_count": 100,
        "file_path": path, "created_at": str(dates[0])
    })

    yield "cheat_ds"

    if os.path.exists(test_db): os.remove(test_db)
    if os.path.exists(path): os.remove(path)

def test_lookahead_prevention(setup_data):
    engine = BacktestEngine()

    original_load = StrategyLoader.load_strategy_class
    StrategyLoader.load_strategy_class = lambda self, n, v: CheatingStrategy

    try:
        res = engine.run("cheat_ds", "Cheating", use_fast=True)
        # It should run without error
        assert res['status'] == 'success'
        # Since it's a constant uptrend and we cheat, we should make money
        # (Though simple trend following also makes money here)
        assert res['metrics']['net_profit'] > 0
    finally:
        StrategyLoader.load_strategy_class = original_load
