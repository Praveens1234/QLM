from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSITrendAligned1M_v3_Inverted_11RRR(Strategy):
    """
    Author: MCP Client
    Description: INVERTED version of RSITrendAligned1M_v3.
                 
                 Inversion Logic:
                 - Original Buy becomes Inverted Sell
                 - Original Sell becomes Inverted Buy
                 - Fixed RRR 1:1 (SL and TP at same distance)
                 
                 Original Strategy: Aggressive RSI trend-aligned
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        # RSI 9 (faster for 1M)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=9, min_periods=9).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=9, min_periods=9).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # EMA 34 for trend
        ema_34 = df['close'].ewm(span=34, adjust=False).mean()
        
        # ATR 7 for SL/TP distance
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=7, min_periods=7).mean()
        
        # RSI shift for momentum
        rsi_prev = rsi.shift(1)
        
        # Bullish/Bearish candles
        is_bullish = df['close'] > df['open']
        is_bearish = df['close'] < df['open']
        
        # Body size filter
        body_size = 2 * abs(df['close'] - df['open']) / (df['high'] - df['low'] + 0.0001)
        has_body = body_size > 0.3
        
        # Trend alignment
        uptrend = df['close'] > ema_34
        downtrend = df['close'] < ema_34
        
        return {
            'rsi': rsi,
            'rsi_prev': rsi_prev,
            'ema_34': ema_34,
            'atr': atr,
            'is_bullish': is_bullish,
            'is_bearish': is_bearish,
            'has_body': has_body,
            'uptrend': uptrend,
            'downtrend': downtrend,
            'rsi_oversold': rsi < 30,
            'rsi_overbought': rsi > 70,
            'rsi_neutral_oversold': (rsi >= 30) & (rsi < 50),
            'rsi_neutral_overbought': (rsi > 50) & (rsi <= 70),
            'rsi_rising': rsi > rsi_prev,
            'rsi_falling': rsi < rsi_prev
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        INVERTED Long Entry:
        - Original was SHORT, now we go LONG
        - Where original would signal short, we enter long
        """
        # Original overbought_reversal (was for short entry) -> NOW WE GO LONG
        original_overbought_short = (vars['downtrend']) & \
                                   (vars['rsi_overbought']) & \
                                   (vars['rsi_falling']) & \
                                   (vars['is_bearish']) & \
                                   (vars['has_body'])
        
        # Original rally_continuation (was for short entry) -> NOW WE GO LONG
        original_rally_short = (vars['downtrend']) & \
                             (vars['rsi_neutral_overbought']) & \
                             (vars['rsi_falling']) & \
                             (vars['is_bearish']) & \
                             (vars['has_body'])
        
        # INVERTED: Go long where original would go short
        signal = original_overbought_short | original_rally_short
        
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        INVERTED Short Entry:
        - Original was LONG, now we go SHORT
        - Where original would signal long, we enter short
        """
        # Original oversold_reversal (was for long entry) -> NOW WE GO SHORT
        original_oversold_long = (vars['uptrend']) & \
                                (vars['rsi_oversold']) & \
                                (vars['rsi_rising']) & \
                                (vars['is_bullish']) & \
                                (vars['has_body'])
        
        # Original pullback_continuation (was for long entry) -> NOW WE GO SHORT
        original_pullback_long = (vars['uptrend']) & \
                               (vars['rsi_neutral_oversold']) & \
                               (vars['rsi_rising']) & \
                               (vars['is_bullish']) & \
                               (vars['has_body'])
        
        # INVERTED: Go short where original would go long
        signal = original_oversold_long | original_pullback_long
        
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        FIXED 1:1 RRR - SL and TP at same distance.
        
        Both SL and TP = 2.5x ATR (midpoint between original SL and TP)
        """
        distance = vars['atr'] * 2.5
        
        sl = df['close'] - distance
        tp = df['close'] + distance
        
        return {
            'sl': sl,
            'tp': tp
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        INVERTED Exit Logic:
        - Original: Long exits below EMA 34 or RSI > 80
        - Inverted Long: Exits above EMA 34 or RSI < 20
        """
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_34'].iloc[idx]
        current_rsi = vars['rsi'].iloc[idx]
        
        if trade['direction'] == 'long':
            # INVERTED: Exit long if close above EMA or RSI very low (opposite of original)
            return (current_close > current_ema) or (current_rsi < 20)
        elif trade['direction'] == 'short':
            # INVERTED: Exit short if close below EMA or RSI very high (opposite of original)
            return (current_close < current_ema) or (current_rsi > 80)
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for long positions - INVERTED."""
        close_above_ema = df['close'] > vars['ema_34']
        rsi_exit_long = vars['rsi'] < 20
        return (close_above_ema | rsi_exit_long).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for short positions - INVERTED."""
        close_below_ema = df['close'] < vars['ema_34']
        rsi_exit_short = vars['rsi'] > 80
        return (close_below_ema | rsi_exit_short).fillna(False)
