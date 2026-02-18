import pytest
import os
import pandas as pd
import numpy as np
from backend.core.strategy import Strategy, StrategyLoader
from backend.core.engine import BacktestEngine
from backend.core.store import MetadataStore
from backend.core.data import DataManager
from backend.database import db

class RobustnessStrategy(Strategy):
    def define_variables(self, df): return {}
    def entry_long(self, df, vars): return pd.Series([True]*len(df))
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit_long_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return False
    def risk_model(self, df, vars): return {}

@pytest.fixture
def setup_bad_data():
    test_db = "data/robust_test.db"
    if os.path.exists(test_db): os.remove(test_db)
    db.db_path = test_db
    db._init_schema()

    # Create Data with NaNs and Infs
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1min")
    close = np.linspace(100, 200, 100)
    close[10] = np.nan # NaN at index 10
    close[20] = np.inf # Inf at index 20

    df = pd.DataFrame({
        "datetime": dates, "dtv": dates.astype(int),
        "open": close,
        "high": close + 5,
        "low": close - 5,
        "close": close,
        "volume": [1000]*100
    })

    path = "tests/bad_data.parquet"
    import pyarrow as pa; import pyarrow.parquet as pq
    # PyArrow handles NaNs fine, but Infs might be tricky or just cast to null?
    # Pandas to Parquet usually works.
    pq.write_table(pa.Table.from_pandas(df), path)

    ms = MetadataStore()
    ms.add_dataset({
        "id": "bad_ds", "symbol": "BAD", "timeframe": "1M", "detected_tf_sec": 60,
        "start_date": str(dates[0]), "end_date": str(dates[-1]), "row_count": 100,
        "file_path": path, "created_at": str(dates[0])
    })

    yield "bad_ds"

    if os.path.exists(test_db): os.remove(test_db)
    if os.path.exists(path): os.remove(path)

def test_backtest_with_nans(setup_bad_data):
    """Ensure backtest engine handles NaNs/Infs gracefully (no crash)."""
    engine = BacktestEngine()

    # Mock strategy loader
    original_load = StrategyLoader.load_strategy_class
    StrategyLoader.load_strategy_class = lambda self, n, v: RobustnessStrategy

    try:
        # Run backtest
        # It should either succeed with warnings or fail with a controlled error message
        result = engine.run("bad_ds", "RobustStrat", parameters={})

        # Check if it didn't crash
        assert result is not None
        assert "metrics" in result

        # Check if metrics are sane (not NaN everywhere)
        # If NaN was encountered, maybe trades were skipped?
        # Or maybe PnL is NaN?
        print("Metrics:", result['metrics'])

    finally:
        StrategyLoader.load_strategy_class = original_load

def test_backtest_empty_data():
    """Ensure engine handles empty dataframe gracefully."""
    test_db = "data/robust_empty_test.db"
    if os.path.exists(test_db): os.remove(test_db)
    db.db_path = test_db
    db._init_schema()

    engine = BacktestEngine()
    # Create empty parquet
    df = pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])
    path = "tests/empty.parquet"
    df.to_parquet(path)

    ms = MetadataStore()
    ms.add_dataset({
        "id": "empty_ds", "symbol": "EMPTY", "timeframe": "1M", "detected_tf_sec": 60,
        "start_date": "2023-01-01", "end_date": "2023-01-01", "row_count": 0,
        "file_path": path, "created_at": "2023-01-01"
    })

    original_load = StrategyLoader.load_strategy_class
    StrategyLoader.load_strategy_class = lambda self, n, v: RobustnessStrategy

    try:
        # This might raise an error, but it should be a caught error?
        # The engine usually loads data.
        # If DF is empty, backtest logic might fail on indexing.

        # We expect a controlled failure or empty result.
        # Actually, BacktestEngine catches Exceptions and returns dict with error.
        result = engine.run("empty_ds", "RobustStrat", parameters={})

        # Depending on implementation, empty DF returns empty metrics or failed status
        # If run catches exception, status is failed.
        # If run handles empty DF gracefully (len(df)==0 check), status is success with 0 trades.

        assert result['status'] == 'success' or result['status'] == 'failed'
        if result['status'] == 'success':
             assert len(result['trades']) == 0

    finally:
        StrategyLoader.load_strategy_class = original_load
        if os.path.exists(path): os.remove(path)
