from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSIUltraQuality1M(Strategy):
    """
    Author: MCP Client
    Description: Ultra-Quality RSI Strategy for 1M.
                 
                 Pragmatic approach: Fewer trades, higher quality.
                 
                 Design:
                 - Extreme RSI levels only (25/75)
                 - Strong trend requirement
                 - Fixed pip SL/TP (more predictable than ATR)
                 - 5-pip fixed SL, 20-pip fixed TP (1:4 RRR)
                 
                 Goal: Trade only when conditions are perfect.
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # RSI shifts
        rsi_prev = rsi.shift(1)
        rsi_prev2 = rsi.shift(2)
        
        # EMA 34 for trend
        ema_34 = df['close'].ewm(span=34, adjust=False).mean()
        
        # ATR 10 (just for volatility check)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=10, min_periods=10).mean()
        
        # Trend
        price_above_ema = df['close'] > ema_34
        price_below_ema = df['close'] < ema_34
        
        # RSI extreme levels (stricter)
        rsi_oversold_extreme = rsi < 25
        rsi_overbought_extreme = rsi > 75
        
        # RSI momentum (must be turning)
        rsi_bullish_turn = (rsi > rsi_prev) & (rsi_prev > rsi_prev2)
        rsi_bearish_turn = (rsi < rsi_prev) & (rsi_prev < rsi_prev2)
        
        # Candle type
        bullish_candle = df['close'] > df['open']
        bearish_candle = df['close'] < df['open']
        
        # Minimum volatility (market must be moving)
        atr_pct = atr / df['close']
        min_volatility = atr_pct > 0.0003
        
        # Maximum volatility (avoid slippage)
        max_volatility = atr_pct < 0.0030
        normal_volatility = min_volatility & max_volatility
        
        return {
            'rsi': rsi,
            'rsi_prev': rsi_prev,
            'ema_34': ema_34,
            'atr': atr,
            'price_above_ema': price_above_ema,
            'price_below_ema': price_below_ema,
            'rsi_oversold_extreme': rsi_oversold_extreme,
            'rsi_overbought_extreme': rsi_overbought_extreme,
            'rsi_bullish_turn': rsi_bullish_turn,
            'rsi_bearish_turn': rsi_bearish_turn,
            'bullish_candle': bullish_candle,
            'bearish_candle': bearish_candle,
            'normal_volatility': normal_volatility
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Ultra-Quality Long Entry:
        
        REQUIRE ALL:
        1. Price > EMA 34 (uptrend)
        2. RSI < 25 (extreme oversold) AND RSI turning up
        3. Bullish candle
        4. Normal volatility
        """
        signal = vars['price_above_ema'] & \
                 vars['rsi_oversold_extreme'] & \
                 vars['rsi_bullish_turn'] & \
                 vars['bullish_candle'] & \
                 vars['normal_volatility']
        
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Ultra-Quality Short Entry:
        
        REQUIRE ALL:
        1. Price < EMA 34 (downtrend)
        2. RSI > 75 (extreme overbought) AND RSI turning down
        3. Bearish candle
        4. Normal volatility
        """
        signal = vars['price_below_ema'] & \
                 vars['rsi_overbought_extreme'] & \
                 vars['rsi_bearish_turn'] & \
                 vars['bearish_candle'] & \
                 vars['normal_volatility']
        
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Fixed pip SL/TP for XAUUSD.
        SL = 5 pips ($5.00)
        TP = 20 pips ($20.00)
        RRR = 1:4
        """
        sl = df['close'] - 5.0  # 5 pip fixed stop loss
        tp = df['close'] + 20.0  # 20 pip fixed take profit
        
        return {
            'sl': sl,
            'tp': tp
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Dynamic Exit Logic:
        - Long: Close below EMA 34
        - Short: Close above EMA 34
        """
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_34'].iloc[idx]
        
        if trade['direction'] == 'long':
            return current_close < current_ema
        elif trade['direction'] == 'short':
            return current_close > current_ema
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for long positions."""
        return (df['close'] < vars['ema_34']).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for short positions."""
        return (df['close'] > vars['ema_34']).fillna(False)
