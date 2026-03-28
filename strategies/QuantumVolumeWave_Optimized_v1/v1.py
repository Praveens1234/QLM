from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class QuantumVolumeWave_Optimized_v1(Strategy):
    """
    Author: MCP Client (AI Agent)
    Description: OPTIMIZED Quantum Volume Wave - Best performer enhanced.
    
    ORIGINAL RESULTS:
    - Win Rate: 39.27% (BEST among all tested)
    - 17,440 trades
    - avg_win: 53.07, avg_loss: -85.02
    
    OPTIMIZATIONS:
    1. Tighter entry filters (quality over quantity)
    2. Better RRR (1:2 instead of 1:3)
    3. Improved exit logic
    4. Signal confirmation requirements
    
    TARGET: 45%+ win rate with positive expectancy
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate wave mechanics indicators with enhancements."""
        
        # ========== 1. WAVE AMPLITUDE (WA) ==========
        candle_direction = np.sign(df['close'] - df['open'])
        candle_magnitude = (df['close'] - df['open']).abs()
        wave_component = candle_direction * candle_magnitude
        wa = wave_component.ewm(span=5, adjust=False).mean()
        
        # ========== 2. WAVE PHASE (WP) ==========
        wa_max = wa.rolling(30).max()
        wa_min = wa.rolling(30).min()
        wa_range = wa_max - wa_min
        wp = (wa - wa_min) / (wa_range + 0.001)
        
        # More extreme thresholds
        oversold_wave = wp < 0.05  # More extreme
        overbought_wave = wp > 0.95  # More extreme
        
        # ========== 3. QUANTUM MOMENTUM (QM) ==========
        momentum = df['close'].diff(5)
        momentum_std = momentum.rolling(20).std()
        qm = momentum / (momentum_std + 0.001)
        
        qm_extreme_oversold = qm < -2.0
        qm_extreme_overbought = qm > 2.0
        
        # ========== 4. PRESSURE ACCUMULATOR (PA) ==========
        buyer_pressure = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.001)
        seller_pressure = (df['high'] - df['close']) / (df['high'] - df['low'] + 0.001)
        pa = (buyer_pressure - seller_pressure).rolling(10).sum()
        
        pa_extreme_low = pa < -5
        pa_extreme_high = pa > 5
        
        # ========== 5. DIRECTION CHANGE FREQUENCY ==========
        direction_change = (candle_direction != candle_direction.shift(1)).astype(int)
        wf = direction_change.rolling(20).sum()
        high_freq = wf > 12
        
        # ========== 6. STRUCTURAL CONFIRMATION ==========
        higher_high = df['high'] > df['high'].shift(1).rolling(5).max()
        lower_low = df['low'] < df['low'].shift(1).rolling(5).min()
        
        # ========== 7. TREND FILTER ==========
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        uptrend = ema_20 > ema_50
        downtrend = ema_20 < ema_50
        
        # ========== 8. ATR ==========
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # ========== 9. ENTRY CONFIRMATION ==========
        # Require price to be moving in expected direction
        price_moving_up = df['close'] > df['open']
        price_moving_down = df['close'] < df['open']
        
        # ========== 10. MULTI-TIMEFRAME MOMENTUM ==========
        roc_10 = df['close'].pct_change(10) * 100
        roc_30 = df['close'].pct_change(30) * 100
        
        return {
            'wa': wa,
            'wp': wp,
            'oversold_wave': oversold_wave,
            'overbought_wave': overbought_wave,
            'qm': qm,
            'qm_extreme_oversold': qm_extreme_oversold,
            'qm_extreme_overbought': qm_extreme_overbought,
            'pa': pa,
            'pa_extreme_low': pa_extreme_low,
            'pa_extreme_high': pa_extreme_high,
            'high_freq': high_freq,
            'higher_high': higher_high,
            'lower_low': lower_low,
            'uptrend': uptrend,
            'downtrend': downtrend,
            'atr': atr,
            'price_moving_up': price_moving_up,
            'price_moving_down': price_moving_down,
            'roc_10': roc_10,
            'roc_30': roc_30
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        OPTIMIZED LONG: Extreme oversold + Multiple confirmations.
        """
        
        # PRIMARY: Extreme oversold wave
        wave_bottom = vars['oversold_wave']
        
        # CONFIRMATION 1: Extreme negative momentum
        mom_confirm = vars['qm_extreme_oversold']
        
        # CONFIRMATION 2: Extreme selling pressure
        pressure_confirm = vars['pa_extreme_low']
        
        # CONFIRMATION 3: High frequency (oscillation)
        freq_confirm = vars['high_freq']
        
        # CONFIRMATION 4: Recent panic selling
        panic_confirm = vars['lower_low'].rolling(5).max().astype(bool)
        
        # CONFIRMATION 5: Price starting to turn
        turning = vars['price_moving_up'].rolling(2).max().astype(bool)
        
        # Require wave bottom + at least 3 confirmations
        confirmations = (
            mom_confirm.astype(int) +
            pressure_confirm.astype(int) +
            freq_confirm.astype(int) +
            panic_confirm.astype(int) +
            turning.astype(int)
        )
        
        entry = wave_bottom & (confirmations >= 3)
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        OPTIMIZED SHORT: Extreme overbought + Multiple confirmations.
        """
        
        wave_top = vars['overbought_wave']
        mom_confirm = vars['qm_extreme_overbought']
        pressure_confirm = vars['pa_extreme_high']
        freq_confirm = vars['high_freq']
        panic_confirm = vars['higher_high'].rolling(5).max().astype(bool)
        turning = vars['price_moving_down'].rolling(2).max().astype(bool)
        
        confirmations = (
            mom_confirm.astype(int) +
            pressure_confirm.astype(int) +
            freq_confirm.astype(int) +
            panic_confirm.astype(int) +
            turning.astype(int)
        )
        
        entry = wave_top & (confirmations >= 3)
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        1:2 RRR - Better balance for optimized strategy.
        """
        sl_distance = vars['atr'] * 1.5
        tp_distance = vars['atr'] * 3.0
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit at wave top or momentum reversal."""
        wave_top = vars['wp'] > 0.85
        momentum_reversal = vars['qm'] > 1.5
        profit_target = df['close'] > df['close'].shift(10) + vars['atr'] * 2
        
        return (wave_top | momentum_reversal | profit_target).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit at wave bottom or momentum reversal."""
        wave_bottom = vars['wp'] < 0.15
        momentum_reversal = vars['qm'] < -1.5
        profit_target = df['close'] < df['close'].shift(10) - vars['atr'] * 2
        
        return (wave_bottom | momentum_reversal | profit_target).fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Fallback exit."""
        idx = trade['current_idx']
        
        if trade['direction'] == 'long':
            if vars['wp'].iloc[idx] > 0.85:
                return True
            if vars['qm'].iloc[idx] > 1.5:
                return True
        else:
            if vars['wp'].iloc[idx] < 0.15:
                return True
            if vars['qm'].iloc[idx] < -1.5:
                return True
        
        return False