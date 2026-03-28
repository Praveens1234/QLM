from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class QuantumVolumeWave_INVERTED_v1(Strategy):
    """
    Author: MCP Client (AI Agent)
    Description: INVERTED version of Quantum Volume Wave strategy.
    
    ORIGINAL RESULTS:
    - Win Rate: 39.27%
    - 17,440 trades
    - avg_win: 53.07, avg_loss: -85.02
    
    INVERSION APPROACH:
    - Original was closer to 50% win rate
    - Inverting should push us to ~61% win rate
    - Using 1:1 RRR for high accuracy
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate wave mechanics indicators (same as original)."""
        
        # ========== 1. WAVE AMPLITUDE (WA) ==========
        candle_direction = np.sign(df['close'] - df['open'])
        candle_magnitude = (df['close'] - df['open']).abs()
        wave_component = candle_direction * candle_magnitude
        wa = wave_component.ewm(span=5, adjust=False).mean()
        wa_normalized = wa / df['close'].rolling(50).std()
        
        # ========== 2. WAVE FREQUENCY (WF) ==========
        direction_change = (candle_direction != candle_direction.shift(1)).astype(int)
        wf = direction_change.rolling(20).sum()
        high_freq = wf > 12
        low_freq = wf < 8
        
        # ========== 3. WAVE PHASE (WP) ==========
        wa_max = wa.rolling(30).max()
        wa_min = wa.rolling(30).min()
        wa_range = wa_max - wa_min
        wp = (wa - wa_min) / (wa_range + 0.001)
        
        oversold_wave = wp < 0.1
        overbought_wave = wp > 0.9
        
        # ========== 4. QUANTUM MOMENTUM (QM) ==========
        momentum = df['close'].diff(5)
        momentum_std = momentum.rolling(20).std()
        qm = momentum / (momentum_std + 0.001)
        
        # ========== 5. PRESSURE ACCUMULATOR (PA) ==========
        buyer_pressure = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.001)
        seller_pressure = (df['high'] - df['close']) / (df['high'] - df['low'] + 0.001)
        pa = (buyer_pressure - seller_pressure).rolling(10).sum()
        
        # ========== 6. STRUCTURAL BREAKS ==========
        higher_high = df['high'] > df['high'].shift(1).rolling(5).max()
        lower_low = df['low'] < df['low'].shift(1).rolling(5).min()
        
        # ========== 7. ATR ==========
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        return {
            'wa': wa,
            'wa_normalized': wa_normalized,
            'wf': wf,
            'wp': wp,
            'oversold_wave': oversold_wave,
            'overbought_wave': overbought_wave,
            'high_freq': high_freq,
            'low_freq': low_freq,
            'qm': qm,
            'pa': pa,
            'higher_high': higher_high,
            'lower_low': lower_low,
            'atr': atr,
            'buyer_pressure': buyer_pressure,
            'seller_pressure': seller_pressure
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        INVERTED: Use original SHORT conditions for LONG.
        """
        
        # Original short conditions
        wave_top = vars['overbought_wave']
        pressure_turning = (vars['pa'] < vars['pa'].shift(3)) & (vars['pa'] > 0)
        panic_high = vars['higher_high'].rolling(3).max().astype(bool)
        oscillation = vars['high_freq']
        qm_overbought = vars['qm'] > 1.5
        
        confirmations = (
            pressure_turning.astype(int) +
            panic_high.astype(int) +
            oscillation.astype(int) +
            qm_overbought.astype(int)
        )
        
        entry = wave_top & (confirmations >= 2)
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        INVERTED: Use original LONG conditions for SHORT.
        """
        
        wave_bottom = vars['oversold_wave']
        pressure_turning = (vars['pa'] > vars['pa'].shift(3)) & (vars['pa'] < 0)
        panic_low = vars['lower_low'].rolling(3).max().astype(bool)
        oscillation = vars['high_freq']
        qm_oversold = vars['qm'] < -1.5
        
        confirmations = (
            pressure_turning.astype(int) +
            panic_low.astype(int) +
            oscillation.astype(int) +
            qm_oversold.astype(int)
        )
        
        entry = wave_bottom & (confirmations >= 2)
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        1:1 RRR for inverted strategy.
        """
        sl_distance = vars['atr'] * 2.0
        tp_distance = vars['atr'] * 2.0
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """INVERTED: Use original short exit for long."""
        wave_bottom = vars['wp'] < 0.2
        momentum_exhausted = vars['qm'] < -1.0
        
        return (wave_bottom | momentum_exhausted).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """INVERTED: Use original long exit for short."""
        wave_top = vars['wp'] > 0.8
        momentum_exhausted = vars['qm'] > 1.0
        
        return (wave_top | momentum_exhausted).fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Fallback exit."""
        idx = trade['current_idx']
        
        if trade['direction'] == 'long':
            if vars['wp'].iloc[idx] < 0.2:
                return True
            if vars['qm'].iloc[idx] < -1.0:
                return True
        else:
            if vars['wp'].iloc[idx] > 0.8:
                return True
            if vars['qm'].iloc[idx] > 1.0:
                return True
        
        return False