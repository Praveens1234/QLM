from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class EntropyBreakoutHighAccuracy_v1(Strategy):
    """
    Author: MCP Client (AI Agent)
    Description: HIGH ACCURACY version - Focus on quality over quantity.
    
    DISCOVERY:
    - Previous versions had too many false signals (73K+ trades, low win rate)
    - The entropy/momentum indicators work but entry timing was wrong
    
    NEW APPROACH:
    1. EXTREME FILTERING - Only trade when ALL conditions align
    2. WAIT FOR CONFIRMATION - Don't jump on first signal
    3. VOLUME-LIKE CONFIRMATION - Use candle range as proxy
    4. BREAKOUT APPROACH - Trade with strong momentum, not against
    
    GOAL: Achieve 70%+ win rate with 1:1 RRR
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate indicators with focus on HIGH PROBABILITY setups."""
        
        # ========== 1. EXPLOSIVE MOMENTUM DETECTOR ==========
        # Look for explosive moves (breakouts)
        momentum_3 = df['close'].pct_change(periods=3) * 100
        momentum_10 = df['close'].pct_change(periods=10) * 100
        
        # Momentum acceleration
        momentum_accel = momentum_3 - momentum_3.shift(3)
        
        # ========== 2. CANDLE POWER INDEX ==========
        # Measure the power behind each candle
        candle_body = (df['close'] - df['open']).abs()
        candle_range = df['high'] - df['low']
        
        # Strong candles: body > 60% of range
        strong_candle = candle_body > (candle_range * 0.6)
        
        # Direction of strong candle
        bullish_power = strong_candle & (df['close'] > df['open'])
        bearish_power = strong_candle & (df['close'] < df['open'])
        
        # ========== 3. RANGE EXPANSION ==========
        # Compare current range to recent average
        avg_range = candle_range.rolling(20).mean()
        range_expansion = candle_range > (avg_range * 1.5)
        
        # ========== 4. SUPPORT/RESISTANCE PROXIMITY ==========
        # Use rolling highs/lows as dynamic S/R
        recent_high = df['high'].rolling(20).max()
        recent_low = df['low'].rolling(20).min()
        
        near_high = df['close'] >= recent_high * 0.995
        near_low = df['close'] <= recent_low * 1.005
        
        # ========== 5. TREND CONFIRMATION ==========
        ema_9 = df['close'].ewm(span=9, adjust=False).mean()
        ema_21 = df['close'].ewm(span=21, adjust=False).mean()
        ema_55 = df['close'].ewm(span=55, adjust=False).mean()
        ema_144 = df['close'].ewm(span=144, adjust=False).mean()
        
        # Strong bullish trend: all EMAs aligned
        strong_bullish = (ema_9 > ema_21) & (ema_21 > ema_55) & (ema_55 > ema_144)
        # Strong bearish trend: all EMAs aligned
        strong_bearish = (ema_9 < ema_21) & (ema_21 < ema_55) & (ema_55 < ema_144)
        
        # ========== 6. PULLBACK DETECTION ==========
        # In strong trend, look for pullbacks
        pullback_to_ema9 = (df['low'] <= ema_9) & (df['close'] > ema_9)
        pullback_to_ema21 = (df['low'] <= ema_21) & (df['close'] > ema_21)
        
        # ========== 7. ATR ==========
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # ========== 8. MULTI-TIMEFRAME MOMENTUM ==========
        # Use price relative to EMAs as momentum proxy
        price_above_ema21 = df['close'] > ema_21
        price_below_ema21 = df['close'] < ema_21
        
        # Consecutive bullish/bearish candles
        def count_consecutive(series):
            result = pd.Series(0, index=series.index)
            count = 0
            for i in range(len(series)):
                if series.iloc[i]:
                    count += 1
                else:
                    count = 0
                result.iloc[i] = count
            return result
        
        bullish_candles = df['close'] > df['open']
        bearish_candles = df['close'] < df['open']
        
        consecutive_bullish = count_consecutive(bullish_candles)
        consecutive_bearish = count_consecutive(bearish_candles)
        
        return {
            'momentum_3': momentum_3,
            'momentum_accel': momentum_accel,
            'bullish_power': bullish_power,
            'bearish_power': bearish_power,
            'range_expansion': range_expansion,
            'near_high': near_high,
            'near_low': near_low,
            'strong_bullish': strong_bullish,
            'strong_bearish': strong_bearish,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'ema_55': ema_55,
            'ema_144': ema_144,
            'pullback_to_ema9': pullback_to_ema9,
            'pullback_to_ema21': pullback_to_ema21,
            'atr': atr,
            'price_above_ema21': price_above_ema21,
            'price_below_ema21': price_below_ema21,
            'consecutive_bullish': consecutive_bullish,
            'consecutive_bearish': consecutive_bearish
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        HIGH ACCURACY LONG: Multiple confirmations required.
        
        MUST HAVE:
        1. Strong bullish trend (all EMAs aligned)
        2. Pullback to support (EMA9 or EMA21)
        3. Bullish candle confirmation
        4. Range expansion (volatility increasing)
        
        OPTIONAL:
        - Near recent low (better risk:reward)
        - Momentum acceleration positive
        """
        
        # CORE CONDITIONS (ALL required)
        trend_aligned = vars['strong_bullish']
        pullback = vars['pullback_to_ema9'] | vars['pullback_to_ema21']
        candle_confirm = vars['bullish_power'].rolling(2).max().astype(bool)  # Recent bullish power candle
        vol_confirm = vars['range_expansion'] | (vars['consecutive_bullish'] >= 2)
        
        # ENHANCEMENT CONDITIONS (at least 1)
        near_support = vars['near_low']
        mom_accel = vars['momentum_accel'] > 0
        above_ema = vars['price_above_ema21']
        
        # Combine: Core ALL must be true, plus at least 1 enhancement
        core_conditions = trend_aligned & pullback & candle_confirm & vol_confirm
        enhancement = near_support | mom_accel
        
        entry = core_conditions & enhancement
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        HIGH ACCURACY SHORT: Multiple confirmations required.
        """
        
        # CORE CONDITIONS (ALL required)
        trend_aligned = vars['strong_bearish']
        pullback = (df['high'] >= vars['ema_9']) & (df['close'] < vars['ema_9'])  # Pullback to EMA9 for shorts
        pullback_alt = (df['high'] >= vars['ema_21']) & (df['close'] < vars['ema_21'])
        pullback_final = pullback | pullback_alt
        candle_confirm = vars['bearish_power'].rolling(2).max().astype(bool)
        vol_confirm = vars['range_expansion'] | (vars['consecutive_bearish'] >= 2)
        
        # ENHANCEMENT CONDITIONS
        near_resistance = vars['near_high']
        mom_accel = vars['momentum_accel'] < 0
        below_ema = vars['price_below_ema21']
        
        core_conditions = trend_aligned & pullback_final & candle_confirm & vol_confirm
        enhancement = near_resistance | mom_accel
        
        entry = core_conditions & enhancement
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        1:1 RRR - Simple and effective for high accuracy strategy.
        """
        sl_distance = vars['atr'] * 1.5
        tp_distance = vars['atr'] * 1.5
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit on trend break or reversal candle."""
        trend_broken = vars['ema_9'] < vars['ema_21']
        reversal_candle = vars['bearish_power'] & vars['range_expansion']
        
        return (trend_broken | reversal_candle).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit on trend break or reversal candle."""
        trend_broken = vars['ema_9'] > vars['ema_21']
        reversal_candle = vars['bullish_power'] & vars['range_expansion']
        
        return (trend_broken | reversal_candle).fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Fallback exit."""
        idx = trade['current_idx']
        
        if trade['direction'] == 'long':
            if vars['ema_9'].iloc[idx] < vars['ema_21'].iloc[idx]:
                return True
        else:
            if vars['ema_9'].iloc[idx] > vars['ema_21'].iloc[idx]:
                return True
        
        return False