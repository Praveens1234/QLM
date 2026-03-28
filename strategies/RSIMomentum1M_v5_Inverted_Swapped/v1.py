from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSIMomentum1M_v5_Inverted_Swapped(Strategy):
    """
    Author: MCP Client
    Description: INVERTED version of RSIMomentum1M_v5 with SWAPPED distances.
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        rsi_prev = rsi.shift(1)
        rsi_prev2 = rsi.shift(2)
        
        ema_21 = df['close'].ewm(span=21, adjust=False).mean()
        ema_5 = df['close'].ewm(span=5, adjust=False).mean()
        
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=10, min_periods=10).mean()
        
        uptrend = df['close'] > ema_21
        uptrend_strength = (df['close'] - ema_21) / df['close']
        strong_uptrend = uptrend_strength > 0.0003
        
        downtrend = df['close'] < ema_21
        downtrend_strength = (ema_21 - df['close']) / df['close']
        strong_downtrend = downtrend_strength > 0.0003
        
        price_above_ema5 = df['close'] > ema_5
        price_below_ema5 = df['close'] < ema_5
        
        rsi_above_50 = rsi > 50
        rsi_below_50 = rsi < 50
        rsi_cross_up = (rsi_prev <= 50) & (rsi > 50)
        rsi_cross_down = (rsi_prev >= 50) & (rsi < 50)
        
        rsi_rising_3 = (rsi > rsi_prev) & (rsi_prev > rsi_prev2)
        rsi_falling_3 = (rsi < rsi_prev) & (rsi_prev < rsi_prev2)
        
        bullish_candle = df['close'] > df['open']
        bearish_candle = df['close'] < df['open']
        
        return {
            'rsi': rsi,
            'ema_21': ema_21,
            'atr': atr,
            'uptrend': uptrend,
            'strong_uptrend': strong_uptrend,
            'downtrend': downtrend,
            'strong_downtrend': strong_downtrend,
            'price_above_ema5': price_above_ema5,
            'price_below_ema5': price_below_ema5,
            'rsi_above_50': rsi_above_50,
            'rsi_below_50': rsi_below_50,
            'rsi_cross_up': rsi_cross_up,
            'rsi_cross_down': rsi_cross_down,
            'rsi_rising_3': rsi_rising_3,
            'rsi_falling_3': rsi_falling_3,
            'bullish_candle': bullish_candle,
            'bearish_candle': bearish_candle
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        original_short_1 = vars['downtrend'] & vars['rsi_cross_down'] & vars['bearish_candle']
        original_short_2 = vars['downtrend'] & vars['strong_downtrend'] & vars['rsi_below_50'] & vars['rsi_falling_3'] & vars['price_below_ema5'] & vars['bearish_candle']
        return (original_short_1 | original_short_2).fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        original_long_1 = vars['uptrend'] & vars['rsi_cross_up'] & vars['bullish_candle']
        original_long_2 = vars['uptrend'] & vars['strong_uptrend'] & vars['rsi_above_50'] & vars['rsi_rising_3'] & vars['price_above_ema5'] & vars['bullish_candle']
        return (original_long_1 | original_long_2).fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        # SWAPPED: Original SL=3.0, TP=7.5 become inverted SL=7.5, TP=3.0
        original_sl_distance = vars['atr'] * 3.0
        original_tp_distance = vars['atr'] * 7.5
        
        sl = df['close'] - original_tp_distance
        tp = df['close'] + original_sl_distance
        
        return {'sl': sl, 'tp': tp}
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_21'].iloc[idx]
        
        if trade['direction'] == 'long':
            return current_close > current_ema
        elif trade['direction'] == 'short':
            return current_close < current_ema
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        return (df['close'] > vars['ema_21']).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        return (df['close'] < vars['ema_21']).fillna(False)
