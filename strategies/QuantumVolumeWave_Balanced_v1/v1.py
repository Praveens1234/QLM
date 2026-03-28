from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class QuantumVolumeWave_Balanced_v1(Strategy):
    """
    Author: MCP Client (AI Agent)
    Description: BALANCED Quantum Wave - Optimal trade-off between quality and quantity.
    
    DISCOVERY PATH:
    - v1: 39.27% win rate, 17,440 trades
    - Optimized: 41.09% win rate, 4,162 trades
    - HighAccuracy: 37.5% win rate, 24 trades (too selective)
    
    BALANCED APPROACH:
    - Moderate selectivity for 50-100 trades/day
    - Target 40-45% win rate with 1:2 RRR
    - Use moderate extreme thresholds
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate balanced indicators."""
        
        # ========== 1. WAVE AMPLITUDE ==========
        candle_direction = np.sign(df['close'] - df['open'])
        candle_magnitude = (df['close'] - df['open']).abs()
        wave_component = candle_direction * candle_magnitude
        wa = wave_component.ewm(span=5, adjust=False).mean()
        
        # ========== 2. WAVE PHASE ==========
        wa_max = wa.rolling(40).max()
        wa_min = wa.rolling(40).min()
        wa_range = wa_max - wa_min
        wp = (wa - wa_min) / (wa_range + 0.001)
        
        # Moderate extremes
        oversold_wave = wp < 0.08
        overbought_wave = wp > 0.92
        
        # ========== 3. MOMENTUM ==========
        momentum = df['close'].diff(5)
        momentum_std = momentum.rolling(25).std()
        qm = momentum / (momentum_std + 0.001)
        
        qm_oversold = qm < -2.0
        qm_overbought = qm > 2.0
        
        # ========== 4. PRESSURE ==========
        buyer_pressure = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.001)
        seller_pressure = (df['high'] - df['close']) / (df['high'] - df['low'] + 0.001)
        pa = (buyer_pressure - seller_pressure).rolling(12).sum()
        
        pa_oversold = pa < -6
        pa_overbought = pa > 6
        
        # ========== 5. VOLATILITY ==========
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # ========== 6. DIRECTION ==========
        bull_candle = df['close'] > df['open']
        bear_candle = df['close'] < df['open']
        
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
            'atr': atr,
            'bull_candle': bull_candle,
            'bear_candle': bear_candle
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Balanced long entry."""
        
        wave_cond = vars['oversold_wave']
        mom_cond = vars['qm_oversold']
        pressure_cond = vars['pa_oversold']
        
        # Need wave extreme + (momentum OR pressure)
        entry = wave_cond & (mom_cond | pressure_cond)
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Balanced short entry."""
        
        wave_cond = vars['overbought_wave']
        mom_cond = vars['qm_overbought']
        pressure_cond = vars['pa_overbought']
        
        entry = wave_cond & (mom_cond | pressure_cond)
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """1:2 RRR for balanced approach."""
        sl_distance = vars['atr'] * 1.5
        tp_distance = vars['atr'] * 3.0
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        return (vars['wp'] > 0.6).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        return (vars['wp'] < 0.4).fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        idx = trade['current_idx']
        if trade['direction'] == 'long':
            return vars['wp'].iloc[idx] > 0.6
        else:
            return vars['wp'].iloc[idx] < 0.4