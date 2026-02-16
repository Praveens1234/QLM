import unittest
import pandas as pd
import numpy as np
import tempfile
import os
import shutil
from backend.core.engine import BacktestEngine
from backend.core.strategy import Strategy
from backend.core.data import DataManager
from backend.core.store import MetadataStore
from backend.database import db

class MockStrategy(Strategy):
    def define_variables(self, df: pd.DataFrame):
        df['sma'] = df['close'].rolling(10).mean()
        return {}

    def entry_long(self, df: pd.DataFrame, vars):
        # Enter if close > sma
        return (df['close'] > df['sma']) & (df['close'].shift(1) <= df['sma'].shift(1))

    def entry_short(self, df: pd.DataFrame, vars):
        return pd.Series(False, index=df.index)

    def exit_long_signal(self, df: pd.DataFrame, vars):
        # Exit if close < sma
        return (df['close'] < df['sma'])

    def exit_short_signal(self, df: pd.DataFrame, vars):
        return pd.Series(False, index=df.index)

    def risk_model(self, df: pd.DataFrame, vars):
        return {'sl': None, 'tp': None}

class TestPerformance(unittest.TestCase):
    def setUp(self):
        # Setup DB
        self.test_db_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_db_dir, "test.db")
        db.db_path = self.test_db_path
        db._init_schema()

        self.store = MetadataStore()
        self.data_manager = DataManager()

        # Create Dummy Data
        dates = pd.date_range(start="2023-01-01", periods=1000, freq="h")
        # Create a sine wave price to generate signals
        x = np.linspace(0, 50, 1000)
        prices = 100 + 10 * np.sin(x) + np.random.normal(0, 0.5, 1000)

        self.df = pd.DataFrame({
            "open": prices, "high": prices + 1, "low": prices - 1, "close": prices, "volume": 1000,
            "datetime": dates,
            "dtv": dates.astype(np.int64)
        })

        # Save Parquet
        self.temp_dir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.temp_dir, "test_data.parquet")
        self.df.to_parquet(self.file_path)

        # Add to store
        self.dataset_id = "test_perf_dataset"
        self.store.add_dataset({
            "id": self.dataset_id,
            "symbol": "TEST",
            "timeframe": "1H",
            "detected_tf_sec": 3600,
            "start_date": str(dates[0]),
            "end_date": str(dates[-1]),
            "row_count": len(self.df),
            "file_path": self.file_path,
            "created_at": "2023-01-01"
        })

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        with db.get_connection() as conn:
            conn.execute("DELETE FROM datasets WHERE id = ?", (self.dataset_id,))

    def test_fast_vs_slow(self):
        engine = BacktestEngine()

        # We need to bypass the StrategyLoader and inject our MockStrategy
        # Since engine.run loads strategy by name, we need to mock that part or
        # just call _execute directly.

        strategy = MockStrategy()

        # Run Slow
        print("Running Slow Mode...")
        res_slow = engine._execute(self.df, strategy, use_fast=False)

        # Run Fast
        print("Running Fast Mode...")
        res_fast = engine._execute(self.df, strategy, use_fast=True)

        print(f"Slow Trades: {len(res_slow['trades'])}")
        print(f"Fast Trades: {len(res_fast['trades'])}")

        self.assertEqual(len(res_slow['trades']), len(res_fast['trades']))

        if len(res_slow['trades']) > 0:
            # Check first trade details
            t1 = res_slow['trades'][0]
            t2 = res_fast['trades'][0]

            self.assertEqual(t1['entry_time'], t2['entry_time'])
            self.assertAlmostEqual(t1['entry_price'], t2['entry_price'], places=5)
            self.assertAlmostEqual(t1['pnl'], t2['pnl'], places=5)

if __name__ == '__main__':
    unittest.main()
