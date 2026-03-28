from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSIBalanced1M(Strategy):
    """
    Author: MCP Client
    Description: Balanced RSI Strategy for 1M.
                 
                 Target: 5-10 quality trades per day.
                 
                 Balanced Design:
                 - RSI zones (30/45 for long, 55/70 for short) with momentum
                 - Single EMA(21) for trend
                 - Fixed pip SL: 10 pips, TP: 25 pips (1:2.5 RRR)
                 - Candle body filter
                 - Moderate volatility filter
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # RSI shifts for momentum
        rsi_prev = rsi.shift(1)
        
        # EMA 21 for trend
        ema_21 = df['close'].ewm(span=21, adjust=False).mean()
        
        # ATR 10
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=10, min_periods=10).mean()
        
        # Trend
        uptrend = df['close'] > ema_21
        downtrend = df['close'] < ema_21
        
        # RSI zones for long
        rsi_buy_zone = (rsi >= 30) & (rsi <= 45)
        rsi_bullish_momentum = rsi > rsi_prev
        
        # RSI zones for short
        rsi_sell_zone = (rsi >= 55) & (rsi <= 70)
        rsi_bearish_momentum = rsi < rsi_prev
        
        # Candle filter
        candle_body_pct = 2 * abs(df['close'] - df['open']) / (df['high'] - df['low'] + 0.00001)
        decent_candle = candle_body_pct > 0.35
        
        bullish_candle = df['close'] > df['open']
        bearish_candle = df['close'] < df['open']
        
        # Volatility
        atr_pct = atr / df['close']
        adequate_volatility = atr_pct > 0.0002
        
        return {
            'rsi': rsi,
            'rsi_prev': rsi_prev,
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
        """
        Balanced Long Entry:
        - Uptrend
        - RSI in buy zone (30-45)
        - RSI bullish momentum
        - Bullish or neutral candle
        - Decent candle body
        - Adequate volatility
        """
        signal = vars['uptrend'] & \
                 vars['rsi_buy_zone'] & \
                 vars['rsi_bullish_momentum'] & \
                 vars['decent_candle'] & \
                 vars['adequate_volatility']
        
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Balanced Short Entry:
        - Downtrend
        - RSI in sell zone (55-70)
        - RSI bearish momentum
        - Bearish or neutral candle
        - Decent candle body
        - Adequate volatility
        """
        signal = vars['downtrend'] & \
                 vars['rsi_sell_zone'] & \
                 vars['rsi_bearish_momentum'] & \
                 vars['decent_candle'] & \
                 vars['adequate_volatility']
        
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Fixed pip SL/TP for XAUUSD.
        SL = 10 pips ($10.00)
        TP = 25 pips ($25.00)
        RRR = 1:2.5
        """
        sl = df['close'] - 10.0
        tp = df['close'] + 25.0
        
        return {
            'sl': sl,
            'tp': tp
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Exit Logic:
        - Long: Close below EMA 21
        - Short: Close above EMA 21
        """
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_21'].iloc[idx]
        
        if trade['direction'] == 'long':
            return current_close < current_ema
        elif trade['direction'] == 'short':
            return current_close > current_ema
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for long positions."""
        return (df['close'] < vars['ema_21']).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for short positions."""
        return (df['close'] > vars['ema_21']).fillna(False)
