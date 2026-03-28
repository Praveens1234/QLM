from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class QuantumVolumeWave_HighAccuracy_v1(Strategy):
    """
    Author: MCP Client (AI Agent)
    Description: HIGH ACCURACY Quantum Wave - Focus on 70%+ win rate with 1:1 RRR.
    
    PREVIOUS RESULTS:
    - QuantumVolumeWave_Optimized_v1: 41.09% win rate
    - Need to push higher for 70%+ target
    
    APPROACH:
    - Even more selective entry conditions
    - Focus on high-probability reversals only
    - Use trend filter as additional confirmation
    - Require multiple extreme readings
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate indicators for high-accuracy entries."""
        
        # ========== 1. WAVE AMPLITUDE ==========
        candle_direction = np.sign(df['close'] - df['open'])
        candle_magnitude = (df['close'] - df['open']).abs()
        wave_component = candle_direction * candle_magnitude
        wa = wave_component.ewm(span=5, adjust=False).mean()
        
        # ========== 2. WAVE PHASE ==========
        wa_max = wa.rolling(50).max()  # Longer lookback
        wa_min = wa.rolling(50).min()
        wa_range = wa_max - wa_min
        wp = (wa - wa_min) / (wa_range + 0.001)
        
        # Extreme thresholds
        oversold_wave = wp < 0.02
        overbought_wave = wp > 0.98
        
        # ========== 3. MOMENTUM ==========
        momentum = df['close'].diff(5)
        momentum_std = momentum.rolling(30).std()
        qm = momentum / (momentum_std + 0.001)
        
        # Extreme readings
        qm_oversold = qm < -2.5
        qm_overbought = qm > 2.5
        
        # ========== 4. PRESSURE ==========
        buyer_pressure = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.001)
        seller_pressure = (df['high'] - df['close']) / (df['high'] - df['low'] + 0.001)
        pa = (buyer_pressure - seller_pressure).rolling(15).sum()
        
        pa_oversold = pa < -8
        pa_overbought = pa > 8
        
        # ========== 5. TREND ==========
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        ema_100 = df['close'].ewm(span=100, adjust=False).mean()
        
        strong_uptrend = (ema_20 > ema_50) & (ema_50 > ema_100)
        strong_downtrend = (ema_20 < ema_50) & (ema_50 < ema_100)
        
        # ========== 6. PRICE STRUCTURE ==========
        # Recent support/resistance
        support = df['low'].rolling(30).min()
        resistance = df['high'].rolling(30).max()
        
        near_support = df['close'] <= support * 1.005
        near_resistance = df['close'] >= resistance * 0.995
        
        # ========== 7. REVERSAL PATTERNS ==========
        # Candlestick reversal patterns
        hammer = (df['close'] > df['open']) & \
                 ((df['close'] - df['open']) < (df['high'] - df['low']) * 0.3) & \
                 ((df['open'] - df['low']) > (df['high'] - df['close']) * 2)
        
        shooting_star = (df['close'] < df['open']) & \
                        ((df['open'] - df['close']) < (df['high'] - df['low']) * 0.3) & \
                        ((df['high'] - df['open']) > (df['close'] - df['low']) * 2)
        
        # ========== 8. ATR ==========
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        return {
            'wp': wp,
            'oversold_wave': oversold_wave,
            'overbought_wave': overbought_wave,
            'qm': qm,
            'qm_oversold': qm_oversold,
            'qm_overbought': qm_overbought,
            'pa': pa,
            'pa_oversold': pa_oversold,
            'pa_overbought': pa_overbought,
            'strong_uptrend': strong_uptrend,
            'strong_downtrend': strong_downtrend,
            'near_support': near_support,
            'near_resistance': near_resistance,
            'hammer': hammer,
            'shooting_star': shooting_star,
            'atr': atr,
            'ema_20': ema_20,
            'ema_50': ema_50
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        HIGH ACCURACY LONG: All extremes must align.
        """
        
        # REQUIRED: Extreme oversold wave
        wave_extreme = vars['oversold_wave']
        
        # REQUIRED: Extreme negative momentum
        mom_extreme = vars['qm_oversold']
        
        # REQUIRED: Extreme selling pressure
        pressure_extreme = vars['pa_oversold']
        
        # OPTIONAL: Near support
        support_confirm = vars['near_support']
        
        # OPTIONAL: Reversal pattern
        pattern_confirm = vars['hammer'].rolling(3).max().astype(bool)
        
        # OPTIONAL: Price turning up
        turning = (df['close'] > df['open']) & (df['close'] > df['close'].shift(2))
        
        # ALL extremes + at least 1 optional
        extremes = wave_extreme & mom_extreme & pressure_extreme
        optional = support_confirm | pattern_confirm | turning
        
        entry = extremes & optional
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        HIGH ACCURACY SHORT: All extremes must align.
        """
        
        wave_extreme = vars['overbought_wave']
        mom_extreme = vars['qm_overbought']
        pressure_extreme = vars['pa_overbought']
        resistance_confirm = vars['near_resistance']
        pattern_confirm = vars['shooting_star'].rolling(3).max().astype(bool)
        turning = (df['close'] < df['open']) & (df['close'] < df['close'].shift(2))
        
        extremes = wave_extreme & mom_extreme & pressure_extreme
        optional = resistance_confirm | pattern_confirm | turning
        
        entry = extremes & optional
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        1:1 RRR for high accuracy strategy.
        """
        sl_distance = vars['atr'] * 1.5
        tp_distance = vars['atr'] * 1.5
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit when wave reverses significantly."""
        wave_reversal = vars['wp'] > 0.5
        momentum_shift = vars['qm'] > 1.0
        
        return (wave_reversal | momentum_shift).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit when wave reverses significantly."""
        wave_reversal = vars['wp'] < 0.5
        momentum_shift = vars['qm'] < -1.0
        
        return (wave_reversal | momentum_shift).fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Fallback exit."""
        idx = trade['current_idx']
        
        if trade['direction'] == 'long':
            if vars['wp'].iloc[idx] > 0.5:
                return True
        else:
            if vars['wp'].iloc[idx] < 0.5:
                return True
        
        return False