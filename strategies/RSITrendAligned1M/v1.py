from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSITrendAligned1M(Strategy):
    """
    Author: MCP Client
    Description: RSI-based trend-aligned strategy for 1M timeframe with 1:2 RRR minimum.
                 Designed to generate 10+ high-quality trades daily using trend alignment
                 and RSI momentum reversals with ATR-based dynamic SL/TP.
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        # Calculate RSI (7 period for 1M frequent signals)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=7, min_periods=7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=7, min_periods=7).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # EMA 50 for trend alignment
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR 14 for dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14, min_periods=14).mean()
        
        # RSI Previous to detect crossovers
        rsi_prev = rsi.shift(1)
        
        # Bullish candle check
        bullish_candle = df['close'] > df['open']
        
        # Bearish candle check
        bearish_candle = df['close'] < df['open']
        
        # Volume confirmation (use volume ratio to average)
        avg_volume = df['volume'].rolling(window=20, min_periods=20).mean()
        above_avg_volume = df['volume'] > (avg_volume * 1.2)
        
        # Minimum volatility check (ATR relative to price)
        atr_pct = atr / df['close']
        sufficient_volatility = atr_pct > 0.0005  # At least 0.05% price movement
        
        return {
            'rsi': rsi,
            'rsi_prev': rsi_prev,
            'ema_50': ema_50,
            'atr': atr,
            'atr_pct': atr_pct,
            'bullish_candle': bullish_candle,
            'bearish_candle': bearish_candle,
            'above_avg_volume': above_avg_volume,
            'sufficient_volatility': sufficient_volatility
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Long Entry Conditions:
        1. Price > EMA 50 (uptrend)
        2. RSI crosses above 30 from below (oversold reversal)
        3. Bullish candle (momentum confirmation)
        4. Above average volume (participation)
        5. Sufficient volatility (tradeable market)
        """
        trend = df['close'] > vars['ema_50']
        rsi_oversold_cross = (vars['rsi_prev'] < 30) & (vars['rsi'] > 30) & (vars['rsi'] < 50)
        momentum_confirm = vars['bullish_candle']
        volume_confirm = vars['above_avg_volume']
        volatility_ok = vars['sufficient_volatility']
        
        signal = trend & rsi_oversold_cross & momentum_confirm & volume_confirm & volatility_ok
        
        # Fill NaN values
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Short Entry Conditions:
        1. Price < EMA 50 (downtrend)
        2. RSI crosses below 70 from above (overbought reversal)
        3. Bearish candle (momentum confirmation)
        4. Above average volume (participation)
        5. Sufficient volatility (tradeable market)
        """
        trend = df['close'] < vars['ema_50']
        rsi_overbought_cross = (vars['rsi_prev'] > 70) & (vars['rsi'] < 70) & (vars['rsi'] > 50)
        momentum_confirm = vars['bearish_candle']
        volume_confirm = vars['above_avg_volume']
        volatility_ok = vars['sufficient_volatility']
        
        signal = trend & rsi_overbought_cross & momentum_confirm & volume_confirm & volatility_ok
        
        # Fill NaN values
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Dynamic SL/TP based on ATR with 1:2 RRR.
        SL = 1.5x ATR away from entry
        TP = 3x ATR away from entry
        """
        atr_multiplier_sl = 1.5
        atr_multiplier_tp = 3.0
        
        # Stop Loss (1.5x ATR) - absolute price level
        sl = df['close'] - (vars['atr'] * atr_multiplier_sl)
        
        # Take Profit (3x ATR) - absolute price level
        tp = df['close'] + (vars['atr'] * atr_multiplier_tp)
        
        return {
            'sl': sl,
            'tp': tp
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Dynamic Exit Logic:
        - Long: Exit if price closes below EMA 50 (trend reversal)
        - Short: Exit if price above EMA 50 (trend reversal)
        """
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_50'].iloc[idx]
        
        if trade['direction'] == 'long':
            # Exit long if close below EMA 50 (trend reversal)
            return current_close < current_ema
        elif trade['direction'] == 'short':
            # Exit short if close above EMA 50 (trend reversal)
            return current_close > current_ema
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit signal for long positions."""
        return (df['close'] < vars['ema_50']).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit signal for short positions."""
        return (df['close'] > vars['ema_50']).fillna(False)