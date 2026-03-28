from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class QuantumVolumeWave_v1(Strategy):
    """
    Author: MCP Client (AI Agent)
    Description: QUANTUM VOLUME WAVE - A completely novel approach using wave mechanics.
    
    BREAKTHROUGH INSIGHT:
    Previous strategies failed because:
    1. Too many signals (noise)
    2. Entry timing was wrong
    3. Not accounting for market microstructure
    
    NEW DISCOVERY - VOLUME WAVE THEORY:
    - Markets move in waves of buying/selling pressure
    - These waves can be detected using candle analysis
    - When wave peaks, reversal is likely
    - Trade AGAINST the wave at extremes
    
    NOVEL INDICATORS:
    1. Wave Amplitude: Measures the strength of directional pressure
    2. Wave Frequency: How often direction changes
    3. Wave Phase: Where are we in the wave cycle?
    4. Quantum Momentum: Momentum that respects wave boundaries
    
    ENTRY LOGIC:
    - Buy when wave amplitude is NEGATIVE peak (oversold wave)
    - Sell when wave amplitude is POSITIVE peak (overbought wave)
    
    RISK MODEL:
    - 1:3 RRR (tight stops, wide targets)
    - Trade less, win more
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate wave mechanics indicators."""
        
        # ========== 1. WAVE AMPLITUDE (WA) ==========
        # Measures cumulative directional pressure
        candle_direction = np.sign(df['close'] - df['open'])
        candle_magnitude = (df['close'] - df['open']).abs()
        
        # Cumulative wave: sum of recent directional moves
        wave_component = candle_direction * candle_magnitude
        
        # Wave amplitude using exponential smoothing
        wa = wave_component.ewm(span=5, adjust=False).mean()
        wa_normalized = wa / df['close'].rolling(50).std()  # Normalize by volatility
        
        # ========== 2. WAVE FREQUENCY (WF) ==========
        # How often does direction change?
        direction_change = (candle_direction != candle_direction.shift(1)).astype(int)
        wf = direction_change.rolling(20).sum()  # Count of direction changes
        
        # High frequency = oscillation (range), Low frequency = trending
        high_freq = wf > 12  # More than 12 changes = ranging
        low_freq = wf < 8   # Less than 8 changes = trending
        
        # ========== 3. WAVE PHASE (WP) ==========
        # Where are we in the wave cycle?
        wa_max = wa.rolling(30).max()
        wa_min = wa.rolling(30).min()
        wa_range = wa_max - wa_min
        
        # Phase: 0 = bottom, 1 = top
        wp = (wa - wa_min) / (wa_range + 0.001)
        
        # Extreme phases
        oversold_wave = wp < 0.1   # Wave at bottom
        overbought_wave = wp > 0.9  # Wave at top
        
        # ========== 4. QUANTUM MOMENTUM (QM) ==========
        # Momentum that accounts for wave structure
        momentum = df['close'].diff(5)
        momentum_std = momentum.rolling(20).std()
        
        # Z-score of momentum
        qm = momentum / (momentum_std + 0.001)
        
        # ========== 5. PRESSURE ACCUMULATOR (PA) ==========
        # Cumulative buying/selling pressure
        buyer_pressure = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.001)
        seller_pressure = (df['high'] - df['close']) / (df['high'] - df['low'] + 0.001)
        
        pa = (buyer_pressure - seller_pressure).rolling(10).sum()
        
        # ========== 6. STRUCTURAL BREAKS ==========
        # Detect when structure changes
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
        LONG ENTRY: Wave at oversold extreme + positive pressure accumulation.
        
        Theory: When wave amplitude reaches extreme negative, 
        the market is oversold and due for reversal.
        """
        
        # PRIMARY: Wave at oversold extreme
        wave_bottom = vars['oversold_wave']
        
        # CONFIRMATION 1: Pressure accumulator turning positive
        pressure_turning = (vars['pa'] > vars['pa'].shift(3)) & (vars['pa'] < 0)
        
        # CONFIRMATION 2: Recent lower low (panic selling)
        panic_low = vars['lower_low'].rolling(3).max().astype(bool)
        
        # CONFIRMATION 3: High frequency (oscillation = mean reversion)
        oscillation = vars['high_freq']
        
        # CONFIRMATION 4: Quantum momentum at extreme
        qm_oversold = vars['qm'] < -1.5
        
        # Combine: Wave bottom + at least 2 confirmations
        confirmations = (
            pressure_turning.astype(int) +
            panic_low.astype(int) +
            oscillation.astype(int) +
            qm_oversold.astype(int)
        )
        
        entry = wave_bottom & (confirmations >= 2)
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        SHORT ENTRY: Wave at overbought extreme + negative pressure accumulation.
        """
        
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
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        1:3 RRR - Tight stops, wide targets for wave reversals.
        """
        sl_distance = vars['atr'] * 1.0
        tp_distance = vars['atr'] * 3.0
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit when wave reaches top or momentum exhausts."""
        wave_top = vars['wp'] > 0.8
        momentum_exhausted = vars['qm'] > 1.0
        
        return (wave_top | momentum_exhausted).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit when wave reaches bottom or momentum exhausts."""
        wave_bottom = vars['wp'] < 0.2
        momentum_exhausted = vars['qm'] < -1.0
        
        return (wave_bottom | momentum_exhausted).fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Fallback exit."""
        idx = trade['current_idx']
        
        if trade['direction'] == 'long':
            if vars['wp'].iloc[idx] > 0.8:
                return True
            if vars['qm'].iloc[idx] > 1.0:
                return True
        else:
            if vars['wp'].iloc[idx] < 0.2:
                return True
            if vars['qm'].iloc[idx] < -1.0:
                return True
        
        return False