from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSIMomentum1M_v5(Strategy):
    """
    Author: MCP Client
    Description: RSI Momentum Strategy for 1M timeframe.
                 Completely different approach - trend FOLLOWING instead of reversal.
                 
                 Target: 10+ quality trades daily with 1:2 RRR.
                 
                 Logic:
                 - Buy when RSI breaks above 50 in uptrend (momentum confirmation)
                 - Sell when RSI breaks below 50 in downtrend
                 - Use EMA for trend direction
                 - Tight SL, wide TP (1:2.5 RRR)
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # RSI shift for crossover detection
        rsi_prev = rsi.shift(1)
        rsi_prev2 = rsi.shift(2)
        
        # EMA 21 for trend
        ema_21 = df['close'].ewm(span=21, adjust=False).mean()
        
        # EMA 5 for fast momentum
        ema_5 = df['close'].ewm(span=5, adjust=False).mean()
        
        # ATR 10 for dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=10, min_periods=10).mean()
        
        # Trend direction
        uptrend = df['close'] > ema_21
        uptrend_strength = (df['close'] - ema_21) / df['close']
        strong_uptrend = uptrend_strength > 0.0003
        
        downtrend = df['close'] < ema_21
        downtrend_strength = (ema_21 - df['close']) / df['close']
        strong_downtrend = downtrend_strength > 0.0003
        
        # Momentum alignment (price vs EMA5)
        price_above_ema5 = df['close'] > ema_5
        price_below_ema5 = df['close'] < ema_5
        
        # RSI conditions
        rsi_above_50 = rsi > 50
        rsi_below_50 = rsi < 50
        rsi_cross_up = (rsi_prev <= 50) & (rsi > 50)
        rsi_cross_down = (rsi_prev >= 50) & (rsi < 50)
        
        # RSI momentum
        rsi_rising_3 = (rsi > rsi_prev) & (rsi_prev > rsi_prev2)
        rsi_falling_3 = (rsi < rsi_prev) & (rsi_prev < rsi_prev2)
        
        # Candle type
        bullish_candle = df['close'] > df['open']
        bearish_candle = df['close'] < df['open']
        
        return {
            'rsi': rsi,
            'rsi_prev': rsi_prev,
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
        """
        Long Entry Conditions:
        1. Price > EMA 21 (uptrend)
        2. RSI crosses above 50 from below (momentum confirmation)
        3. OR (RSI > 50 and RSI rising and price > EMA5)
        4. Bullish candle
        """
        # Scenario 1: RSI cross above 50
        rsi_momentum_entry = vars['uptrend'] & \
                            vars['rsi_cross_up'] & \
                            vars['bullish_candle']
        
        # Scenario 2: Trend continuation
        trend_continuation = vars['uptrend'] & \
                           vars['strong_uptrend'] & \
                           vars['rsi_above_50'] & \
                           vars['rsi_rising_3'] & \
                           vars['price_above_ema5'] & \
                           vars['bullish_candle']
        
        signal = rsi_momentum_entry | trend_continuation
        
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Short Entry Conditions:
        1. Price < EMA 21 (downtrend)
        2. RSI crosses below 50 from above (momentum confirmation)
        3. OR (RSI < 50 and RSI falling and price < EMA5)
        4. Bearish candle
        """
        # Scenario 1: RSI cross below 50
        rsi_momentum_entry = vars['downtrend'] & \
                            vars['rsi_cross_down'] & \
                            vars['bearish_candle']
        
        # Scenario 2: Trend continuation
        trend_continuation = vars['downtrend'] & \
                           vars['strong_downtrend'] & \
                           vars['rsi_below_50'] & \
                           vars['rsi_falling_3'] & \
                           vars['price_below_ema5'] & \
                           vars['bearish_candle']
        
        signal = rsi_momentum_entry | trend_continuation
        
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Dynamic SL/TP with 1:2.5 RRR.
        SL = 3.0x ATR (wider to account for momentum stops)
        TP = 7.5x ATR (better RRR for momentum trades)
        """
        sl = df['close'] - (vars['atr'] * 3.0)
        tp = df['close'] + (vars['atr'] * 7.5)
        
        return {
            'sl': sl,
            'tp': tp
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Dynamic Exit Logic:
        - Long: Close below EMA 21 (trend reversal)
        - Short: Close above EMA 21 (trend reversal)
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
