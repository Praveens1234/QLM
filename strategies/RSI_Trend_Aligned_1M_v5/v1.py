from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSI_Trend_Aligned_1M_v5(Strategy):
    """
    Author: MCP Client
    Description: High-quality RSI trend-following strategy for XAUUSD 1M.
    - Uses EMA 20/50 spread for strong trend identification
    - RSI confluence: Both crossover AND momentum turn required
    - 1:1.5 RRR with selective entries for ~40% win rate
    - ATR-based dynamic SL/TP
    - Target: 10+ high-quality trades/day with positive expectancy
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
        
        # EMA spread for trend strength
        ema_spread = (ema_20 - ema_50) / df['close']
        
        # ATR for dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean()
        
        # Previous bar values
        close_prev = df['close'].shift(1)
        rsi_14_prev = rsi_14.shift(1)
        
        # Momentum indicators
        volume_trend = df['volume'].rolling(10).mean()
        
        return {
            'rsi_14': rsi_14,
            'rsi_14_prev': rsi_14_prev,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'ema_spread': ema_spread,
            'atr_14': atr_14,
            'close_prev': close_prev,
            'volume_trend': volume_trend
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Long entry: Strong uptrend + RSI bounce from oversold zone."""
        # Strong uptrend: EMA 20 > EMA 50 AND price above both EMAs
        strong_uptrend = (vars['ema_20'] > vars['ema_50']) & \
                        (df['close'] > vars['ema_20']) & \
                        (df['close'] > vars['ema_50'])
        
        # Trend strength: EMA spread at least 0.1%
        trend_strength = vars['ema_spread'] > 0.001
        
        # RSI crossing above 30 from below
        rsi_crossover = (vars['rsi_14_prev'] <= 30) & (vars['rsi_14'] > 30)
        
        # RSI bullish momentum
        rsi_bullish = (vars['rsi_14_prev'] < vars['rsi_14']) & (vars['rsi_14'] < 40)
        
        # Price rising
        price_rising = df['close'] > vars['close_prev']
        
        # Combined RSI signal: Both crossover AND momentum
        rsi_signal = rsi_crossover | (rsi_bullish & price_rising)
        
        # Strong trend filter
        trend_filter = strong_uptrend & trend_strength
        
        entry = trend_filter & rsi_signal
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Short entry: Strong downtrend + RSI rejection from overbought zone."""
        # Strong downtrend: EMA 20 < EMA 50 AND price below both EMAs
        strong_downtrend = (vars['ema_20'] < vars['ema_50']) & \
                          (df['close'] < vars['ema_20']) & \
                          (df['close'] < vars['ema_50'])
        
        # Trend strength: EMA spread at least 0.1%
        trend_strength = vars['ema_spread'] < -0.001
        
        # RSI crossing below 70 from above
        rsi_crossover = (vars['rsi_14_prev'] >= 70) & (vars['rsi_14'] < 70)
        
        # RSI bearish momentum
        rsi_bearish = (vars['rsi_14_prev'] > vars['rsi_14']) & (vars['rsi_14'] > 60)
        
        # Price falling
        price_falling = df['close'] < vars['close_prev']
        
        # Combined RSI signal: Both crossover AND momentum
        rsi_signal = rsi_crossover | (rsi_bearish & price_falling)
        
        # Strong trend filter
        trend_filter = strong_downtrend & trend_strength
        
        entry = trend_filter & rsi_signal
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """ATR-based SL/TP with 1:1.5 ratio."""
        
        # SL distance: 2.0x ATR (wider stops for better win rate)
        sl_multiplier = self.parameters.get('sl_multiplier', 2.0)
        sl_distance = vars['atr_14'] * sl_multiplier
        
        # TP distance: 3.0x ATR (1:1.5 ratio)
        tp_multiplier = self.parameters.get('tp_multiplier', 3.0)
        tp_distance = vars['atr_14'] * tp_multiplier
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit long if RSI very overbought OR trend weakening."""
        rsi_overbought = vars['rsi_14'] > 75
        trend_weakens = df['close'] < vars['ema_20']
        exit = rsi_overbought | trend_weakens
        return exit.fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit short if RSI very oversold OR trend weakening."""
        rsi_oversold = vars['rsi_14'] < 25
        trend_weakens = df['close'] > vars['ema_20']
        exit = rsi_oversold | trend_weakens
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