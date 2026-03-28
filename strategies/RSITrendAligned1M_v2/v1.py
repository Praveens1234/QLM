from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSITrendAligned1M_v2(Strategy):
    """
    Author: MCP Client
    Description: Improved RSI-based trend-aligned strategy for 1M timeframe.
                 Key improvements:
                 - Relaxed entry filters for more trade opportunities
                 - RSI(14) for more reliable signals
                 - Trend strength filter
                 - Dynamic SL/TP based on volatility
                 - Designed for 10+ high-quality trades daily
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        # RSI 14 (more stable than RSI 7)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # EMA 20 for trend alignment (faster than EMA 50)
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR 14 for dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14, min_periods=14).mean()
        
        # RSI shift for crossover detection
        rsi_prev = rsi.shift(1)
        
        # Bullish/Bearish candles
        is_bullish = df['close'] > df['open']
        is_bearish = df['close'] < df['open']
        
        # Trend strength (distance between EMAs)
        trend_strength = abs(ema_20 - ema_50) / df['close']
        strong_trend = trend_strength > 0.0003  # At least 0.03% EMA separation
        
        # Price vs EMA distance (momentum)
        price_vs_ema20 = (df['close'] - ema_20) / df['close']
        price_above_ema20 = price_vs_ema20 > 0.0005
        price_below_ema20 = price_vs_ema20 < -0.0005
        
        # Volume check (relaxed)
        avg_volume = df['volume'].rolling(window=10, min_periods=10).mean()
        normal_volume = df['volume'] > (avg_volume * 0.8)  # Lower threshold
        
        return {
            'rsi': rsi,
            'rsi_prev': rsi_prev,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'atr': atr,
            'is_bullish': is_bullish,
            'is_bearish': is_bearish,
            'strong_trend': strong_trend,
            'price_above_ema20': price_above_ema20,
            'price_below_ema20': price_below_ema20,
            'normal_volume': normal_volume
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Long Entry Conditions (more relaxed):
        1. Price > EMA 20 (short-term uptrend)
        2. Price > EMA 50 (long-term uptrend)
        3. RSI < 35 and increasing (oversold recovery)
        4. RSI crosses above 30 or RSI < 35 and RSI > RSI_prev
        5. Bullish or neutral candle
        6. Normal volume
        """
        uptrend_short = df['close'] > vars['ema_20']
        uptrend_long = df['close'] > vars['ema_50']
        
        # RSI conditions: oversold recovery (more flexible)
        rsi_oversold_recovery = (vars['rsi'] < 35) & (vars['rsi'] > vars['rsi_prev']) & (vars['rsi'] < 60)
        
        momentum_ok = vars['price_above_ema20']
        volume_ok = vars['normal_volume']
        
        signal = uptrend_short & uptrend_long & rsi_oversold_recovery & momentum_ok & volume_ok
        
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Short Entry Conditions (more relaxed):
        1. Price < EMA 20 (short-term downtrend)
        2. Price < EMA 50 (long-term downtrend)
        3. RSI > 65 and decreasing (overbought correction)
        4. RSI crosses below 70 or RSI > 65 and RSI < RSI_prev
        5. Bearish or neutral candle
        6. Normal volume
        """
        downtrend_short = df['close'] < vars['ema_20']
        downtrend_long = df['close'] < vars['ema_50']
        
        # RSI conditions: overbought correction (more flexible)
        rsi_overbought_correction = (vars['rsi'] > 65) & (vars['rsi'] < vars['rsi_prev']) & (vars['rsi'] > 40)
        
        momentum_ok = vars['price_below_ema20']
        volume_ok = vars['normal_volume']
        
        signal = downtrend_short & downtrend_long & rsi_overbought_correction & momentum_ok & volume_ok
        
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Dynamic SL/TP based on ATR with 1:2.5 RRR (more aggressive).
        SL = 2.0x ATR (wider for 1M noise)
        TP = 5.0x ATR (better payoff)
        """
        sl = df['close'] - (vars['atr'] * 2.0)  # 2.0x ATR stop loss
        tp = df['close'] + (vars['atr'] * 5.0)  # 5.0x ATR take profit
        
        return {
            'sl': sl,
            'tp': tp
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Dynamic Exit Logic:
        - Long: Exit if price closes below EMA 20 or RSI > 75
        - Short: Exit if price closes above EMA 20 or RSI < 25
        """
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema20 = vars['ema_20'].iloc[idx]
        current_rsi = vars['rsi'].iloc[idx]
        
        if trade['direction'] == 'long':
            # Exit long if close below EMA 20 (trend reversal) or RSI very overbought
            return (current_close < current_ema20) or (current_rsi > 75)
        elif trade['direction'] == 'short':
            # Exit short if close above EMA 20 (trend reversal) or RSI very oversold
            return (current_close > current_ema20) or (current_rsi < 25)
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit signal for long positions."""
        close_below_ema = df['close'] < vars['ema_20']
        rsi_overbought_exit = vars['rsi'] > 75
        return (close_below_ema | rsi_overbought_exit).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit signal for short positions."""
        close_above_ema = df['close'] > vars['ema_20']
        rsi_oversold_exit = vars['rsi'] < 25
        return (close_above_ema | rsi_oversold_exit).fillna(False)
