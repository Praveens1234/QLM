from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSITrendAligned1M_Final(Strategy):
    """
    Author: MCP Client
    Description: Final Balanced RSI Trend Aligned Strategy for 1M.
                 
                 Target: 8-12 quality trades per day with 45%+ win rate.
                 
                 Design Principles:
                 1. RSI as confirmation, not primary signal
                 2. Price action + trend as primary filter
                 3. Multiple confluence factors required
                 4. Dynamic SL/TP with 1:2.5 RRR
                 5. Quality over quantity approach
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
        rsi_prev5 = rsi.shift(5)
        
        # EMAs for trend filtering
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR 14 for dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14, min_periods=14).mean()
        
        # Price action filters
        # Trend alignment
        price_above_ema20 = df['close'] > ema_20
        price_above_ema50 = df['close'] > ema_50
        price_below_ema20 = df['close'] < ema_20
        price_below_ema50 = df['close'] < ema_50
        
        # EMA alignment (confluence)
        ema_bullish_aligment = ema_20 > ema_50
        ema_bearish_aligment = ema_20 < ema_50
        
        # Strong uptrend/downtrend
        strong_uptrend = price_above_ema20 & price_above_ema50 & ema_bullish_aligment
        strong_downtrend = price_below_ema20 & price_below_ema50 & ema_bearish_aligment
        
        # RSI conditions
        # Long: RSI recovering from oversold or neutral-bullish
        rsi_oversold = rsi < 35
        rsi_neutral_bullish = (rsi >= 35) & (rsi <= 55)
        rsi_bullish_recovering = rsi_oversold & (rsi > rsi_prev)
        rsi_bullish_continuing = rsi_neutral_bullish & (rsi > rsi_prev) & (rsi > rsi_prev5)
        
        # Short: RSI correcting from overbought or neutral-bearish  
        rsi_overbought = rsi > 65
        rsi_neutral_bearish = (rsi >= 45) & (rsi <= 65)
        rsi_bearish_correcting = rsi_overbought & (rsi < rsi_prev)
        rsi_bearish_continuing = rsi_neutral_bearish & (rsi < rsi_prev) & (rsi < rsi_prev5)
        
        # Candle confirmation
        candle_body = df['close'] - df['open']
        candle_range = df['high'] - df['low']
        body_ratio = 2 * abs(candle_body) / (candle_range + 0.0001)
        strong_candle = body_ratio > 0.4
        bullish_candle = candle_body > 0
        bearish_candle = candle_body < 0
        
        # Momentum (using recent closes)
        close_momentum_5 = df['close'] > df['close'].shift(5)
        
        # Volatility check (ensure tradeable market)
        atr_pct = atr / df['close']
        adequate_volatility = atr_pct > 0.0002
        
        # Avoid extreme volatility (slippage risk)
        extreme_volatility = atr_pct > 0.0050
        normal_volatility = adequate_volatility & (~extreme_volatility)
        
        return {
            'rsi': rsi,
            'rsi_prev': rsi_prev,
            'ema_20': ema_20,
            'ema_50': ema_50,
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
        """
        Long Entry - Requires strong trend alignment + RSI confirmation:
        
        Condition A: Oversold Recovery
        - Strong uptrend + RSI oversold and recovering + bullish candle + normal volatility
        
        Condition B: Trend Continuation  
        - Strong uptrend + RSI neutral-bullish and rising + strong bullish candle + positive 5-momentum + normal volatility
        
        Must meet BOTH trend and RSI conditions
        """
        # Condition A: Oversold recovery
        recovery_trade = vars['strong_uptrend'] & \
                        vars['rsi_bullish_recovering'] & \
                        vars['bullish_candle'] & \
                        vars['normal_volatility']
        
        # Condition B: Trend continuation
        continuation_trade = vars['strong_uptrend'] & \
                           vars['rsi_bullish_continuing'] & \
                           vars['strong_candle'] & \
                           vars['bullish_candle'] & \
                           vars['close_momentum_5'] & \
                           vars['normal_volatility']
        
        signal = recovery_trade | continuation_trade
        
        return signal.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Short Entry - Requires strong trend alignment + RSI confirmation:
        
        Condition A: Overbought Correction
        - Strong downtrend + RSI overbought and correcting + bearish candle + normal volatility
        
        Condition B: Trend Continuation
        - Strong downtrend + RSI neutral-bearish and falling + strong bearish candle + negative 5-momentum + normal volatility
        
        Must meet BOTH trend and RSI conditions
        """
        # Condition A: Overbought correction
        correction_trade = vars['strong_downtrend'] & \
                         vars['rsi_bearish_correcting'] & \
                         vars['bearish_candle'] & \
                         vars['normal_volatility']
        
        # Condition B: Trend continuation
        continuation_trade = vars['strong_downtrend'] & \
                           vars['rsi_bearish_continuing'] & \
                           vars['strong_candle'] & \
                           vars['bearish_candle'] & \
                           (~vars['close_momentum_5']) & \
                           vars['normal_volatility']
        
        signal = correction_trade | continuation_trade
        
        return signal.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Dynamic SL/TP with 1:2.5 RRR.
        Designed for XAUUSD 1M timeframe characteristics.
        
        SL = 3.0x ATR (respect volatility)
        TP = 7.5x ATR (2.5x reward for risk taken)
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
        - Long: Close below EMA 20 (trend weakened)
        - Short: Close above EMA 20 (trend weakened)
        """
        idx = trade['current_idx']
        current_close = df.loc[idx, 'close']
        current_ema = vars['ema_20'].iloc[idx]
        
        if trade['direction'] == 'long':
            return current_close < current_ema
        elif trade['direction'] == 'short':
            return current_close > current_ema
        
        return False
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for long positions."""
        return (df['close'] < vars['ema_20']).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Vectorized exit for short positions."""
        return (df['close'] > vars['ema_20']).fillna(False)
