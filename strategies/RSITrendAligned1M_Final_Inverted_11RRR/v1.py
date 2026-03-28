from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSITrendAligned1M_Final_Inverted_11RRR(Strategy):
    """
    Author: MCP Client
    Description: INVERTED version of RSITrendAligned1M_Final with 1:1 RRR.
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        rsi_prev = rsi.shift(1)
        rsi_prev5 = rsi.shift(5)
        
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14, min_periods=14).mean()
        
        price_above_ema20 = df['close'] > ema_20
        price_above_ema50 = df['close'] > ema_50
        price_below_ema20 = df['close'] < ema_20
        price_below_ema50 = df['close'] < ema_50
        
        ema_bullish_aligment = ema_20 > ema_50
        ema_bearish_aligment = ema_20 < ema_50
        
        strong_uptrend = price_above_ema20 & price_above_ema50 & ema_bullish_aligment
        strong_downtrend = price_below_ema20 & price_below_ema50 & ema_bearish_aligment
        
        rsi_oversold = rsi < 35
        rsi_neutral_bullish = (rsi >= 35) & (rsi <= 55)
        rsi_bullish_recovering = rsi_oversold & (rsi > rsi_prev)
        rsi_bullish_continuing = rsi_neutral_bullish & (rsi > rsi_prev) & (rsi > rsi_prev5)
        
        rsi_overbought = rsi > 65
        rsi_neutral_bearish = (rsi >= 45) & (rsi <= 65)
        rsi_bearish_correcting = rsi_overbought & (rsi < rsi_prev)
        rsi_bearish_continuing = rsi_neutral_bearish & (rsi < rsi_prev) & (rsi < rsi_prev5)
        
        candle_body = df['close'] - df['open']
        candle_range = df['high'] - df['low']
        body_ratio = 2 * abs(candle_body) / (candle_range + 0.0001)
        strong_candle = body_ratio > 0.4
        bullish_candle = candle_body > 0
        bearish_candle = candle_body < 0
        
        close_momentum_5 = df['close'] > df['close'].shift(5)
        
        atr_pct = atr / df['close']
        adequate_volatility = atr_pct > 0.0002
        extreme_volatility = atr_pct > 0.0050
        normal_volatility = adequate_volatility & (~extreme_volatility)
        
        return {
            'rsi': rsi,
            'ema_20': ema_20,
            'atr': atr,
            'strong_uptrend': strong_uptrend,
            'strong_downtrend': strong_downtrend,
            'rsi_bullish_recovering': rsi_bullish_recovering,
            'rsi_bullish_continuing': rsi_bullish_continuing,
            'rsi_bearish_correcting': rsi_bearish_correcting,
            'rsi_bearish_continuing': rsi_bearish_continuing,
            'bullish_candle': bullish_candle,
            'bearish_candle': bearish_candle,
            'strong_candle': strong_candle,
            'close_momentum_5': close_momentum_5,
            'normal_volatility': normal_volatility
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        original_short_1 = vars['strong_downtrend'] & vars['rsi_bearish_correcting'] & vars['bearish_candle'] & vars['normal_volatility']
        original_short_2 = vars['strong_downtrend'] & vars['rsi_bearish_continuing'] & vars['strong_candle'] & vars['bearish_candle'] & (~vars['close_momentum_5']) & vars['normal_volatility']
        return (original_short_1 | original_short_2).fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        original_long_1 = vars['strong_uptrend'] & vars['rsi_bullish_recovering'] & vars['bullish_candle'] & vars['normal_volatility']
        original_long_2 = vars['strong_uptrend'] & vars['rsi_bullish_continuing'] & vars['strong_candle'] & vars['bullish_candle'] & vars['close_momentum_5'] & vars['normal_volatility']
        return (original_long_1 | original_long_2).fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        distance = vars['atr'] * 5.25
        sl = df['close'] - distance
        tp = df['close'] + distance
        return {'sl': sl, 'tp': tp}
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_20'].iloc[idx]
        
        # INVERTED exit logic
        if trade['direction'] == 'long':
            return current_close > current_ema
        elif trade['direction'] == 'short':
            return current_close < current_ema
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        return (df['close'] > vars['ema_20']).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        return (df['close'] < vars['ema_20']).fillna(False)
