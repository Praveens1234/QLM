from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSITrendAligned1M_v3(Strategy):
    """
    Author: MCP Client
    Description: Aggressive RSI trend-aligned strategy for 1M timeframe.
                 Designed for 10+ daily trades with quality filters.
                 
                 Key Changes:
                 - RSI(9) for faster signals
                 - Single EMA(34) trend filter
                 - RSI zones instead of crossovers
                 - Removed volume filter
                 - Wider SL/TP ratios (1:2.5)
                 - Momentum confirmation
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        # RSI 9 (faster for 1M)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=9, min_periods=9).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=9, min_periods=9).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # EMA 34 for trend (between fast and slow)
        ema_34 = df['close'].ewm(span=34, adjust=False).mean()
        
        # ATR 7 (shorter period for 1M)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=7, min_periods=7).mean()
        
        # RSI shift for momentum
        rsi_prev = rsi.shift(1)
        
        # RSI zones
        rsi_oversold = (vars['rsi'] < 30) if False else (rsi < 30)
        rsi_overbought = (vars['rsi'] > 70) if False else (rsi > 70)
        rsi_neutral_oversold = (rsi >= 30) & (rsi < 50)
        rsi_neutral_overbought = (rsi > 50) & (rsi <= 70)
        
        # Bullish/Bearish candles
        is_bullish = df['close'] > df['open']
        is_bearish = df['close'] < df['open']
        
        # Body size filter (avoid dojis)
        body_size = 2 * abs(df['close'] - df['open']) / (df['high'] - df['low'] + 0.0001)
        has_body = body_size > 0.3
        
        # Trend alignment (price vs EMA)
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
        Long Entry - Multiple scenarios:
        
        Scenario 1: Oversold reversal
        - Uptrend + RSI < 30 + RSI rising + Bullish candle
        
        Scenario 2: Pullback in uptrend
        - Uptrend + 30 <= RSI < 45 + RSI rising + Bullish candle
        """
        # Scenario 1: Oversold reversal
        oversold_reversal = (vars['uptrend']) & \
                           (vars['rsi_oversold']) & \
                           (vars['rsi_rising']) & \
                           (vars['is_bullish']) & \
                           (vars['has_body'])
        
        # Scenario 2: Pullback continuation
        pullback_continuation = (vars['uptrend']) & \
                               (vars['rsi_neutral_oversold']) & \
                               (vars['rsi_rising']) & \
                               (vars['is_bullish']) & \
                               (vars['has_body'])
        
        signal = oversold_reversal | pullback_continuation
        
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Short Entry - Multiple scenarios:
        
        Scenario 1: Overbought reversal
        - Downtrend + RSI > 70 + RSI falling + Bearish candle
        
        Scenario 2: Rally in downtrend
        - Downtrend + 55 < RSI <= 70 + RSI falling + Bearish candle
        """
        # Scenario 1: Overbought reversal
        overbought_reversal = (vars['downtrend']) & \
                            (vars['rsi_overbought']) & \
                            (vars['rsi_falling']) & \
                            (vars['is_bearish']) & \
                            (vars['has_body'])
        
        # Scenario 2: Rally continuation
        rally_continuation = (vars['downtrend']) & \
                           (vars['rsi_neutral_overbought']) & \
                           (vars['rsi_falling']) & \
                           (vars['is_bearish']) & \
                           (vars['has_body'])
        
        signal = overbought_reversal | rally_continuation
        
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Dynamic SL/TP with 1:2.5 RRR.
        SL = 2.5x ATR
        TP = 6.25x ATR
        """
        sl = df['close'] - (vars['atr'] * 2.5)
        tp = df['close'] + (vars['atr'] * 6.25)
        
        return {
            'sl': sl,
            'tp': tp
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Dynamic Exit Logic:
        - Long: Close below EMA 34 or RSI > 80
        - Short: Close above EMA 34 or RSI < 20
        """
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_34'].iloc[idx]
        current_rsi = vars['rsi'].iloc[idx]
        
        if trade['direction'] == 'long':
            return (current_close < current_ema) or (current_rsi > 80)
        elif trade['direction'] == 'short':
            return (current_close > current_ema) or (current_rsi < 20)
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for long positions."""
        close_below_ema = df['close'] < vars['ema_34']
        rsi_exit_long = vars['rsi'] > 80
        return (close_below_ema | rsi_exit_long).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for short positions."""
        close_above_ema = df['close'] > vars['ema_34']
        rsi_exit_short = vars['rsi'] < 20
        return (close_above_ema | rsi_exit_short).fillna(False)
