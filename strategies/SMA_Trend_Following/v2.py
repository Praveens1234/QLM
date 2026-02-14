from backend.core.strategy import Strategy

import pandas as pd
import numpy as np


class SMATrendFollowingStrategy(Strategy):
    """
    SMA Trend Following Strategy for XAUUSD 5M - OPTIMIZED VERSION.

    Optimized Parameters:
    - SMA Fast: 10
    - SMA Slow: 50
    - SL: 1.0x ATR
    - TP: 1.5x ATR
    - Risk: 1% per trade

    Improvements:
    - Faster SMAs reduce lag on 5M timeframe
    - Tighter stops prevent large drawdowns
    - Lower risk per trade preserves capital
    """

    def define_variables(self, df: pd.DataFrame) -> dict:
        """Calculate SMA and ATR indicators."""
        close = df['close']
        high = df['high']
        low = df['low']

        # Optimized SMA periods for 5M timeframe
        sma_fast = close.rolling(window=10).mean()
        sma_slow = close.rolling(window=50).mean()

        # ATR14 calculation
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean()

        return {
            "sma_fast": sma_fast,
            "sma_slow": sma_slow,
            "atr_14": atr_14,
            "close": close
        }

    def entry_long(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        """Long entry: Fast SMA crosses above Slow SMA."""
        sma_fast = vars['sma_fast']
        sma_slow = vars['sma_slow']
        prev_fast = sma_fast.shift(1)
        prev_slow = sma_slow.shift(1)

        golden_cross = (prev_fast <= prev_slow) & (sma_fast > sma_slow)
        return golden_cross

    def entry_short(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        """Short entry: Fast SMA crosses below Slow SMA."""
        sma_fast = vars['sma_fast']
        sma_slow = vars['sma_slow']
        prev_fast = sma_fast.shift(1)
        prev_slow = sma_slow.shift(1)

        death_cross = (prev_fast >= prev_slow) & (sma_fast < sma_slow)
        return death_cross

    def risk_model(self, df: pd.DataFrame, vars: dict) -> dict:
        """Optimized risk management: 1% risk, 1.0x SL, 1.5x TP."""
        atr = vars['atr_14'].iloc[-1]
        current_price = vars['close'].iloc[-1]

        if pd.isna(atr):
            atr = current_price * 0.005  # Fallback 0.5%

        return {
            "stop_loss_dist": atr * 1.0,
            "take_profit_dist": atr * 1.5,
            "sizing_risk_per_trade": 0.01
        }

    def exit(self, df: pd.DataFrame, vars: dict, trade: dict) -> bool:
        """Exit on reversal crossover."""
        current_idx = trade['current_idx']
        current_close = vars['close'].iloc[current_idx]
        sma_fast = vars['sma_fast'].iloc[current_idx]
        direction = trade['direction']

        if direction == 'long':
            if current_close < sma_fast:
                return True
        else:
            if current_close > sma_fast:
                return True

        return False