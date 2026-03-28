from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class EntropyMomentumOscillator_INVERTED(Strategy):
    """
    Author: MCP Client (AI Agent)
    Description: INVERTED version of Entropy Momentum Oscillator Strategy.
    
    INVERSION LOGIC:
    - Original strategy had 18% win rate (anti-pattern detected!)
    - This version FLIPS all signals:
      - Original Long becomes This Short
      - Original Short becomes This Long
    - SL and TP distances are SWAPPED (RRR inverted)
    
    EXPECTED OUTCOME:
    - Win rate should flip to ~82% (100% - 18%)
    - With 1:1 RRR, this should be profitable
    
    NOVEL INDICATORS (same as original):
    - Price Entropy Index (PEI)
    - Momentum Phase Shift (MPS)
    - Candle Flow Imbalance (CFI)
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate novel entropy-based indicators (same as original)."""
        
        # ========== 1. PRICE ENTROPY INDEX (PEI) ==========
        price_change = df['close'].diff()
        entropy_window = 20
        
        rolling_std = price_change.rolling(entropy_window).std()
        rolling_range = df['high'].rolling(entropy_window).max() - df['low'].rolling(entropy_window).min()
        
        pei = (rolling_std / (rolling_range + 0.001)) * 10
        pei = pei.fillna(5.0)
        
        # ========== 2. MOMENTUM PHASE SHIFT (MPS) ==========
        momentum = df['close'].pct_change(periods=5) * 100
        momentum_sma = momentum.rolling(14).mean()
        momentum_std = momentum.rolling(14).std()
        
        mps = (momentum - momentum_sma) / (momentum_std + 0.001)
        mps = mps.fillna(0)
        
        # ========== 3. CANDLE FLOW IMBALANCE (CFI) ==========
        candle_body = df['close'] - df['open']
        candle_range = df['high'] - df['low']
        body_ratio = candle_body / (candle_range + 0.001)
        
        upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
        lower_wick = df[['open', 'close']].min(axis=1) - df['low']
        wick_imbalance = (lower_wick - upper_wick) / (candle_range + 0.001)
        
        cfi = (body_ratio * 0.6 + wick_imbalance * 0.4) * 100
        cfi = cfi.rolling(3).mean().fillna(0)
        
        # ========== 4. ENTROPY REGIME FILTER ==========
        entropy_threshold = pei.rolling(100).quantile(0.3)
        low_entropy_regime = pei < entropy_threshold
        
        # ========== 5. TREND CONTEXT ==========
        ema_9 = df['close'].ewm(span=9, adjust=False).mean()
        ema_21 = df['close'].ewm(span=21, adjust=False).mean()
        ema_55 = df['close'].ewm(span=55, adjust=False).mean()
        
        bullish_trend = (ema_9 > ema_21) & (ema_21 > ema_55)
        bearish_trend = (ema_9 < ema_21) & (ema_21 < ema_55)
        
        # ========== 6. ATR ==========
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        return {
            'pei': pei,
            'mps': mps,
            'cfi': cfi,
            'low_entropy_regime': low_entropy_regime,
            'bullish_trend': bullish_trend,
            'bearish_trend': bearish_trend,
            'atr': atr,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'ema_55': ema_55
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        INVERTED Long Entry: Uses ORIGINAL SHORT conditions.
        Original short had consistent losers, now they become winners.
        """
        in_ordered_regime = vars['low_entropy_regime']
        mps_bearish = vars['mps'] < -0.5
        cfi_bearish = vars['cfi'] < -10
        trend_aligned = vars['bearish_trend']
        pei_declining = vars['pei'] < vars['pei'].shift(3)
        
        signal_count = (
            in_ordered_regime.astype(int) +
            mps_bearish.astype(int) +
            cfi_bearish.astype(int) +
            trend_aligned.astype(int) +
            pei_declining.astype(int)
        )
        
        entry = (signal_count >= 3) & in_ordered_regime
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        INVERTED Short Entry: Uses ORIGINAL LONG conditions.
        Original long had consistent losers, now they become winners.
        """
        in_ordered_regime = vars['low_entropy_regime']
        mps_bullish = vars['mps'] > 0.5
        cfi_bullish = vars['cfi'] > 10
        trend_aligned = vars['bullish_trend']
        pei_declining = vars['pei'] < vars['pei'].shift(3)
        
        signal_count = (
            in_ordered_regime.astype(int) +
            mps_bullish.astype(int) +
            cfi_bullish.astype(int) +
            trend_aligned.astype(int) +
            pei_declining.astype(int)
        )
        
        entry = (signal_count >= 3) & in_ordered_regime
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        INVERTED Risk Model: 1:1 RRR for high accuracy strategy.
        Expected win rate ~82% with 1:1 RRR should be profitable.
        """
        sl_distance = vars['atr'] * 2.0
        tp_distance = vars['atr'] * 2.0
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        INVERTED: Use original short exit conditions for long exits.
        """
        entropy_rising = vars['pei'] > vars['pei'].shift(5)
        mps_bullish_shift = vars['mps'] > 1.0
        trend_broken = vars['ema_9'] > vars['ema_21']
        
        exit_signal = entropy_rising | mps_bullish_shift | trend_broken
        
        return exit_signal.fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        INVERTED: Use original long exit conditions for short exits.
        """
        entropy_rising = vars['pei'] > vars['pei'].shift(5)
        mps_bearish_shift = vars['mps'] < -1.0
        trend_broken = vars['ema_9'] < vars['ema_21']
        
        exit_signal = entropy_rising | mps_bearish_shift | trend_broken
        
        return exit_signal.fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Mandatory exit method with INVERTED logic.
        """
        idx = trade['current_idx']
        
        if trade['direction'] == 'long':
            if vars['pei'].iloc[idx] > vars['pei'].iloc[idx-5]:
                return True
            if vars['mps'].iloc[idx] > 1.0:
                return True
            if vars['ema_9'].iloc[idx] > vars['ema_21'].iloc[idx]:
                return True
        else:
            if vars['pei'].iloc[idx] > vars['pei'].iloc[idx-5]:
                return True
            if vars['mps'].iloc[idx] < -1.0:
                return True
            if vars['ema_9'].iloc[idx] < vars['ema_21'].iloc[idx]:
                return True
        
        return False