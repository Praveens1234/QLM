from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class PriceActionRSI1M_Inverted_11RRR(Strategy):
    """
    Author: MCP Client
    Description: INVERTED version of PriceActionRSI1M with 1:1 RRR (fixed 25 pips).
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        ema_7 = df['close'].ewm(span=7, adjust=False).mean()
        ema_25 = df['close'].ewm(span=25, adjust=False).mean()
        
        prev_open = df['open'].shift(1)
        prev_close = df['close'].shift(1)
        
        prev_bearish = prev_close < prev_open
        current_bullish = df['close'] > df['open']
        bullish_engulfing = prev_bearish & current_bullish & (df['open'] < prev_close) & (df['close'] > prev_open)
        
        prev_bullish = prev_close > prev_open
        current_bearish = df['close'] < df['open']
        bearish_engulfing = prev_bullish & current_bearish & (df['open'] > prev_close) & (df['close'] < prev_open)
        
        uptrend = ema_7 > ema_25
        downtrend = ema_7 < ema_25
        
        rsi_value_zone_long = (rsi >= 30) & (rsi <= 50)
        rsi_value_zone_short = (rsi >= 50) & (rsi <= 70)
        
        rsi_rising = rsi > rsi.shift(1)
        rsi_falling = rsi < rsi.shift(1)
        
        return {
            'rsi': rsi,
            'ema_7': ema_7,
            'ema_25': ema_25,
            'uptrend': uptrend,
            'downtrend': downtrend,
            'bullish_engulfing': bullish_engulfing,
            'bearish_engulfing': bearish_engulfing,
            'rsi_value_zone_long': rsi_value_zone_long,
            'rsi_value_zone_short': rsi_value_zone_short,
            'rsi_rising': rsi_rising,
            'rsi_falling': rsi_falling
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        original_short = vars['bearish_engulfing'] & vars['downtrend'] & vars['rsi_value_zone_short'] & vars['rsi_falling']
        return original_short.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        original_long = vars['bullish_engulfing'] & vars['uptrend'] & vars['rsi_value_zone_long'] & vars['rsi_rising']
        return original_long.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        # Fixed 1:1 RRR at 25 pips (average of 15 and 35)
        distance = 25.0
        sl = df['close'] - distance
        tp = df['close'] + distance
        return {'sl': sl, 'tp': tp}
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_25'].iloc[idx]
        
        if trade['direction'] == 'long':
            return current_close > current_ema
        elif trade['direction'] == 'short':
            return current_close < current_ema
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        return (df['close'] > vars['ema_25']).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        return (df['close'] < vars['ema_25']).fillna(False)
