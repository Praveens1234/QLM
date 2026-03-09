from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MTDL_RSIStrategy(Strategy):
    """
    Multi Timeframe Divergence And Liquidity (MTDL) RSI Strategy
    Target Asset: XAUUSD | Risk: Max 10 USD | RRR: 1:2
    
    Strategy Components:
    - Trend: 15M EMA cross (long/short bias)
    - Signal: RSI Divergence at swing points
    - Confirmation: Price momentum in direction of bias
    - Risk: Hard cap at 10 USD per trade
    """
    
    def __init__(self):
        # Parameters
        self.max_risk_usd = 10.00
        self.spread_buffer = 0.10  # 10 cents for XAUUSD spread
        self.rsi_period = 14
        self.ema_fast = 50
        self.ema_slow = 200
        self.pivot_lookback = 5
        self.divergence_threshold = 5.0  # Minimum RSI divergence points
    
    def _calculate_rsi(self, closes, period=14):
        """Calculate RSI using Wilder's smoothing method"""
        closes = np.asarray(closes, dtype=np.float64)
        deltas = np.diff(closes)
        
        n = len(closes)
        rsi = np.full(n, np.nan)
        
        if len(deltas) < period:
            return pd.Series(rsi, index=range(n))
        
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        if avg_loss == 0:
            rsi[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[period] = 100.0 - (100.0 / (1 + rs))
        
        for i in range(period + 1, n):
            delta = closes[i] - closes[i - 1]
            gain = delta if delta > 0 else 0.0
            loss = -delta if delta < 0 else 0.0
            
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            
            if avg_loss == 0:
                rsi[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100.0 - (100.0 / (1 + rs))
        
        return pd.Series(rsi, index=range(n))
    
    def _calculate_ema(self, values, period):
        """Calculate EMA"""
        alpha = 2.0 / (period + 1)
        ema = np.zeros(len(values))
        ema[0] = values[0]
        for i in range(1, len(values)):
            ema[i] = alpha * values[i] + (1 - alpha) * ema[i-1]
        return ema
    
    def _get_htf_bias(self, df):
        """
        Calculate HTF bias using pseudo-15M candles
        Returns: 1 (bullish), -1 (bearish)
        """
        n = len(df)
        
        # Create pseudo 15M candles (every 15th bar)
        pseudo_15m_idx = list(range(14, n, 15))
        
        if len(pseudo_15m_idx) < self.ema_slow:
            return np.zeros(n)  # Not enough data
        
        # Get close prices at pseudo 15M intervals
        pseudo_close = df['close'].iloc[pseudo_15m_idx].values
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(pseudo_close, self.ema_fast)
        ema_slow = self._calculate_ema(pseudo_close, self.ema_slow)
        
        # Get bias from last closed 15M candle (index -2)
        if len(ema_fast) < 2:
            return np.zeros(n)
        
        htf_value = 1 if ema_fast[-2] > ema_slow[-2] else -1
        
        return np.full(n, htf_value)
    
    def detect_pivots(self, df):
        """Detect local pivot highs and lows"""
        n = len(df)
        pivot_highs = pd.Series(index=range(n), dtype='float64')
        pivot_lows = pd.Series(index=range(n), dtype='float64')
        
        high_vals = df['high'].values
        low_vals = df['low'].values
        
        for i in range(self.pivot_lookback, n):
            # Pivot high
            center = high_vals[i - 2]
            if (high_vals[i-4] < high_vals[i-3] < center and
                center > high_vals[i-1] > high_vals[i]):
                pivot_highs.iloc[i] = center
            
            # Pivot low
            center = low_vals[i - 2]
            if (low_vals[i-4] > low_vals[i-3] > center and
                center < low_vals[i-1] < low_vals[i]):
                pivot_lows.iloc[i] = center
        
        return pivot_highs, pivot_lows
    
    def _find_last_pivot_rsi(self, rsi_series, pivot_series, idx, lookback=50):
        """Find RSI value at last pivot before current index"""
        # Get pivot indices before current
        pivot_indices = pivot_series.iloc[:idx].dropna().index.tolist()
        
        if not pivot_indices:
            return None, None
        
        # Get the last pivot
        last_pivot_idx = pivot_indices[-1]
        pivot_price = pivot_series.iloc[last_pivot_idx]
        pivot_rsi = rsi_series.iloc[last_pivot_idx]
        
        return pivot_price, pivot_rsi
    
    def define_variables(self, df):
        """Step 1: Calculate all indicators"""
        n = len(df)
        
        # HTF Bias
        htf_bias = self._get_htf_bias(df)
        
        # RSI
        rsi = self._calculate_rsi(df['close'].values, self.rsi_period)
        
        # Pivots
        ph, pl = self.detect_pivots(df)
        
        # Forward fill for last pivot reference
        last_ph = ph.ffill()
        last_pl = pl.ffill()
        
        # Get RSI at pivots
        last_ph_rsi = rsi.where(ph.notna()).ffill()
        last_pl_rsi = rsi.where(pl.notna()).ffill()
        
        # Fill any remaining NaN with current RSI
        last_ph_rsi = last_ph_rsi.fillna(rsi)
        last_pl_rsi = last_pl_rsi.fillna(rsi)
        last_ph = last_ph.fillna(df['high'])
        last_pl = last_pl.fillna(df['low'])
        
        return {
            'htf_bias': pd.Series(htf_bias, index=range(n)),
            'rsi': rsi,
            'last_ph': last_ph,
            'last_pl': last_pl,
            'last_ph_rsi': last_ph_rsi,
            'last_pl_rsi': last_pl_rsi,
            'close': df['close'],
            'high': df['high'],
            'low': df['low'],
        }
    
    def _calculate_risk(self, df, vars, idx, direction):
        """Calculate SL/TP with risk cap"""
        if direction == 'long':
            entry = vars['close'].iloc[idx]
            sl = vars['last_pl'].iloc[idx] - self.spread_buffer
            risk = entry - sl
            if risk > self.max_risk_usd or risk <= 0:
                return None, None
            tp = entry + (risk * 2)
        else:
            entry = vars['close'].iloc[idx]
            sl = vars['last_ph'].iloc[idx] + self.spread_buffer
            risk = sl - entry
            if risk > self.max_risk_usd or risk <= 0:
                return None, None
            tp = entry - (risk * 2)
        return sl, tp
    
    def _check_rsi_divergence(self, vars, idx, direction):
        """
        Check for RSI divergence
        Long: Current RSI higher than at last swing low (while price may be lower)
        Short: Current RSI lower than at last swing high (while price may be higher)
        """
        if direction == 'long':
            current_rsi = vars['rsi'].iloc[idx]
            pivot_rsi = vars['last_pl_rsi'].iloc[idx]
            if pd.isna(pivot_rsi):
                return False
            return current_rsi > pivot_rsi + self.divergence_threshold
        else:
            current_rsi = vars['rsi'].iloc[idx]
            pivot_rsi = vars['last_ph_rsi'].iloc[idx]
            if pd.isna(pivot_rsi):
                return False
            return current_rsi < pivot_rsi - self.divergence_threshold
    
    def entry_long(self, df, vars):
        """
        LONG Entry Conditions:
        1. HTF Bias: Bullish (50 EMA > 200 EMA on 15M)
        2. Price: At or near recent swing low (support)
        3. RSI: Showing bullish divergence
        4. Risk: Within 10 USD limit
        """
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        min_bars = self.ema_slow
        
        for i in range(min_bars, n):
            # Condition 1: HTF Bias bullish
            if vars['htf_bias'].iloc[i] != 1:
                continue
            
            # Condition 2: Price near support (within 0.3% of swing low)
            price = vars['close'].iloc[i]
            swing_low = vars['last_pl'].iloc[i]
            if pd.isna(swing_low):
                continue
            
            near_support = price <= swing_low * 1.003
            
            # Condition 3: RSI Divergence
            divergence = self._check_rsi_divergence(vars, i, 'long')
            
            # Condition 4: Risk Check
            sl, tp = self._calculate_risk(df, vars, i, 'long')
            if sl is None:
                continue
            
            # Entry: Bias + Support + Divergence
            if near_support and divergence:
                result.iloc[i] = True
        
        return result
    
    def entry_short(self, df, vars):
        """
        SHORT Entry Conditions:
        1. HTF Bias: Bearish (50 EMA < 200 EMA on 15M)
        2. Price: At or near recent swing high (resistance)
        3. RSI: Showing bearish divergence
        4. Risk: Within 10 USD limit
        """
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        min_bars = self.ema_slow
        
        for i in range(min_bars, n):
            # Condition 1: HTF Bias bearish
            if vars['htf_bias'].iloc[i] != -1:
                continue
            
            # Condition 2: Price near resistance (within 0.3% of swing high)
            price = vars['close'].iloc[i]
            swing_high = vars['last_ph'].iloc[i]
            if pd.isna(swing_high):
                continue
            
            near_resistance = price >= swing_high * 0.997
            
            # Condition 3: RSI Divergence
            divergence = self._check_rsi_divergence(vars, i, 'short')
            
            # Condition 4: Risk Check
            sl, tp = self._calculate_risk(df, vars, i, 'short')
            if sl is None:
                continue
            
            # Entry: Bias + Resistance + Divergence
            if near_resistance and divergence:
                result.iloc[i] = True
        
        return result
    
    def risk_model(self, df, vars):
        """Dynamic SL/TP with 1:2 RRR"""
        idx = df.index.get_loc(df.index[-1])
        
        bias = vars['htf_bias'].iloc[idx]
        if bias == 1:
            sl, tp = self._calculate_risk(df, vars, idx, 'long')
        elif bias == -1:
            sl, tp = self._calculate_risk(df, vars, idx, 'short')
        else:
            sl, tp = None, None
        
        return {'sl': sl, 'tp': tp}
    
    def exit(self, df, vars, trade):
        return False