from backend.core.strategy import Strategy

import pandas as pd
import numpy as np


class SMATrendFollowingStrategy(Strategy):
    """
    SMA Trend Following Strategy for XAUUSD 5M.

    Components:
    1. Trend: SMA50/SMA200 crossover for direction
    2. Risk: ATR-based stop loss and take profit
    3. Position Sizing: 2% risk per trade

    Market context: Low volatility (0.04%), bullish trend bias
    """

    def define_variables(self, df: pd.DataFrame) -> dict:
        """Calculate SMA and ATR indicators."""
        close = df['close']
        high = df['high']
        low = df['low']

        # SMA calculations (vectorized)
        sma_50 = close.rolling(window=50).mean()
        sma_200 = close.rolling(window=200).mean()

        # ATR14 calculation (True Range method)
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean()

        return {
            "sma_50": sma_50,
            "sma_200": sma_200,
            "atr_14": atr_14,
            "close": close
        }

    def entry_long(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        """
        Long entry: Golden Cross (SMA50 crosses above SMA200)
        Only trade with the trend (price should be above SMA200 for confirmation)
        """
        sma_50 = vars['sma_50']
        sma_200 = vars['sma_200']
        prev_sma_50 = sma_50.shift(1)
        prev_sma_200 = sma_200.shift(1)
        close = vars['close']

        # Golden Cross + Price above SMA200 confirmation
        golden_cross = (prev_sma_50 <= prev_sma_200) & (sma_50 > sma_200)
        trend_confirmation = close > sma_200

        return golden_cross & trend_confirmation

    def entry_short(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        """
        Short entry: Death Cross (SMA50 crosses below SMA200)
        Only trade with the trend (price should be below SMA200 for confirmation)
        """
        sma_50 = vars['sma_50']
        sma_200 = vars['sma_200']
        prev_sma_50 = sma_50.shift(1)
        prev_sma_200 = sma_200.shift(1)
        close = vars['close']

        # Death Cross + Price below SMA200 confirmation
        death_cross = (prev_sma_50 >= prev_sma_200) & (sma_50 < sma_200)
        trend_confirmation = close < sma_200

        return death_cross & trend_confirmation

    def risk_model(self, df: pd.DataFrame, vars: dict) -> dict:
        """
        ATR-based risk management:
        - Stop Loss: 2x ATR
        - Take Profit: 3x ATR (1.5R reward)
        - Risk per trade: 2%
        """
        atr = vars['atr_14'].iloc[-1]
        current_price = vars['close'].iloc[-1]

        # Fallback if ATR unavailable
        if pd.isna(atr):
            atr = current_price * 0.01

        return {
            "stop_loss_dist": atr * 2.0,
            "take_profit_dist": atr * 3.0,
            "sizing_risk_per_trade": 0.02
        }

    def exit(self, df: pd.DataFrame, vars: dict, trade: dict) -> bool:
        """
        Exit conditions:
        1. Opposite SMA crossover (trend reversal)
        2. Hit stop loss or take profit (handled by engine)
        """
        current_idx = trade['current_idx']
        current_close = vars['close'].iloc[current_idx]
        sma_50 = vars['sma_50'].iloc[current_idx]
        direction = trade['direction']

        # Exit on SMA crossover reversal
        if direction == 'long':
            # Exit long when price crosses below SMA50
            if current_close < sma_50:
                return True
        else:
            # Exit short when price crosses above SMA50
            if current_close > sma_50:
                return True

        return False