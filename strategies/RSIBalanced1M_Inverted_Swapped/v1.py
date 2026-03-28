from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSIBalanced1M_Inverted_Swapped(Strategy):
    """
    Author: MCP Client
    Description: INVERTED version of RSIBalanced1M with SWAPPED distances.
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        rsi_prev = rsi.shift(1)
        
        ema_21 = df['close'].ewm(span=21, adjust=False).mean()
        
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=10, min_periods=10).mean()
        
        uptrend = df['close'] > ema_21
        downtrend = df['close'] < ema_21
        
        rsi_buy_zone = (rsi >= 30) & (rsi <= 45)
        rsi_bullish_momentum = rsi > rsi_prev
        
        rsi_sell_zone = (rsi >= 55) & (rsi <= 70)
        rsi_bearish_momentum = rsi < rsi_prev
        
        candle_body_pct = 2 * abs(df['close'] - df['open']) / (df['high'] - df['low'] + 0.00001)
        decent_candle = candle_body_pct > 0.35
        
        bullish_candle = df['close'] > df['open']
        bearish_candle = df['close'] < df['open']
        
        atr_pct = atr / df['close']
        adequate_volatility = atr_pct > 0.0002
        
        return {
            'rsi': rsi,
            'ema_21': ema_21,
            'uptrend': uptrend,
            'downtrend': downtrend,
            'rsi_buy_zone': rsi_buy_zone,
            'rsi_sell_zone': rsi_sell_zone,
            'rsi_bullish_momentum': rsi_bullish_momentum,
            'rsi_bearish_momentum': rsi_bearish_momentum,
            'decent_candle': decent_candle,
            'bullish_candle': bullish_candle,
            'bearish_candle': bearish_candle,
            'adequate_volatility': adequate_volatility
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        original_short = vars['downtrend'] & vars['rsi_sell_zone'] & vars['rsi_bearish_momentum'] & vars['decent_candle'] & vars['adequate_volatility']
        return original_short.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        original_long = vars['uptrend'] & vars['rsi_buy_zone'] & vars['rsi_bullish_momentum'] & vars['decent_candle'] & vars['adequate_volatility']
        return original_long.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        # SWAPPED: Original SL=10, TP=25 become inverted SL=25, TP=10
        original_sl_distance = 10.0
        original_tp_distance = 25.0
        
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
