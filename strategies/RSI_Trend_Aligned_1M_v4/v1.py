from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSI_Trend_Aligned_1M_v4(Strategy):
    """
    Author: MCP Client
    Description: RSI trend-following strategy optimized for XAUUSD 1M with 1:2 RRR.
    - Classic trend-following: EMA 20 > EMA 50 for long, < for short
    - RSI used for entry timing: Buy dips in uptrend, sell rallies in downtrend
    - 1:2 risk-reward ratio (reward double the risk) to compensate for ~35-40% win rate
    - ATR-based dynamic SL/TP
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
        
        # EMAs for trend identification
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR for dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean()
        
        # Previous RSI for detecting reversals
        rsi_14_prev = rsi_14.shift(1)
        
        return {
            'rsi_14': rsi_14,
            'rsi_14_prev': rsi_14_prev,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'atr_14': atr_14
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Long entry: Buy the dip in uptrend when RSI bounces from oversold."""
        # Trend filter: Uptrend
        uptrend = vars['ema_20'] > vars['ema_50']
        
        # Entry zone: RSI was oversold and turning up
        # Option 1: Cross above 30 (most conservative)
        rsi_cross_30 = (vars['rsi_14_prev'] <= 30) & (vars['rsi_14'] > 30)
        
        # Option 2: Was below 35, now turning up (more aggressive)
        rsi_bounce = (vars['rsi_14_prev'] < 35) & \
                    (vars['rsi_14'] > vars['rsi_14_prev']) & \
                    (vars['rsi_14'] < 45)
        
        rsi_signal = rsi_cross_30 | rsi_bounce
        
        entry = uptrend & rsi_signal
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Short entry: Sell the rally in downtrend when RSI reverses from overbought."""
        # Trend filter: Downtrend
        downtrend = vars['ema_20'] < vars['ema_50']
        
        # Entry zone: RSI was overbought and turning down
        # Option 1: Cross below 70 (most conservative)
        rsi_cross_70 = (vars['rsi_14_prev'] >= 70) & (vars['rsi_14'] < 70)
        
        # Option 2: Was above 65, now turning down (more aggressive)
        rsi_reject = (vars['rsi_14_prev'] > 65) & \
                    (vars['rsi_14'] < vars['rsi_14_prev']) & \
                    (vars['rsi_14'] > 55)
        
        rsi_signal = rsi_cross_70 | rsi_reject
        
        entry = downtrend & rsi_signal
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """ATR-based SL/TP with 1:2 ratio (2R reward)."""
        
        # SL distance: 1.5x ATR
        sl_multiplier = self.parameters.get('sl_multiplier', 1.5)
        sl_distance = vars['atr_14'] * sl_multiplier
        
        # TP distance: 3x ATR (1:2 ratio)
        tp_multiplier = self.parameters.get('tp_multiplier', 3.0)
        tp_distance = vars['atr_14'] * tp_multiplier
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit long if RSI becomes very overbought (>72) OR trend reverses."""
        rsi_exit = vars['rsi_14'] > 72
        trend_exit = vars['ema_20'] < vars['ema_50']
        exit = rsi_exit | trend_exit
        return exit.fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit short if RSI becomes very oversold (<28) OR trend reverses."""
        rsi_exit = vars['rsi_14'] < 28
        trend_exit = vars['ema_20'] > vars['ema_50']
        exit = rsi_exit | trend_exit
        return exit.fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Dynamic exit: Trailing stop based on EMA 20."""
        idx = trade['current_idx']
        if idx < 0 or idx >= len(df):
            return False
        
        if trade['direction'] == 'long':
            # Exit long if price breaks below EMA 20
            if df.loc[idx, 'close'] < vars['ema_20'][idx]:
                return True
        elif trade['direction'] == 'short':
            # Exit short if price breaks above EMA 20
            if df.loc[idx, 'close'] > vars['ema_20'][idx]:
                return True
        
        return False