import pandas as pd
import numpy as np
from backend.core.strategy import Strategy
from typing import Dict, Any

class SmaCross(Strategy):
    """
    Simple Moving Average Crossover Strategy.
    """

    def define_variables(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        # Calculate SMAs
        sma_fast = df['close'].rolling(window=20).mean()
        sma_slow = df['close'].rolling(window=50).mean()

        # Calculate ATR for risk model
        atr = (df['high'] - df['low']).rolling(window=14).mean()

        return {
            "sma_fast": sma_fast,
            "sma_slow": sma_slow,
            "atr": atr
        }

    def entry_long(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        # Long when fast crosses above slow
        sma_fast = vars['sma_fast']
        sma_slow = vars['sma_slow']

        # Current Fast > Slow AND Previous Fast <= Slow
        crossover = (sma_fast > sma_slow) & (sma_fast.shift(1) <= sma_slow.shift(1))
        return crossover

    def entry_short(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        # Short when fast crosses below slow
        sma_fast = vars['sma_fast']
        sma_slow = vars['sma_slow']

        crossunder = (sma_fast < sma_slow) & (sma_fast.shift(1) >= sma_slow.shift(1))
        return crossunder

    def risk_model(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        atr = vars['atr']
        close = df['close']

        # Define SL/TP distances
        sl_dist = atr * 2.0
        tp_dist = atr * 3.0

        # Get signals to determine direction
        longs = self.entry_long(df, vars)
        shorts = self.entry_short(df, vars)

        sl = pd.Series(np.nan, index=df.index)
        tp = pd.Series(np.nan, index=df.index)

        # Assign SL/TP based on signal direction
        # For Longs: SL below, TP above
        sl[longs] = close[longs] - sl_dist[longs]
        tp[longs] = close[longs] + tp_dist[longs]

        # For Shorts: SL above, TP below
        sl[shorts] = close[shorts] + sl_dist[shorts]
        tp[shorts] = close[shorts] - tp_dist[shorts]

        return {"sl": sl, "tp": tp}

    def position_size(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        # Risk 1% of account ($10,000) = $100 per trade
        risk_amount = 100.0
        atr = vars['atr'].bfill()

        # Stop Loss distance is 2 * ATR
        sl_distance = 2 * atr

        # Prevent division by zero
        sl_distance = sl_distance.replace(0, 1.0)

        # Size = Risk Amount / SL Distance
        size = risk_amount / sl_distance

        return size.fillna(1.0)

    def exit(self, df: pd.DataFrame, vars: Dict[str, pd.Series], trade: Dict[str, Any]) -> bool:
        # Exit if trend reverses (Fast crosses back)
        current_idx = trade.get('current_idx', 0)
        if current_idx >= len(df):
            return True

        sma_fast = vars['sma_fast'].iloc[current_idx]
        sma_slow = vars['sma_slow'].iloc[current_idx]

        if trade['direction'] == 'long':
            # Exit Long if Fast < Slow
            return sma_fast < sma_slow
        else:
            # Exit Short if Fast > Slow
            return sma_fast > sma_slow
