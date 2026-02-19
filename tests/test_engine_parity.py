import unittest
import pandas as pd
import numpy as np
from typing import Dict, Any
from backend.core.strategy import Strategy
from backend.core.engine import BacktestEngine
from backend.core.store import MetadataStore

class ParityStrategy(Strategy):
    """
    A strategy designed to produce identical results in both Fast and Legacy modes.
    Enters on RSI < 30 (Long), Exits on RSI > 70.
    """
    def define_variables(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        # Simple RSI implementation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return {"rsi": rsi}

    def entry_long(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return vars['rsi'] < 30

    def entry_short(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return pd.Series(False, index=df.index)

    def exit_long_signal(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        # Vectorized Exit
        return vars['rsi'] > 70

    def exit_short_signal(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return pd.Series(False, index=df.index)

    def exit(self, df: pd.DataFrame, vars: Dict[str, pd.Series], trade: Dict[str, Any]) -> bool:
        # Legacy Loop Exit
        current_idx = trade['current_idx']
        # Check if RSI > 70 at current_idx
        # Note: current_idx is integer index
        # We need to access the Series by integer location
        rsi_val = vars['rsi'].iloc[current_idx]
        return rsi_val > 70

    def risk_model(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        return {}

class TestEngineParity(unittest.TestCase):
    def setUp(self):
        # Create a dummy dataset
        dates = pd.date_range(start="2023-01-01", periods=1000, freq="h")
        # Generate a sine wave price to ensure RSI oscillates
        prices = 100 + 10 * np.sin(np.linspace(0, 10*np.pi, 1000))

        self.df = pd.DataFrame({
            "open": prices, "high": prices+1, "low": prices-1, "close": prices, "volume": 1000,
            "datetime": dates,
            "dtv": dates.astype('int64')
        })

        # Save dataset metadata so engine can load it
        # Wait, engine loads from file. We need to mock DataManager or write a file.
        # It's easier to mock DataManager.load_dataset

        self.engine = BacktestEngine()
        # Mocking DataManager.load_dataset
        self.engine.data_manager.load_dataset = lambda path: self.df

        # Mock MetadataStore to return dummy meta
        # Since engine instantiates MetadataStore internally, we need to patch it or ensure it works.
        # But wait, MetadataStore interacts with DB.

        # StrategyLoader is also used.
        # We can bypass engine.run and call _execute directly if we want to isolate engine logic.
        # Yes, calling _execute_fast and _execute_legacy directly is better for unit testing logic.

    def test_parity(self):
        strategy = ParityStrategy()

        # Run Fast
        fast_results = self.engine._execute_fast(self.df, strategy)

        # Run Legacy
        legacy_results = self.engine._execute_legacy(self.df, strategy)

        # Compare Metrics
        metrics_fast = fast_results['metrics']
        metrics_legacy = legacy_results['metrics']

        # Check Total Trades
        self.assertEqual(metrics_fast['total_trades'], metrics_legacy['total_trades'],
                         f"Trade count mismatch: Fast={metrics_fast['total_trades']}, Legacy={metrics_legacy['total_trades']}")

        # Check Net Profit
        self.assertAlmostEqual(metrics_fast['net_profit'], metrics_legacy['net_profit'], places=2,
                               msg=f"Net Profit mismatch: Fast={metrics_fast['net_profit']}, Legacy={metrics_legacy['net_profit']}")

        # Compare Individual Trades (first 5)
        trades_fast = fast_results['trades']
        trades_legacy = legacy_results['trades']

        for i in range(min(len(trades_fast), len(trades_legacy))):
            tf = trades_fast[i]
            tl = trades_legacy[i]

            self.assertEqual(tf['entry_time'], tl['entry_time'])
            self.assertEqual(tf['exit_time'], tl['exit_time'])
            self.assertAlmostEqual(tf['entry_price'], tl['entry_price'], places=4)
            self.assertAlmostEqual(tf['exit_price'], tl['exit_price'], places=4)
            self.assertAlmostEqual(tf['pnl'], tl['pnl'], places=4)

if __name__ == '__main__':
    unittest.main()
