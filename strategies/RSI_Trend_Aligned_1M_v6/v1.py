from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSI_Trend_Aligned_1M_v6(Strategy):
    """
    Author: MCP Client
    Description: RSI trend-following strategy - Final optimized version for XAUUSD 1M.
    - EMA 20/50 for trend alignment (simple, effective)
    - RSI 14 with flexible entry conditions (cross + momentum)
    - 1:2 RRR (reward is 2x risk) for positive expectancy with ~35-40% win rate
    - ATR 14 for dynamic SL/TP - tight SL (1.2x ATR), wide TP (2.4x ATR)
    - Clean exits: RSI reversal OR EMA trend change
    - Target: 10+ trades/day with positive expectancy
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        
        # RSI 14 calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs))
        
        # EMAs for trend alignment
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR for dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean()
        
        # Previous RSI for crossover detection
        rsi_14_prev = rsi_14.shift(1)
        
        return {
            'rsi_14': rsi_14,
            'rsi_14_prev': rsi_14_prev,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'atr_14': atr_14
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Long entry: Uptrend + RSI bouncing up."""
        # Trend alignment: EMA 20 > EMA 50
        uptrend = vars['ema_20'] > vars['ema_50']
        
        # RSI crossover above 30
        rsi_cross_up = (vars['rsi_14_prev'] < 30) & (vars['rsi_14'] >= 30)
        
        # RSI bullish momentum (below 40 and rising)
        rsi_bullish = (vars['rsi_14_prev'] < 40) & \
                      (vars['rsi_14'] > vars['rsi_14_prev']) & \
                      (vars['rsi_14'] < 50)
        
        # Combine signals
        rsi_signal = rsi_cross_up | rsi_bullish
        
        entry = uptrend & rsi_signal
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Short entry: Downtrend + RSI rejecting down."""
        # Trend alignment: EMA 20 < EMA 50
        downtrend = vars['ema_20'] < vars['ema_50']
        
        # RSI crossover below 70
        rsi_cross_down = (vars['rsi_14_prev'] > 70) & (vars['rsi_14'] <= 70)
        
        # RSI bearish momentum (above 60 and falling)
        rsi_bearish = (vars['rsi_14_prev'] > 60) & \
                      (vars['rsi_14'] < vars['rsi_14_prev']) & \
                      (vars['rsi_14'] > 50)
        
        # Combine signals
        rsi_signal = rsi_cross_down | rsi_bearish
        
        entry = downtrend & rsi_signal
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """ATR-based SL/TP with 1:2 ratio (tight SL, wide TP)."""
        
        # SL distance: 1.2x ATR (tight but not too tight)
        sl_multiplier = self.parameters.get('sl_multiplier', 1.2)
        sl_distance = vars['atr_14'] * sl_multiplier
        
        # TP distance: 2.4x ATR (1:2 ratio)
        tp_multiplier = self.parameters.get('tp_multiplier', 2.4)
        tp_distance = vars['atr_14'] * tp_multiplier
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit long if RSI overbought (68) OR trend ends."""
        rsi_exit = vars['rsi_14'] > 68
        trend_exit = vars['ema_20'] < vars['ema_50']
        exit = rsi_exit | trend_exit
        return exit.fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit short if RSI oversold (32) OR trend ends."""
        rsi_exit = vars['rsi_14'] < 32
        trend_exit = vars['ema_20'] > vars['ema_50']
        exit = rsi_exit | trend_exit
        return exit.fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Dynamic exit: EMA crossover reversal."""
        idx = trade['current_idx']
        if idx < 0 or idx >= len(df):
            return False
        
        if trade['direction'] == 'long':
            # Exit long on bearish EMA crossover
            if vars['ema_20'][idx] < vars['ema_50'][idx]:
                return True
        elif trade['direction'] == 'short':
            # Exit short on bullish EMA crossover
            if vars['ema_20'][idx] > vars['ema_50'][idx]:
                return True
        
        return False