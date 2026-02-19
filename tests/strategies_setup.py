from backend.core.strategy import Strategy
import pandas as pd
import numpy as np
from typing import Dict, Any

class StandardStrategy(Strategy):
    """
    Standard SMA Crossover Strategy.
    Vectorized for Fast Engine.
    """
    def __init__(self, parameters: Dict[str, Any] = None):
        super().__init__(parameters)
        self.fast_window = self.parameters.get('fast_window', 10)
        self.slow_window = self.parameters.get('slow_window', 50)

    def define_variables(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        fast_ma = df['close'].rolling(window=self.fast_window).mean()
        slow_ma = df['close'].rolling(window=self.slow_window).mean()
        return {
            "fast_ma": fast_ma,
            "slow_ma": slow_ma
        }

    def entry_long(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        # Cross Over
        return (vars['fast_ma'] > vars['slow_ma']) & (vars['fast_ma'].shift(1) <= vars['slow_ma'].shift(1))

    def entry_short(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        # Cross Under
        return (vars['fast_ma'] < vars['slow_ma']) & (vars['fast_ma'].shift(1) >= vars['slow_ma'].shift(1))

    def exit_long_signal(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        # Exit Long when Fast < Slow
        return vars['fast_ma'] < vars['slow_ma']

    def exit_short_signal(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        # Exit Short when Fast > Slow
        return vars['fast_ma'] > vars['slow_ma']

    def exit(self, df: pd.DataFrame, vars: Dict[str, pd.Series], trade: Dict[str, Any]) -> bool:
        # Legacy Loop Exit
        idx = trade['current_idx']
        fast = vars['fast_ma'].iloc[idx]
        slow = vars['slow_ma'].iloc[idx]

        if trade['direction'] == 'long':
            return fast < slow
        else:
            return fast > slow

    def risk_model(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        # Simple Stop Loss at 1%
        sl_pct = 0.01

        # Calculate SL levels
        # For Long: Close * (1 - 0.01)
        # For Short: Close * (1 + 0.01)
        # Note: In risk_model we usually return fixed levels or ATR based.
        # Here we return arrays for engine to pick at entry time.

        # Actually risk_model returns dict of Series.
        # But 'sl' is determined at entry.
        # The engine uses `sl_arr[i]` at entry time.

        sl_long = df['close'] * (1 - sl_pct)
        sl_short = df['close'] * (1 + sl_pct)

        # We need a single SL array?
        # The engine picks `sl_arr[i]`.
        # If we have both signals, how does it know which SL to use?
        # Typically the strategy logic calculates it.
        # Let's just return a generic SL array assuming Entry logic handles direction.
        # Wait, `run_numba_backtest` takes `sl_arr`.
        # If `entry_long[i]` is true, it uses `sl_arr[i]`.
        # If `entry_short[i]` is true, it uses `sl_arr[i]`.

        # So we can't easily have different logic in one array if both signals technically "could" exist (though mutually exclusive usually).
        # We'll use a hack: Combine them.

        # Better: use ATR.
        atr = df['high'].rolling(14).max() - df['low'].rolling(14).min() # Approx

        # But to match logic:
        # If long, SL = close - ATR
        # If short, SL = close + ATR

        sl = pd.Series(np.nan, index=df.index)

        # We don't know direction yet in this function context for the array construction fully.
        # Ideally `risk_model` returns specific 'sl_long' and 'sl_short' but the engine expects 'sl'.
        # Let's leave SL/TP empty for this simple test to rely on signal exits.
        return {}

class BrokenStrategy(Strategy):
    """
    Malicious/Broken Strategy for testing validation.
    """
    def define_variables(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        import os # Security Violation
        os.system("echo 'Malicious'")
        return {}

    def entry_long(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return pd.Series([True]*len(df))

    def entry_short(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return pd.Series([False]*len(df))

    def exit(self, df: pd.DataFrame, vars: Dict[str, pd.Series], trade: Dict[str, Any]) -> bool:
        return False

    def risk_model(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        return {}
