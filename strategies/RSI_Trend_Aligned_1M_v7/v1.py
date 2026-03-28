from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSI_Trend_Aligned_1M_v7(Strategy):
    """
    Author: MCP Client
    Description: RSI trend-following strategy - High RR breakthrough version.
    - EMA 20/50 for trend filtering
    - RSI 14 extreme entries ONLY (<25 for long >75 for short) - highest quality
    - 1:3 RRR (3R reward) to compensate for slippage/spread on XAUUSD
    - Wider ATR multiplier for SL (2x ATR) to avoid premature stops
    - Exponential exits to capture larger moves
    - Target: 8-15 trades/day with positive expectancy
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        
        # RSI 14 calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs))
        
        # EMAs for trend filtering
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR for dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean()
        
        # Previous values
        rsi_14_prev = rsi_14.shift(1)
        close_prev = df['close'].shift(1)
        
        return {
            'rsi_14': rsi_14,
            'rsi_14_prev': rsi_14_prev,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'atr_14': atr_14,
            'close_prev': close_prev
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Long entry: Uptrend + RSI extreme oversold bounce."""
        # Trend filter: Uptrend
        uptrend = vars['ema_20'] > vars['ema_50']
        
        # RSI signal: Was deep oversold (<25) and turning up
        rsi_oversold = vars['rsi_14_prev'] < 25
        rsi_turning = vars['rsi_14'] > vars['rsi_14_prev']
        price_rising = df['close'] > vars['close_prev']
        
        entry = uptrend & rsi_oversold & rsi_turning & price_rising
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Short entry: Downtrend + RSI extreme overbought rejection."""
        # Trend filter: Downtrend
        downtrend = vars['ema_20'] < vars['ema_50']
        
        # RSI signal: Was deep overbought (>75) and turning down
        rsi_overbought = vars['rsi_14_prev'] > 75
        rsi_turning = vars['rsi_14'] < vars['rsi_14_prev']
        price_falling = df['close'] < vars['close_prev']
        
        entry = downtrend & rsi_overbought & rsi_turning & price_falling
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """ATR-based SL/TP with 1:3 ratio."""
        
        # SL distance: 2.0x ATR (wider stop to avoid noise)
        sl_distance = vars['atr_14'] * 2.0
        
        # TP distance: 6.0x ATR (1:3 ratio for big winners)
        tp_distance = vars['atr_14'] * 6.0
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit long only on trend reversal (no RSI exit for longer holds)."""
        exit = vars['ema_20'] < vars['ema_50']
        return exit.fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit short only on trend reversal (no RSI exit for longer holds)."""
        exit = vars['ema_20'] > vars['ema_50']
        return exit.fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Dynamic exit: Only EMA crossover."""
        idx = trade['current_idx']
        if idx < 0 or idx >= len(df):
            return False
        
        if trade['direction'] == 'long':
            if vars['ema_20'][idx] < vars['ema_50'][idx]:
                return True
        elif trade['direction'] == 'short':
            if vars['ema_20'][idx] > vars['ema_50'][idx]:
                return True
        
        return False