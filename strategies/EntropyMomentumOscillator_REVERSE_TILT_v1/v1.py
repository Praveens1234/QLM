from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class EntropyMomentumOscillator_REVERSE_TILT_v1(Strategy):
    """
    Author: MCP Client (AI Agent)
    Description: REVERSE TILT version - Tests counter-intuitive signal logic.
    
    DISCOVERY FROM ORIGINAL:
    - Original had 18% win rate (bullish signals = bearish reality)
    - Simple inversion still lost (21% win rate)
    - Hypothesis: The signals are asymmetrically wrong
    
    NEW APPROACH: REVERSE TILT
    - If original bullish momentum signals were consistently WRONG,
      then bearish momentum should predict LONG entries
    - This creates a "contrarian momentum" strategy
    - Trade AGAINST the momentum phase shift direction
    
    RISK MODEL:
    - Fixed 1:1 RRR for simplicity
    - Test with tighter stops for quick scalping
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate indicators - FOCUS ON CONTRARIAN SIGNALS."""
        
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
        
        # ========== 4. HIGH ENTROPY REGIME (CHAOS) ==========
        # INVERTED: Now we look for HIGH entropy (chaotic) regime
        # Because original low-entropy signals failed
        entropy_threshold_high = pei.rolling(100).quantile(0.7)
        high_entropy_regime = pei > entropy_threshold_high
        
        # Also test low entropy for comparison
        entropy_threshold_low = pei.rolling(100).quantile(0.3)
        low_entropy_regime = pei < entropy_threshold_low
        
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
        
        # ========== 7. CONTRARIAN SIGNALS ==========
        # Original bullish momentum led to losses, so contrarian:
        # When MPS shows strong bullish, we expect reversal = SHORT
        # When MPS shows strong bearish, we expect reversal = LONG
        
        return {
            'pei': pei,
            'mps': mps,
            'cfi': cfi,
            'high_entropy_regime': high_entropy_regime,
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
        CONTRARIAN LONG: Enter when momentum is BEARISH (expect reversal).
        
        Logic: Original strategy said "long when bullish momentum"
        and that failed consistently. So we do the opposite.
        """
        # Trade in HIGH entropy regime (chaos = mean reversion opportunity)
        in_chaotic_regime = vars['high_entropy_regime']
        
        # CONTRARIAN: Strong bearish momentum = expect reversal up
        mps_oversold = vars['mps'] < -1.5
        
        # Candles showing selling pressure = contrarian buy signal
        cfi_oversold = vars['cfi'] < -20
        
        # Counter-trend: Original trend-following failed, try counter-trend
        counter_trend = vars['bearish_trend']  # Buy in downtrend (contrarian)
        
        # PEI declining = regime becoming more ordered (good for mean reversion)
        pei_declining = vars['pei'] < vars['pei'].shift(3)
        
        # Price near recent low (mean reversion setup)
        near_low = df['close'] < df['low'].rolling(10).min().shift(1) + vars['atr'] * 0.5
        
        signal_count = (
            mps_oversold.astype(int) +
            cfi_oversold.astype(int) +
            counter_trend.astype(int) +
            pei_declining.astype(int) +
            near_low.astype(int)
        )
        
        entry = (signal_count >= 2)  # More relaxed conditions
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        CONTRARIAN SHORT: Enter when momentum is BULLISH (expect reversal).
        """
        in_chaotic_regime = vars['high_entropy_regime']
        
        # CONTRARIAN: Strong bullish momentum = expect reversal down
        mps_overbought = vars['mps'] > 1.5
        
        # Candles showing buying pressure = contrarian sell signal
        cfi_overbought = vars['cfi'] > 20
        
        # Counter-trend
        counter_trend = vars['bullish_trend']  # Sell in uptrend (contrarian)
        
        pei_declining = vars['pei'] < vars['pei'].shift(3)
        
        # Price near recent high (mean reversion setup)
        near_high = df['close'] > df['high'].rolling(10).max().shift(1) - vars['atr'] * 0.5
        
        signal_count = (
            mps_overbought.astype(int) +
            cfi_overbought.astype(int) +
            counter_trend.astype(int) +
            pei_declining.astype(int) +
            near_high.astype(int)
        )
        
        entry = (signal_count >= 2)
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        TIGHT 1:1 RRR for mean reversion scalping.
        """
        sl_distance = vars['atr'] * 1.0
        tp_distance = vars['atr'] * 1.0
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit when momentum reverses back."""
        mps_reversal = vars['mps'] > 0.5  # Momentum turned bullish
        profit_target = df['close'] > df['close'].shift(5) + vars['atr'] * 0.5
        
        return (mps_reversal | profit_target).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit when momentum reverses back."""
        mps_reversal = vars['mps'] < -0.5  # Momentum turned bearish
        profit_target = df['close'] < df['close'].shift(5) - vars['atr'] * 0.5
        
        return (mps_reversal | profit_target).fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Fallback exit logic."""
        idx = trade['current_idx']
        
        if trade['direction'] == 'long':
            if vars['mps'].iloc[idx] > 0.5:
                return True
        else:
            if vars['mps'].iloc[idx] < -0.5:
                return True
        
        return False