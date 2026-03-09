---
description: Comprehensive rules and guidelines for coding QLM trading strategies
---

# QLM Strategy Coding Rules

This document defines every rule and convention for writing strategies in the QLM backtesting engine.

---

## 1. File Location & Naming

- Strategies live in `strategies/{StrategyName}/v{N}.py`
- `{StrategyName}` is the folder name (spaces allowed, e.g. `RSI 2`)
- `v{N}.py` is the version file (e.g. `v1.py`, `v2.py`)
- Each version is a complete, self-contained strategy file
- The engine always loads the **latest version** unless specified

---

## 2. Required Imports

```python
from backend.core.strategy import Strategy
import pandas as pd
import numpy as np
```

---

## 3. Class Structure

Your strategy **must** be a class that inherits from `Strategy`:

```python
class MyStrategy(Strategy):
    """
    Strategy description goes here.
    """
    pass
```

> **IMPORTANT**: There must be exactly ONE class that inherits from `Strategy` per file.

---

## 4. Constructor & Parameters

The base class provides `__init__` and `set_parameters`:

```python
def __init__(self, parameters: Dict[str, Any] = None):
    self.parameters = parameters or {}
```

- Access parameters via `self.parameters.get('key', default_value)`
- **NEVER hardcode values** that should be optimizable
- Always provide sensible defaults

**Example:**
```python
rsi_period = int(self.parameters.get('rsi_period', 14))
sma_period = int(self.parameters.get('sma_period', 200))
```

---

## 5. Required Methods (Abstract — MUST override)

### 5.1 `define_variables(self, df: pd.DataFrame) -> dict`

Compute all indicators/variables. Called **once** before the backtest loop.

**Rules:**
- `df` contains columns: `datetime`, `open`, `high`, `low`, `close`, `volume`, `dtv`
- Return a `dict` of `pd.Series` (same index as `df`)
- Use vectorized pandas/numpy — no loops
- All parameters must come from `self.parameters`

```python
def define_variables(self, df):
    close = df['close']
    period = int(self.parameters.get('sma_period', 50))
    sma = close.rolling(window=period).mean()
    return {"sma": sma, "close": close}
```

### 5.2 `entry_long(self, df: pd.DataFrame, vars: dict) -> pd.Series`

Return a **boolean Series** where `True` = enter long at that bar's close.

```python
def entry_long(self, df, vars):
    return vars['close'] > vars['sma']
```

### 5.3 `entry_short(self, df: pd.DataFrame, vars: dict) -> pd.Series`

Return a **boolean Series** where `True` = enter short at that bar's close.

```python
def entry_short(self, df, vars):
    return vars['close'] < vars['sma']
```

### 5.4 `exit(self, df: pd.DataFrame, vars: dict, trade: dict) -> bool`

Per-bar exit check for legacy engine. Return `True` to exit.

**`trade` dict contains:**
- `direction`: `"long"` or `"short"`
- `entry_price`: float
- `current_idx`: int (current bar index)

```python
def exit(self, df, vars, trade):
    idx = trade['current_idx']
    if trade['direction'] == 'long':
        return vars['close'].iloc[idx] < vars['sma'].iloc[idx]
    else:
        return vars['close'].iloc[idx] > vars['sma'].iloc[idx]
```

### 5.5 `risk_model(self, df: pd.DataFrame, vars: dict) -> dict`

Define Stop Loss and Take Profit levels.

**Return format (choose ONE):**

**Option A — Distance-based (recommended):**
```python
return {
    "stop_loss_dist": atr * 2.0,      # scalar or Series
    "take_profit_dist": atr * 3.0,     # scalar or Series
}
```

**Option B — Absolute price levels:**
```python
return {
    "sl": close - atr * 2.0,    # pd.Series
    "tp": close + atr * 3.0,    # pd.Series
}
```

**Rules:**
- The engine auto-converts distances to absolute prices per bar
- For distance mode, SL and TP are applied directionally (long: SL below, TP above; short: reversed)
- Return `np.nan` or omit keys if no SL/TP is desired

---

## 6. Optional Methods

### 6.1 `exit_long_signal(self, df, vars) -> pd.Series`

Vectorized exit signal for long positions (used by Fast Engine).
Default: all `False` (no vectorized exit).

```python
def exit_long_signal(self, df, vars):
    return vars['close'] < vars['sma']  # Exit long when price drops below SMA
```

### 6.2 `exit_short_signal(self, df, vars) -> pd.Series`

Vectorized exit signal for short positions.
Default: all `False`.

### 6.3 `position_size(self, df, vars) -> pd.Series`

Custom position sizing per bar. Default: `1.0` for all bars.

Only used when the API `position_sizing` is set to `"strategy_defined"`.

```python
def position_size(self, df, vars):
    # Risk 1 ATR distance as position size multiplier
    atr = vars['atr']
    base_risk = 100  # USD risk per trade
    return base_risk / atr
```

---

## 7. Position Sizing Modes

The user selects position sizing at the API level:

| Mode | Description |
|------|-------------|
| `"fixed"` | Use `fixed_size * leverage` for every trade |
| `"percent_equity"` | Risk `risk_per_trade` fraction of equity per trade |
| `"strategy_defined"` | Use `position_size()` return value × leverage |

---

## 8. Leverage

Leverage is a multiplier applied to position size. Example:
- `fixed_size=1.0`, `leverage=10.0` → effective size = 10.0
- Leverage does NOT affect SL/TP levels, only PnL magnitude

---

## 9. Backtest Modes

| Mode | PnL Column | Description |
|------|-----------|-------------|
| `"capital"` | USD | PnL = (exit - entry) × size. Equity tracked in USD. |
| `"rrr"` | R-multiples | PnL = net_pnl / initial_risk. Equity still tracked in USD internally. |

Both modes always compute RRR (R-multiple) per trade.

---

## 10. Realistic Market Simulation

These features make backtests simulate real market conditions, preventing over-optimistic results.
All features are **off by default** (backward compatible). Enable via the API request.

### 10.1 Slippage

Slippage worsens your entry/exit prices, just like real order execution.

| Mode | `slippage_mode` | `slippage_value` | Effect |
|------|----------------|-----------------|--------|
| None | `"none"` | 0.0 | No slippage (default) |
| Fixed | `"fixed"` | e.g. `0.5` | Fixed amount added/subtracted from price |
| Percent | `"percent"` | e.g. `0.01` | Percentage of price |
| Random | `"random"` | e.g. `1.0` | Random uniform [0, value] per trade |

**Direction rules:**
- **Long entry**: price + slippage (buy at higher price = worse)
- **Short entry**: price - slippage (sell at lower price = worse)
- **SL exit**: slippage worsens further (market order)
- **TP exit**: NO slippage (limit order, fills at exact price)

### 10.2 Spread (Bid-Ask)

| Parameter | Value | Effect |
|-----------|-------|--------|
| `spread_value` | e.g. `0.20` | Full spread in price units |

**Direction rules:**
- **Long entry**: price + spread/2 (buy at ask)
- **Short entry**: price - spread/2 (sell at bid)
- **Long exit**: price - spread/2 (sell at bid)
- **Short exit**: price + spread/2 (buy at ask)

> **Tip for XAUUSD**: Typical spread is 0.15–0.30. Set `spread_value: 0.20`.

### 10.3 Next-Bar Entry

| Parameter | Value | Effect |
|-----------|-------|--------|
| `entry_on_next_bar` | `true` | Enter at next bar's **open** price |
| `entry_on_next_bar` | `false` | Enter at current bar's **close** price (default) |

> **IMPORTANT**: In live trading, you receive a signal at bar close and execute on the next bar's open.
> Using `entry_on_next_bar: true` makes backtests match live behavior exactly.

### 10.4 API Example (All Realism Features)

```json
{
  "dataset_id": "abc123",
  "strategy_name": "RSI 2",
  "mode": "capital",
  "initial_capital": 10000,
  "leverage": 10,
  "slippage_mode": "fixed",
  "slippage_value": 0.5,
  "spread_value": 0.20,
  "entry_on_next_bar": true
}
```

---

## 11. Trade Ledger Columns

Every trade record contains:

| Column | Description |
|--------|-------------|
| `entry_time` | Entry datetime |
| `direction` | `"long"` or `"short"` |
| `entry_price` | Price at entry (includes slippage + spread if enabled) |
| `exit_price` | Price at exit (includes slippage + spread if enabled) |
| `exit_time` | Exit datetime |
| `pnl` | PnL in USD or R (depends on mode) |
| `gross_pnl` | PnL before commission |
| `commission` | Total commission (entry + exit) |
| `r_multiple` | Risk-Reward ratio (always computed) |
| `sl` | Stop Loss price (null if none) |
| `tp` | Take Profit price (null if none) |
| `mae` | Max Adverse Excursion (worst drawdown during trade) |
| `mfe` | Max Favorable Excursion (best runup during trade) |
| `mae_price` | Price at MAE point |
| `mfe_price` | Price at MFE point |
| `mae_pnl` | MAE in PnL units |
| `mfe_pnl` | MFE in PnL units |
| `mae_r` | MAE in R-multiples |
| `mfe_r` | MFE in R-multiples |
| `duration` | Holding time in minutes |
| `exit_reason` | `"SL Hit"`, `"TP Hit"`, `"Exit"`, `"End of Data"` |
| `size` | Position size used |
| `initial_risk` | Dollar risk at entry |

---

## 12. Exit Reason (Status) Logic

| Status | Meaning |
|--------|---------|
| `SL Hit` | Strategy defined SL and the price hit it |
| `TP Hit` | Strategy defined TP and the price hit it |
| `Exit` | Strategy's exit signal closed the trade (not SL/TP) |
| `End of Data` | Trade was still open at dataset end, force-closed |

---

## 13. Common Mistakes to Avoid

1. **Hardcoding values** — Use `self.parameters.get()` for anything optimizable
2. **Not returning pd.Series** from signal methods — Always return boolean Series with same index as `df`
3. **Using loops in `define_variables`** — Use vectorized pandas operations
4. **Forgetting NaN handling** — Early bars will have NaN from rolling windows; use `.fillna()`
5. **Not implementing `risk_model`** — Without SL/TP, trades only close via exit signals or EOD
6. **Using wrong risk key names** — Use `stop_loss_dist`/`take_profit_dist` (distance) or `sl`/`tp` (absolute)
7. **Ignoring `exit_long_signal`/`exit_short_signal`** — If not overridden, fast engine only exits via SL/TP/EOD

---

## 14. Performance Metrics

The engine computes these metrics automatically:

| Metric | Description |
|--------|-------------|
| `total_trades` | Total number of trades |
| `win_rate` | Percentage of winning trades |
| `net_profit` | Total PnL |
| `profit_factor` | Gross Profit / Gross Loss |
| `max_drawdown` | Largest peak-to-trough decline |
| `max_drawdown_pct` | Max drawdown as percentage |
| `sharpe_ratio` | Risk-adjusted return (per-trade) |
| `sortino_ratio` | Downside risk-adjusted return |
| `sqn` | System Quality Number |
| `expectancy` | Average PnL per trade |
| `calmar_ratio` | Annualized return / max drawdown |
| `max_consecutive_wins` | Longest winning streak |
| `max_consecutive_losses` | Longest losing streak |
| `avg_mae` | Average MAE across all trades |
| `avg_mfe` | Average MFE across all trades |
| `var_95` | Value at Risk (95% confidence) |
| `trades_per_day` | Average trades per calendar day |

---

## 15. Complete Example Strategy

```python
from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MeanReversionStrategy(Strategy):
    """
    RSI Mean Reversion with dynamic parameters.
    """

    def define_variables(self, df):
        close = df['close']
        high = df['high']
        low = df['low']

        # Dynamic parameters
        rsi_period = int(self.parameters.get('rsi_period', 14))
        sma_period = int(self.parameters.get('sma_period', 200))

        # RSI
        delta = close.diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        ma_up = up.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
        ma_down = down.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
        rs = ma_up / ma_down.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)

        # SMA Filter
        sma = close.rolling(window=sma_period).mean()

        # ATR for risk
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        return {"rsi": rsi, "sma": sma, "atr": atr, "close": close}

    def entry_long(self, df, vars):
        oversold = float(self.parameters.get('rsi_oversold', 30))
        return (vars['rsi'] < oversold) & (vars['close'] > vars['sma'])

    def entry_short(self, df, vars):
        overbought = float(self.parameters.get('rsi_overbought', 70))
        return (vars['rsi'] > overbought) & (vars['close'] < vars['sma'])

    def exit(self, df, vars, trade):
        idx = trade['current_idx']
        rsi = vars['rsi'].iloc[idx]
        if trade['direction'] == 'long':
            return rsi >= 50
        return rsi <= 50

    def risk_model(self, df, vars):
        atr = vars['atr'].iloc[-1]
        if pd.isna(atr):
            atr = vars['close'].iloc[-1] * 0.01
        return {
            "stop_loss_dist": atr * 2.0,
            "take_profit_dist": atr * 3.0,
        }
```
