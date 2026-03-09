# QLM Strategy Coding Guidelines

When writing or modifying a trading strategy for the QLM (QuantLogic Framework) engine via the `create_strategy` tool, you must adhere strictly to the following syntax, interface, and security requirements. 

## 1. Security & Imports
For security reasons, the code is analyzed dynamically via an Abstract Syntax Tree (AST) before it is allowed to run.
*   **Allowed Root Modules:** `math`, `numpy`, `pandas`, `typing`, `datetime`, `collections`, `itertools`, `functools`, `random`, `statistics`, `scipy`, `sklearn`, `talib`, `backend`
*   **Restricted Sub-Modules (DO NOT IMPORT):** `backend.database`, `backend.core.system`, `backend.api`
*   **Blocked Built-in Functions (DO NOT USE):** `exec()`, `eval()`, `__import__()`, `open()`, `compile()`, `globals()`, `locals()`, `input()`, `breakpoint()`
*   The class MUST inherit from `backend.core.strategy.Strategy`.

## 2. Base Structure
Every strategy must define a class inheriting from `Strategy` and implement five strictly typed mandatory methods.

```python
from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MyStrategy(Strategy):
    """
    Author: MCP Client
    Description: A sample structure.
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """
        Step 1: Calculate all indicators globally.
        You MUST return a dictionary mapping string names to pandas Series.
        Use vectorized logic here (e.g., df['close'].rolling(14).mean()).
        """
        return {
            'sma_14': df['close'].rolling(14).mean(),
            'sma_50': df['close'].rolling(50).mean()
        }

    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Step 2a: Define exact conditions to enter a Long position.
        You MUST return a boolean pandas Series of the identical length as df.
        True = Enter Long immediately.
        """
        return (df['close'] > vars['sma_14']) & (vars['sma_14'] > vars['sma_50'])

    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Step 2b: Define exact conditions to enter a Short position.
        Returns a boolean pandas Series. 
        If you only trade Longs, return a Series of pure False.
        """
        return pd.Series([False] * len(df), index=df.index)

    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Step 3: Define dynamic Stop Loss (sl) and Take Profit (tp) logic.
        You MUST return a Dictionary mapping 'sl' and/or 'tp' to a pandas Series (or a scalar).
        """
        return {
            'sl': df['close'] * 0.95,  # 5% stop loss
            'tp': df['close'] * 1.10   # 10% take profit
        }

    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Step 4: Dynamic (Slow Mode) Exit Logic applied tick-by-tick internally by the engine.
        `trade` is a dict with keys: `entry_time`, `entry_price`, `direction`, `sl`, `tp`, `current_idx`.
        MUST return a single boolean True/False indicating whether to exit immediately.
        """
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        
        # Example dynamic trailing stop logic
        if trade['direction'] == 'long' and current_close < vars['sma_14'][idx]:
            return True
        return False
```

## 3. Fast Mode Execution (Optional Vectorized Exmits)
While `exit()` is mandatory, QLM allows for **Fast Mode** execution if you provide purely vectorized exit signals via these two optional methods. When these are provided along with valid `entry_long`/`entry_short` vectorized arrays, the engine can skip the tick-by-tick iteration, creating massive speed improvements.

```python
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Vectorized Exit. Returns a boolean Series. True = Exit open long positions.
        """
        return df['close'] < vars['sma_14']

    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Vectorized Exit. Returns a boolean Series. True = Exit open short positions.
        """
        return pd.Series(False, index=df.index)
```

## 4. Crucial Reminders
1. `entry_long`, `entry_short`, `exit_long_signal`, and `exit_short_signal` MUST return a `pd.Series` composed of exactly boolean `True`/`False` values spanning the entire `df.index`. Failure to cast to pure boolean series will crash the simulation!
2. All methods expect the `df` argument, representing raw standard columns (`open`, `high`, `low`, `close`, `volume`, `datetime`). 
3. Include comprehensive error handling if your indicators could yield `NaN` values, as `NaN`s in boolean execution arrays invalidate the array. For example, fill `NaN` results using `.fillna(False)`.
