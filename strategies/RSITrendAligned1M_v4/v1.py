from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSITrendAligned1M_v4(Strategy):
    """
    Author: MCP Client
    Description: Balanced RSI trend-aligned strategy for 1M timeframe.
                 Target: 10-15 high-quality trades per day with 40%+ win rate.
                 
                 Key Features:
                 - RSI(14) for stable signals
                 - EMA(21) fast trend filter + EMA(50) trend confirmation
                 - Trend strength filter
                 - Quality filters (candle body, volatility)
                 - Dynamic SL/TP with 1:2.5 RRR
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # EMA 21 (fast) and EMA 50 (slow) for trend
        ema_21 = df['close'].ewm(span=21, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR 14
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14, min_periods=14).mean()
        
        # RSI momentum
        rsi_prev = rsi.shift(1)
        rsi_3ago = rsi.shift(3)
        
        # RSI trends
        rsi_trending_up = (rsi > rsi_prev) & (rsi_prev > rsi_3ago)
        rsi_trending_down = (rsi < rsi_prev) & (rsi_prev < rsi_3ago)
        
        # Candle body size
        body_ratio = 2 * abs(df['close'] - df['open']) / (df['high'] - df['low'] + 0.0001)
        strong_body = body_ratio > 0.4
        
        # Trend filter
        uptrend = df['close'] > ema_21
        strong_uptrend = (df['close'] > ema_21) & (ema_21 > ema_50)
        downtrend = df['close'] < ema_21
        strong_downtrend = (df['close'] < ema_21) & (ema_21 < ema_50)
        
        # Trend strength
        trend_strength = abs(ema_21 - ema_50) / df['close']
        strong_trend_signal = trend_strength > 0.0002
        
        # Volatility filter
        atr_pct = atr / df['close']
        sufficient_volatility = atr_pct > 0.0003
        
        return {
            'rsi': rsi,
            'rsi_prev': rsi_prev,
            'ema_21': ema_21,
            'ema_50': ema_50,
            'atr': atr,
            'rsi_trending_up': rsi_trending_up,
            'rsi_trending_down': rsi_trending_down,
            'strong_body': strong_body,
            'uptrend': uptrend,
            'strong_uptrend': strong_uptrend,
            'downtrend': downtrend,
            'strong_downtrend': strong_downtrend,
            'strong_trend': strong_trend_signal,
            'sufficient_volatility': sufficient_volatility
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Long Entry Condition:
        - Strong uptrend (price > EMA21 > EMA50)
        - RSI in recovery zone (30-45) OR oversold and rising
        - RSI trending up
        - Strong candle body
        - Sufficient volatility
        - Strong trend
        """
        rsi_recovery = (vars['rsi'] >= 30) & (vars['rsi'] <= 45)
        rsi_oversold_rising = (vars['rsi'] < 35) & (vars['rsi'] > vars['rsi_prev'])
        
        rsi_condition = (rsi_recovery | rsi_oversold_rising) & vars['rsi_trending_up']
        
        signal = vars['strong_uptrend'] & \
                 rsi_condition & \
                 vars['strong_body'] & \
                 vars['sufficient_volatility'] & \
                 vars['strong_trend']
        
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Short Entry Condition:
        - Strong downtrend (price < EMA21 < EMA50)
        - RSI in correction zone (55-70) OR overbought and falling
        - RSI trending down
        - Strong candle body
        - Sufficient volatility
        - Strong trend
        """
        rsi_correction = (vars['rsi'] >= 55) & (vars['rsi'] <= 70)
        rsi_overbought_falling = (vars['rsi'] > 65) & (vars['rsi'] < vars['rsi_prev'])
        
        rsi_condition = (rsi_correction | rsi_overbought_falling) & vars['rsi_trending_down']
        
        signal = vars['strong_downtrend'] & \
                 rsi_condition & \
                 vars['strong_body'] & \
                 vars['sufficient_volatility'] & \
                 vars['strong_trend']
        
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Dynamic SL/TP with 1:2.5 RRR.
        SL = 2.0x ATR
        TP = 5.0x ATR
        """
        sl = df['close'] - (vars['atr'] * 2.0)
        tp = df['close'] + (vars['atr'] * 5.0)
        
        return {
            'sl': sl,
            'tp': tp
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Dynamic Exit Logic:
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
