from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSI_Trend_Aligned_1M_v2(Strategy):
    """
    Author: MCP Client
    Description: RSI-based trend-aligned strategy with 1:1 RRR for 1M timeframe (Optimized).
    - Uses EMA 20/50 for trend alignment only (no price filter)
    - RSI 14 for entry signals (entering 30-40 zone in uptrend, entering 60-70 zone in downtrend)
    - ATR-based SL/TP with fixed 1:1 Reward:Risk ratio
    - Designed for 10+ high-quality trades/day on XAUUSD
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
        
        # RSI shift for detecting crossovers
        rsi_14_prev = rsi_14.shift(1)
        
        return {
            'rsi_14': rsi_14,
            'rsi_14_prev': rsi_14_prev,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'atr_14': atr_14
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Long entry: Uptrend + RSI entering oversold zone (crossing above 30)."""
        # Trend alignment: EMA 20 > EMA 50 (uptrend)
        uptrend = vars['ema_20'] > vars['ema_50']
        
        # RSI signal: crossing above 30 (coming from oversold to neutral)
        rsi_cross_up = (vars['rsi_14_prev'] < 30) & (vars['rsi_14'] >= 30)
        
        # Alternative: RSI was below 40 and now turning up (less strict)
        rsi_bullish = (vars['rsi_14_prev'] < 40) & (vars['rsi_14'] > vars['rsi_14_prev'])
        
        # More aggressive entry for higher frequency:
        # Use either cross above 30 OR bullish turn up below 40
        rsi_entry = rsi_cross_up | rsi_bullish
        
        entry = uptrend & rsi_entry
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Short entry: Downtrend + RSI entering overbought zone (crossing below 70)."""
        # Trend alignment: EMA 20 < EMA 50 (downtrend)
        downtrend = vars['ema_20'] < vars['ema_50']
        
        # RSI signal: crossing below 70 (coming from overbought to neutral)
        rsi_cross_down = (vars['rsi_14_prev'] > 70) & (vars['rsi_14'] <= 70)
        
        # Alternative: RSI was above 60 and now turning down (less strict)
        rsi_bearish = (vars['rsi_14_prev'] > 60) & (vars['rsi_14'] < vars['rsi_14_prev'])
        
        # More aggressive entry for higher frequency:
        # Use either cross below 70 OR bearish turn down above 60
        rsi_entry = rsi_cross_down | rsi_bearish
        
        entry = downtrend & rsi_entry
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """ATR-based SL/TP with fixed 1:1 RRR."""
        
        # SL distance: 1.5x ATR (adjustable via parameters)
        atr_multiplier = self.parameters.get('atr_sl_multiplier', 1.5)
        sl_distance = vars['atr_14'] * atr_multiplier
        
        # TP distance: 1.5x ATR (1:1 RRR - same as SL)
        tp_distance = sl_distance
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit long if RSI reaches overbought (>65)."""
        exit = vars['rsi_14'] > 65
        return exit.fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit short if RSI reaches oversold (<35)."""
        exit = vars['rsi_14'] < 35
        return exit.fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Dynamic exit: EMA trend reversal (only if trend changes)."""
        idx = trade['current_idx']
        if idx < 0 or idx >= len(df):
            return False
        
        if trade['direction'] == 'long':
            # Exit long if EMA crosses bearish (20 < 50)
            if vars['ema_20'][idx] < vars['ema_50'][idx]:
                return True
        elif trade['direction'] == 'short':
            # Exit short if EMA crosses bullish (20 > 50)
            if vars['ema_20'][idx] > vars['ema_50'][idx]:
                return True
        
        return False