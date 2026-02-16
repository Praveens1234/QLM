import unittest
import pandas as pd
import numpy as np
import tempfile
import os
import shutil
from backend.ai.analytics import optimize_strategy
from backend.core.strategy import Strategy
from backend.core.store import MetadataStore
from backend.database import db

# Mock Strategy that uses parameters
class ParamStrategy(Strategy):
    def define_variables(self, df: pd.DataFrame):
        # Use 'window' parameter, default 10
        window = self.parameters.get('window', 10)
        df['sma'] = df['close'].rolling(window).mean()
        return {}

    def entry_long(self, df: pd.DataFrame, vars):
        return (df['close'] > df['sma']) & (df['close'].shift(1) <= df['sma'].shift(1))

    def entry_short(self, df: pd.DataFrame, vars):
        return pd.Series(False, index=df.index)

    def exit_long_signal(self, df: pd.DataFrame, vars):
        return (df['close'] < df['sma'])

    def risk_model(self, df: pd.DataFrame, vars):
        return {'sl': None, 'tp': None}

class TestOptimization(unittest.TestCase):
    def setUp(self):
        self.test_db_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_db_dir, "test_opt.db")
        db.db_path = self.test_db_path
        db._init_schema()

        self.store = MetadataStore()

        # Create Data
        dates = pd.date_range(start="2023-01-01", periods=200, freq="h")
        prices = np.linspace(100, 200, 200) + np.sin(np.linspace(0, 20, 200))*10
        df = pd.DataFrame({
            "open": prices, "high": prices+1, "low": prices-1, "close": prices, "volume": 1000,
            "datetime": dates, "dtv": dates.astype(np.int64)
        })

        self.temp_dir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.temp_dir, "opt_data.parquet")
        df.to_parquet(self.file_path)

        self.dataset_id = "opt_dataset"
        self.store.add_dataset({
            "id": self.dataset_id, "symbol": "OPT", "timeframe": "1H",
            "detected_tf_sec": 3600, "start_date": str(dates[0]), "end_date": str(dates[-1]),
            "row_count": len(df), "file_path": self.file_path, "created_at": "2023-01-01"
        })

        # Register Mock Strategy via StrategyLoader is tricky because it loads from disk.
        # So we have to write it to disk.
        import uuid
        self.strat_name = f"ParamStrat_{uuid.uuid4().hex}"
        self.strat_dir = os.path.join("strategies", self.strat_name)
        os.makedirs(self.strat_dir, exist_ok=True)

        code = """
from backend.core.strategy import Strategy
import pandas as pd

class ParamStrategy(Strategy):
    def define_variables(self, df: pd.DataFrame):
        window = self.parameters.get('window', 10)
        df['sma'] = df['close'].rolling(window).mean()
        return {}

    def entry_long(self, df: pd.DataFrame, vars):
        return (df['close'] > df['sma']) & (df['close'].shift(1) <= df['sma'].shift(1))

    def entry_short(self, df: pd.DataFrame, vars):
        return pd.Series(False, index=df.index)

    def exit_long_signal(self, df: pd.DataFrame, vars):
        return (df['close'] < df['sma'])

    def exit_short_signal(self, df: pd.DataFrame, vars):
        return pd.Series(False, index=df.index)

    def risk_model(self, df: pd.DataFrame, vars):
        return {'sl': None, 'tp': None}
"""
        with open(os.path.join(self.strat_dir, "v1.py"), "w") as f:
            f.write(code)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.test_db_dir)
        if os.path.exists(self.strat_dir):
            shutil.rmtree(self.strat_dir)

    def test_optimize(self):
        param_grid = {"window": [5, 10, 20]}

        # We need to make sure the strategy loader finds our new file
        # Check backend/core/strategy.py StrategyLoader default dir

        result = optimize_strategy(self.strat_name, self.dataset_id, param_grid)

        self.assertEqual(result['status'], 'success')
        self.assertIn('best_params', result)
        self.assertIn('window', result['best_params'])
        print(f"Best Params: {result['best_params']}")
        print(f"Total Runs: {result['total_runs']}")
        self.assertEqual(result['total_runs'], 3)

if __name__ == '__main__':
    unittest.main()
