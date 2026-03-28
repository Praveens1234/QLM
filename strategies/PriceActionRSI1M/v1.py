from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class PriceActionRSI1M(Strategy):
    """
    Author: MCP Client
    Description: Price Action + RSI Confirmation Strategy for 1M.
                 
                 Reverse approach: Price action as PRIMARY signal, RSI as CONFIRMATION.
                 
                 Target: 8-12 quality trades per day.
                 
                 Logic:
                 - Long: Engulfing bullish candle + RSI < 50 (value zone) + EMA trend
                 - Short: Engulfing bearish candle + RSI > 50 (value zone) + EMA trend
                 - Fixed SL: 15 pips, TP: 35 pips (1:2.33 RRR)
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # EMA speeds for trend identification
        ema_7 = df['close'].ewm(span=7, adjust=False).mean()
        ema_25 = df['close'].ewm(span=25, adjust=False).mean()
        
        # Previous candle for engulfing patterns
        prev_open = df['open'].shift(1)
        prev_close = df['close'].shift(1)
        
        # Bullish engulfing: Previous bearish candle, current bullish that engulfs previous
        prev_bearish = prev_close < prev_open
        current_bullish = df['close'] > df['open']
        bullish_engulfing = prev_bearish & current_bullish & \
                           (df['open'] < prev_close) & (df['close'] > prev_open)
        
        # Bearish engulfing: Previous bullish candle, current bearish that engulfs previous  
        prev_bullish = prev_close > prev_open
        current_bearish = df['close'] < df['open']
        bearish_engulfing = prev_bullish & current_bearish & \
                          (df['open'] > prev_close) & (df['close'] < prev_open)
        
        # Trend
        uptrend = ema_7 > ema_25
        downtrend = ema_7 < ema_25
        
        # RSI in value zone
        rsi_value_zone_long = (rsi >= 30) & (rsi <= 50)
        rsi_value_zone_short = (rsi >= 50) & (rsi <= 70)
        
        # RSI direction
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
        """
        Price Action + RSI Confirmation Long:
        
        REQUIRE ALL:
        1. Bullish engulfing pattern (strong price action)
        2. Uptrend alignment (ema7 > ema25)
        3. RSI in value zone (30-50)
        4. RSI rising (momentum confirmation)
        """
        signal = vars['bullish_engulfing'] & \
                 vars['uptrend'] & \
                 vars['rsi_value_zone_long'] & \
                 vars['rsi_rising']
        
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Price Action + RSI Confirmation Short:
        
        REQUIRE ALL:
        1. Bearish engulfing pattern (strong price action)
        2. Downtrend alignment (ema7 < ema25)
        3. RSI in value zone (50-70)
        4. RSI falling (momentum confirmation)
        """
        signal = vars['bearish_engulfing'] & \
                 vars['downtrend'] & \
                 vars['rsi_value_zone_short'] & \
                 vars['rsi_falling']
        
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Fixed pip SL/TP for XAUUSD.
        SL = 15 pips ($15.00)
        TP = 35 pips ($35.00)
        RRR = 1:2.33
        """
        sl = df['close'] - 15.0
        tp = df['close'] + 35.0
        
        return {
            'sl': sl,
            'tp': tp
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Exit Logic:
        - Long: Close below EMA 25 (trend breakdown)
        - Short: Close above EMA 25 (trend breakdown)
        """
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_25'].iloc[idx]
        
        if trade['direction'] == 'long':
            return current_close < current_ema
        elif trade['direction'] == 'short':
            return current_close > current_ema
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for long positions."""
        return (df['close'] < vars['ema_25']).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for short positions."""
        return (df['close'] > vars['ema_25']).fillna(False)
