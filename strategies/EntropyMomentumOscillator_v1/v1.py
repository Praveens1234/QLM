from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class EntropyMomentumOscillator_v1(Strategy):
    """
    Author: MCP Client AI
    Description: Novel Entropy Momentum Oscillator (EMO) Strategy - First of its kind!
    
    Novel Indicators Invented:
    1. Price Entropy Index (PEI) - Shannon entropy of normalized returns
    2. Phase Coherence (PC) - Measures synchronization in price movements
    3. Entropy Flux (EF) - Rate of entropy change (entropy gradient)
    4. Entropy Momentum (EM) - Momentum weighted by entropy regime
    
    Core Hypothesis:
    - Low entropy + High coherence = Strong trend continuation signal
    - High entropy + Low coherence = Range-bound/mean-reversion opportunity
    - Entropy flux spike = Imminent regime change (potential reversal)
    
    Entry Logic:
    - Long: PEI < threshold (ordered market) + Positive EM + High PC
    - Short: PEI < threshold (ordered market) + Negative EM + High PC
    
    Risk Management: Dynamic ATR-based with 1:2 RRR
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all entropy-based indicators using vectorized operations."""
        
        close = df['close']
        high = df['high']
        low = df['low']
        
        # ============================================
        # 1. RETURNS & NORMALIZED RETURNS
        # ============================================
        # Log returns for entropy calculation
        log_returns = np.log(close / close.shift(1))
        
        # Normalize returns to [-1, 1] range for entropy
        rolling_std_20 = log_returns.rolling(20).std()
        normalized_returns = log_returns / (rolling_std_20 + 1e-10)
        normalized_returns = normalized_returns.clip(-3, 3) / 3  # Clip extreme values
        
        # ============================================
        # 2. PRICE ENTROPY INDEX (PEI)
        # ============================================
        # Shannon entropy of discretized returns
        # Bin returns into 10 bins and calculate entropy
        def calc_entropy(series):
            if len(series) < 2 or series.isna().all():
                return 0.5  # Neutral entropy
            # Discretize into bins
            bins = np.linspace(-1, 1, 11)
            digitized = np.digitize(series.dropna().values, bins)
            digitized = np.clip(digitized, 0, 9)
            
            # Calculate probability distribution
            counts = np.bincount(digitized, minlength=10)
            probs = counts / (counts.sum() + 1e-10)
            
            # Shannon entropy (normalized to [0, 1])
            probs = probs[probs > 0]
            entropy = -np.sum(probs * np.log2(probs + 1e-10))
            return entropy / np.log2(10)  # Normalize to [0, 1]
        
        # Rolling entropy calculation (optimized)
        pei = normalized_returns.rolling(30).apply(
            lambda x: calc_entropy(x), 
            raw=False
        ).fillna(0.5)
        
        # ============================================
        # 3. PHASE COHERENCE (PC)
        # ============================================
        # Measures how synchronized price movements are
        # High coherence = most bars move in same direction
        direction = np.sign(close.diff())
        
        # Coherence = |sum of directions| / count (how aligned are movements?)
        coherence_sum = direction.rolling(15).sum()
        coherence_count = direction.rolling(15).count()
        pc = (coherence_sum.abs() / (coherence_count + 1e-10)).fillna(0)
        
        # ============================================
        # 4. ENTROPY FLUX (EF)
        # ============================================
        # Rate of entropy change - detects regime shifts
        entropy_flux = pei.diff(5).abs().fillna(0)
        
        # Normalized entropy flux
        ef = entropy_flux / (entropy_flux.rolling(50).mean() + 1e-10)
        ef = ef.clip(0, 5).fillna(1)
        
        # ============================================
        # 5. ENTROPY MOMENTUM (EM)
        # ============================================
        # Traditional momentum weighted by inverse entropy
        # When entropy is low (ordered), momentum signals are stronger
        raw_momentum = close.pct_change(10)
        entropy_weight = (1 - pei) ** 2  # Quadratic penalty on high entropy
        em = raw_momentum * entropy_weight * 100  # Scale for interpretability
        em = em.fillna(0)
        
        # ============================================
        # 6. MAGNETIC ZONE DETECTOR
        # ============================================
        # Identifies price levels that attract price (support/resistance zones)
        # Uses kernel density estimation concept
        
        # Pivot highs and lows
        pivot_high = high.rolling(5, center=True).max()
        pivot_low = low.rolling(5, center=True).min()
        
        # Distance to nearest pivot
        dist_to_high = (close - pivot_high) / (close + 1e-10)
        dist_to_low = (close - pivot_low) / (close + 1e-10)
        
        # Magnetic strength (how strongly price is attracted to levels)
        magnetic_high = (dist_to_high.abs() < 0.002).astype(float)
        magnetic_low = (dist_to_low.abs() < 0.002).astype(float)
        
        # ============================================
        # 7. ATR for Dynamic Risk Management
        # ============================================
        tr = pd.DataFrame({
            'h_l': high - low,
            'h_pc': (high - close.shift(1)).abs(),
            'l_pc': (low - close.shift(1)).abs()
        }).max(axis=1)
        
        atr_14 = tr.rolling(14).mean().fillna(tr.mean())
        
        # ============================================
        # 8. TREND FILTER (Multi-timeframe perspective)
        # ============================================
        ema_20 = close.ewm(span=20).mean()
        ema_50 = close.ewm(span=50).mean()
        ema_100 = close.ewm(span=100).mean()
        
        trend_alignment = (
            (close > ema_20) & (ema_20 > ema_50) & (ema_50 > ema_100)
        ).astype(float) - (
            (close < ema_20) & (ema_20 < ema_50) & (ema_50 < ema_100)
        ).astype(float)
        
        return {
            'pei': pei,                          # Price Entropy Index [0, 1]
            'pc': pc,                            # Phase Coherence [0, 1]
            'ef': ef,                            # Entropy Flux (normalized)
            'em': em,                            # Entropy Momentum
            'atr_14': atr_14,                    # ATR for risk management
            'trend_alignment': trend_alignment,  # Multi-EMA alignment [-1, 0, 1]
            'magnetic_high': magnetic_high,      # Near pivot high
            'magnetic_low': magnetic_low,        # Near pivot low
            'ema_20': ema_20,
            'ema_50': ema_50
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Entropy-based Long Entry:
        
        Core Signal: Low entropy (ordered market) + positive entropy momentum
        
        Conditions:
        1. PEI < 0.6 (market is ordered, not chaotic)
        2. EM > 0.5 (positive momentum weighted by entropy)
        3. PC > 0.3 (some coherence in price movements)
        4. EF < 2 (no major regime shift happening)
        5. Price above EMA20 (short-term trend up)
        
        This captures: "Ordered uptrend continuation"
        """
        
        conditions = (
            (vars['pei'] < 0.6) &           # Ordered market (not chaotic)
            (vars['em'] > 0.5) &            # Positive entropy-weighted momentum
            (vars['pc'] > 0.3) &            # Some phase coherence
            (vars['ef'] < 2.0) &            # Stable regime (no entropy spike)
            (df['close'] > vars['ema_20'])  # Above short-term EMA
        )
        
        return conditions.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Entropy-based Short Entry:
        
        Core Signal: Low entropy (ordered market) + negative entropy momentum
        
        Conditions:
        1. PEI < 0.6 (market is ordered, not chaotic)
        2. EM < -0.5 (negative momentum weighted by entropy)
        3. PC > 0.3 (some coherence in price movements)
        4. EF < 2 (no major regime shift happening)
        5. Price below EMA20 (short-term trend down)
        
        This captures: "Ordered downtrend continuation"
        """
        
        conditions = (
            (vars['pei'] < 0.6) &           # Ordered market (not chaotic)
            (vars['em'] < -0.5) &           # Negative entropy-weighted momentum
            (vars['pc'] > 0.3) &            # Some phase coherence
            (vars['ef'] < 2.0) &            # Stable regime (no entropy spike)
            (df['close'] < vars['ema_20'])  # Below short-term EMA
        )
        
        return conditions.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        Dynamic Risk Model:
        
        Stop Loss: 1.5x ATR from entry
        Take Profit: 3.0x ATR from entry (1:2 RRR)
        
        Entropy-adjusted: In higher entropy periods, use wider stops
        """
        
        # Base distances
        sl_distance = vars['atr_14'] * 1.5
        tp_distance = vars['atr_14'] * 3.0
        
        # Adjust for entropy (high entropy = wider stops)
        entropy_factor = 1 + (vars['pei'] * 0.5)  # 1.0 to 1.5 multiplier
        
        return {
            'sl_distance': sl_distance * entropy_factor,
            'tp_distance': tp_distance * entropy_factor
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Vectorized Long Exit:
        
        Exit when:
        1. Entropy spikes (regime change detected)
        2. Entropy momentum reverses strongly
        3. Price drops below EMA50 (trend weakening)
        """
        
        exit_conditions = (
            (vars['ef'] > 3.0) |                    # Major entropy flux (regime change)
            (vars['em'] < -1.5) |                   # Strong negative momentum reversal
            (df['close'] < vars['ema_50'])          # Below medium-term EMA
        )
        
        return exit_conditions.fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        Vectorized Short Exit:
        
        Exit when:
        1. Entropy spikes (regime change detected)
        2. Entropy momentum reverses strongly
        3. Price rises above EMA50 (trend weakening)
        """
        
        exit_conditions = (
            (vars['ef'] > 3.0) |                    # Major entropy flux (regime change)
            (vars['em'] > 1.5) |                    # Strong positive momentum reversal
            (df['close'] > vars['ema_50'])          # Above medium-term EMA
        )
        
        return exit_conditions.fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """
        Dynamic exit fallback (slow mode) - uses vectorized signals above.
        """
        idx = trade['current_idx']
        
        # Use the pre-computed exit signals
        if trade['direction'] == 'long':
            return bool(vars.get('_exit_long', pd.Series([False] * len(df))).iloc[idx] if '_exit_long' in vars else False)
        else:
            return bool(vars.get('_exit_short', pd.Series([False] * len(df))).iloc[idx] if '_exit_short' in vars else False)