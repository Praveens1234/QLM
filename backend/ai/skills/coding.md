# Strategy Coding Skill

**Goal**: Write high-performance, vectorized Python strategy code for the QLM Engine.

## 1. Core Architecture
All strategies **must** inherit from `backend.core.strategy.Strategy` and implement these methods:

```python
from backend.core.strategy import Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta  # Available if needed, or use raw pandas

class MyStrategy(Strategy):

    def define_variables(self, df: pd.DataFrame) -> dict:
        """
        Calculate indicators here. Returns a dict of Series.
        Optimization: Calculate ONCE here, do not recalc in loops.
        """
        # Example: Vectorized SMA
        close = df['close']
        sma_fast = close.rolling(20).mean()
        sma_slow = close.rolling(50).mean()
        atr = ta.atr(df['high'], df['low'], df['close'], length=14)

        return {
            'sma_fast': sma_fast,
            'sma_slow': sma_slow,
            'atr': atr
        }

    def entry_long(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        """
        Return Boolean Series. True = Enter Long.
        """
        # Crossover: Fast > Slow
        crossover = (vars['sma_fast'] > vars['sma_slow']) & (vars['sma_fast'].shift(1) <= vars['sma_slow'].shift(1))
        return crossover

    def entry_short(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        """
        Return Boolean Series. True = Enter Short.
        """
        crossunder = (vars['sma_fast'] < vars['sma_slow']) & (vars['sma_fast'].shift(1) >= vars['sma_slow'].shift(1))
        return crossunder

    def risk_model(self, df: pd.DataFrame, vars: dict) -> dict:
        """
        Define Stop Loss (sl) and Take Profit (tp) levels for EVERY candle.
        The engine captures the values at the moment of entry.
        """
        atr = vars['atr'].fillna(0)
        close = df['close']

        return {
            # Long: SL below, TP above
            'sl': close - (atr * 1.5),
            'tp': close + (atr * 2.0)
        }

    def exit(self, df: pd.DataFrame, vars: dict, trade: dict) -> bool:
        """
        Custom exit logic (e.g., indicator reversal).
        Called iteratively (can be slower, keep simple).
        Returns True to close the trade.
        """
        idx = trade['current_idx']
        # Example: Exit if price falls below SMA 50
        current_close = df['close'].iloc[idx]
        sma_50 = vars['sma_slow'].iloc[idx]

        if trade['direction'] == 'long' and current_close < sma_50:
            return True
        return False
```

## 2. Best Practices
*   **Vectorization**: Always use `pandas` or `numpy` for indicators. Avoid iterating rows in `define_variables`.
*   **NaN Handling**: Indicators (like SMA-50) produce `NaN` for the first N rows. Use `.fillna(0)` or handle carefully.
*   **Lookahead Bias**: Never use `.shift(-1)`. You can only see current (`iloc[i]`) and past (`iloc[i-1]`) data.
*   **Performance**: The `exit()` method is called in a loop. Do not recalculate indicators there. Access pre-calculated `vars`.
