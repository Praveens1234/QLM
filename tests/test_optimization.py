import pytest
import os
import shutil
import pandas as pd
import numpy as np
from backend.core.strategy import Strategy
from backend.core.store import MetadataStore
from backend.core.data import DataManager
from backend.ai.analytics import optimize_strategy, optimize_strategy_genetic
from backend.database import db

class OptimizationStrategy(Strategy):
    def __init__(self, parameters=None):
        self.parameters = parameters or {"ma_fast": 10, "ma_slow": 20}

    def define_variables(self, df):
        return {}

    def entry_long(self, df, vars):
        # Win if parameters match target
        win = (self.parameters["ma_fast"] == 5) and (self.parameters["ma_slow"] == 10)

        # Simple oscillation strategy: Buy on even indices (Low price)
        # We rely on the fact that prices oscillate 100, 110, 100, 110...
        # We only trade if "win" condition (correct params) is met
        if not win:
             return pd.Series([False]*len(df))

        # Enter every other bar starting at 0
        s = pd.Series([False]*len(df))
        s.iloc[::2] = True
        return s

    def entry_short(self, df, vars): return pd.Series([False]*len(df))

    def exit_long_signal(self, df, vars):
        # Exit every other bar starting at 1
        s = pd.Series([False]*len(df))
        s.iloc[1::2] = True
        return s

    def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return True
    def risk_model(self, df, vars): return {}

@pytest.fixture
def setup_opt_data():
    test_db = "data/opt_test.db"
    if os.path.exists(test_db): os.remove(test_db)
    db.db_path = test_db
    db._init_schema()

    # Create Dummy Data with oscillation
    # 20 bars
    # Even indices (0, 2, ...): Close 100
    # Odd indices (1, 3, ...): Close 110
    # Strategy buys at 100, sells at 110. Profit 10 per trade.
    # Total 10 trades.
    n = 20
    dates = pd.date_range(start="2023-01-01", periods=n, freq="1min")
    closes = [100 if i % 2 == 0 else 110 for i in range(n)]

    df = pd.DataFrame({
        "datetime": dates, "dtv": dates.astype(int),
        "open": closes,
        "high": [120]*n,
        "low": [80]*n,
        "close": closes,
        "volume": [100]*n
    })
    path = "tests/opt_data.parquet"
    import pyarrow as pa; import pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pandas(df), path)

    ms = MetadataStore()
    ms.add_dataset({
        "id": "opt_ds", "symbol": "OPT", "timeframe": "1M", "detected_tf_sec": 60,
        "start_date": str(dates[0]), "end_date": str(dates[-1]), "row_count": n,
        "file_path": path, "created_at": str(dates[0])
    })

    yield "opt_ds"

    if os.path.exists(test_db): os.remove(test_db)
    if os.path.exists(path): os.remove(path)

def test_grid_search(setup_opt_data):
    from backend.core.strategy import StrategyLoader
    original_load = StrategyLoader.load_strategy_class
    StrategyLoader.load_strategy_class = lambda self, n, v: OptimizationStrategy

    try:
        param_grid = {
            "ma_fast": [5, 10],
            "ma_slow": [10, 20]
        }

        result = optimize_strategy("OptStrat", setup_opt_data, param_grid)

        best = result["best_params"]
        # Expect 5, 10 to be best because only that combo generates trades/profit
        assert best["ma_fast"] == 5
        assert best["ma_slow"] == 10
        assert result["best_metrics"]["net_profit"] > 0
        assert result["best_metrics"]["total_trades"] == 10

    finally:
        StrategyLoader.load_strategy_class = original_load

def test_genetic_optimization_repeated(setup_opt_data):
    """Ensure we can run GA multiple times without DEAP creator errors."""
    from backend.core.strategy import StrategyLoader
    original_load = StrategyLoader.load_strategy_class
    StrategyLoader.load_strategy_class = lambda self, n, v: OptimizationStrategy

    try:
        param_grid = {
            "ma_fast": [5, 10],
            "ma_slow": [10, 20]
        }

        # Run 1
        optimize_strategy_genetic("OptStrat", setup_opt_data, param_grid, population_size=5, generations=2)

        # Run 2
        optimize_strategy_genetic("OptStrat", setup_opt_data, param_grid, population_size=5, generations=2)

    finally:
        StrategyLoader.load_strategy_class = original_load

def test_genetic_optimization(setup_opt_data):
    from backend.core.strategy import StrategyLoader
    original_load = StrategyLoader.load_strategy_class
    StrategyLoader.load_strategy_class = lambda self, n, v: OptimizationStrategy

    try:
        # Genetic needs a larger search space to be meaningful, but for test we keep it simple
        # We include the "winning" combo: 5, 10
        # Reduce search space to ensure deterministic success in test environment
        param_grid = {
            "ma_fast": [5, 10],
            "ma_slow": [10, 20]
        }

        result = optimize_strategy_genetic(
            "OptStrat",
            setup_opt_data,
            param_grid,
            population_size=10,
            generations=5
        )

        best = result["best_params"]
        # It should find 5, 10 because all others return 0 profit (fitness -inf or 0)
        assert best["ma_fast"] == 5
        assert best["ma_slow"] == 10
        assert result["best_metrics"]["net_profit"] > 0
        assert result["best_metrics"]["total_trades"] == 10

    finally:
        StrategyLoader.load_strategy_class = original_load
