from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSIStrategy(Strategy):
    """
    Refined RSI Mean Reversion Strategy (Trend-Following Pullbacks).

    Philosophy:
    1. Trend Filter: Only trade in the direction of the dominant trend (SMA 200).
    2. Entry: Buy deep pullbacks (RSI < 30) in uptrends; Short overextensions (RSI > 70) in downtrends.
    3. Exit: Dynamic. Primary = Mean Reversion (RSI 50). Secondary = Volatility Stop (ATR).
    4. Safety: Time-based exit to prevent dead capital.

    Optimized for: High win rate, lower frequency, protection against regime change.
    """

    # Configuration for Optimization
    params = {
        'rsi_period': 14,
        'rsi_lower': 30,
        'rsi_upper': 70,
        'rsi_mean': 50,
        'trend_sma': 200,
        'atr_period': 14,
        'risk_reward': 1.5,  # SL distance multiplier
        'max_holding_bars': 10 # Time stop
    }

    def define_variables(self, df: pd.DataFrame) -> dict:
        """
        Pre-calculates all vector indicators. 
        Uses Wilder's Smoothing for RSI (Standard Industry Practice).
        """
        # 1. Inputs
        close = df['close']
        high = df['high']
        low = df['low']
        
        # 2. RSI (Wilder's Smoothing)
        delta = close.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        
        # Alpha = 1/N is standard for Wilder's
        alpha = 1.0 / self.params['rsi_period']
        ma_up = up.ewm(alpha=alpha, adjust=False).mean()
        ma_down = down.ewm(alpha=alpha, adjust=False).mean()
        
        rs = ma_up / ma_down.replace(0, np.nan) # Avoid div/0
        rsi = 100 - (100 / (1 + rs))
        
        # 3. Trend Filter (SMA)
        trend_sma = close.rolling(window=self.params['trend_sma']).mean()
        
        # 4. Volatility (ATR) for Stop Loss
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.params['atr_period']).mean()

        return {
            "rsi": rsi.fillna(50),
            "trend_sma": trend_sma,
            "atr": atr.fillna(0),
            "close": close,
            "high": high,
            "low": low
        }

    def entry_long(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        # Condition 1: Long-term Uptrend (Price > SMA200)
        is_uptrend = vars['close'] > vars['trend_sma']
        
        # Condition 2: RSI Crossover < 30 (Oversold)
        # We use crossover to trigger ONCE per dip, not continuously
        rsi_below = vars['rsi'] < self.params['rsi_lower']
        rsi_prev_above = vars['rsi'].shift(1) >= self.params['rsi_lower']
        trigger = rsi_below & rsi_prev_above
        
        return trigger & is_uptrend

    def entry_short(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        # Condition 1: Long-term Downtrend (Price < SMA200)
        is_downtrend = vars['close'] < vars['trend_sma']
        
        # Condition 2: RSI Crossover > 70 (Overbought)
        rsi_above = vars['rsi'] > self.params['rsi_upper']
        rsi_prev_below = vars['rsi'].shift(1) <= self.params['rsi_upper']
        trigger = rsi_above & rsi_prev_below
        
        return trigger & is_downtrend

    def exit(self, df: pd.DataFrame, vars: dict, trade: dict) -> bool:
        """
        Multi-stage exit logic:
        1. Structural Stop Loss (ATR based) - Protective
        2. Mean Reversion (RSI 50) - Profit Taking
        3. Time Stop - Efficiency
        """
        curr_idx = trade['current_idx']
        entry_idx = trade['entry_idx']
        
        # Current Market Data
        current_rsi = vars['rsi'].iloc[curr_idx]
        current_close = vars['close'].iloc[curr_idx]
        bars_held = curr_idx - entry_idx

        # 1. Time Stop (Dead Money Check)
        if bars_held >= self.params['max_holding_bars']:
            return True

        # 2. Logic per direction
        if trade['direction'] == 'long':
            # Stop Loss (Hard exit)
            if current_close <= trade['stop_loss_price']:
                return True
            # Mean Reversion (Target)
            if current_rsi >= self.params['rsi_mean']:
                return True
                
        elif trade['direction'] == 'short':
            # Stop Loss (Hard exit)
            if current_close >= trade['stop_loss_price']:
                return True
            # Mean Reversion (Target)
            if current_rsi <= self.params['rsi_mean']:
                return True

        return False

    def risk_model(self, df: pd.DataFrame, vars: dict) -> dict:
        """
        Calculates dynamic risk parameters at the moment of entry.
        These values are attached to the 'trade' object.
        """
        # Get data at current bar (entry bar)
        # Note: In most backtesters, this is called BEFORE entry execution
        current_atr = vars['atr'].iloc[-1]
        current_close = vars['close'].iloc[-1]
        
        # Dynamic Stop Loss Distance
        risk_dist = current_atr * self.params['risk_reward']
        
        # Return dict to be merged into trade object
        return {
            "atr_at_entry": current_atr,
            "stop_loss_dist": risk_dist,
            # We calculate exact prices here for the engine to use
            "long_stop_price": current_close - risk_dist,
            "short_stop_price": current_close + risk_dist
        }