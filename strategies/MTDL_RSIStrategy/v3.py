from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MTDL_RSIStrategy(Strategy):
    """
    Multi Timeframe Divergence And Liquidity (MTDL) RSI Strategy
    Target Asset: XAUUSD | Classification: Mean-Reversion to Trend-Continuation
    
    Core Logic:
    - HTF Bias: 50 EMA > 200 EMA on 15M (long only) or 50 EMA < 200 EMA (short only)
    - Liquidity Sweep: Price breaks below last pivot low (long) or above last pivot high (short)
    - RSI Divergence: Higher low in RSI during price lower low (long)
    - MSS: Candle closes beyond the pivot extreme that caused the sweep
    - Risk: Max 10 USD, Hard 1:2 RRR
    """
    
    def __init__(self):
        # Risk parameters
        self.max_risk_usd = 10.00
        self.spread_buffer = 0.05
        self.rsi_period = 14
        self.ema_fast = 50
        self.ema_slow = 200
        self.pivot_lookback = 5
        
        # State tracking
        self._last_bar_idx = -1
        self._htf_bias_cache = {}
    
    def _calculate_rsi(self, closes, period=14):
        """Calculate RSI using pure numpy/pandas - Wilder's smoothing method"""
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
    
    def _get_htf_bias_simplified(self, df):
        """
        Calculate HTF bias using embedded 15M approximation
        For RangeIndex data, use every 15th bar as 15M candle
        """
        n = len(df)
        bias = np.zeros(n)
        
        # Create pseudo-15M candles from every 15th 1M bar
        pseudo_15m_indices = list(range(14, n, 15))
        
        if len(pseudo_15m_indices) < self.ema_slow:
            # Not enough data, default to neutral
            return pd.Series(np.zeros(n), index=range(n))
        
        # Extract pseudo 15M close prices
        pseudo_15m_close = df['close'].iloc[pseudo_15m_indices].values
        
        # Calculate EMAs on pseudo 15M data
        ema_fast_vals = np.zeros(len(pseudo_15m_close))
        ema_slow_vals = np.zeros(len(pseudo_15m_close))
        
        # EMA calculation
        ema_fast_vals[0] = pseudo_15m_close[0]
        ema_slow_vals[0] = pseudo_15m_close[0]
        
        alpha_fast = 2.0 / (self.ema_fast + 1)
        alpha_slow = 2.0 / (self.ema_slow + 1)
        
        for i in range(1, len(pseudo_15m_close)):
            ema_fast_vals[i] = alpha_fast * pseudo_15m_close[i] + (1 - alpha_fast) * ema_fast_vals[i-1]
            ema_slow_vals[i] = alpha_slow * pseudo_15m_close[i] + (1 - alpha_slow) * ema_slow_vals[i-1]
        
        # Get bias from second-to-last 15M candle (anti-lookahead)
        if len(ema_fast_vals) < 2:
            return pd.Series(np.zeros(n), index=range(n))
        
        htf_bias = 1 if ema_fast_vals[-2] > ema_slow_vals[-2] else -1
        
        # Map to 1M bars
        bias[:] = htf_bias
        
        return pd.Series(bias, index=range(n))
    
    def detect_pivots(self, df):
        """
        Detect fractal pivot highs and lows using 5-bar pattern
        """
        n = len(df)
        pivot_highs = pd.Series(index=range(n), dtype='float64')
        pivot_lows = pd.Series(index=range(n), dtype='float64')
        
        high_vals = df['high'].values
        low_vals = df['low'].values
        
        for i in range(self.pivot_lookback, n):
            # Check for pivot high
            center_high = high_vals[i - 2]
            if (high_vals[i-4] < high_vals[i-3] < center_high and
                center_high > high_vals[i-1] > high_vals[i]):
                pivot_highs.iloc[i] = center_high
            
            # Check for pivot low
            center_low = low_vals[i - 2]
            if (low_vals[i-4] > low_vals[i-3] > center_low and
                center_low < low_vals[i-1] < low_vals[i]):
                pivot_lows.iloc[i] = center_low
        
        return pivot_highs, pivot_lows
    
    def define_variables(self, df):
        """Step 1: Calculate all indicators"""
        n = len(df)
        
        # HTF Bias calculation (simplified for non-timeindex data)
        htf_bias = self._get_htf_bias_simplified(df)
        
        # RSI calculation
        closes = df['close'].values
        rsi = self._calculate_rsi(closes, self.rsi_period)
        
        # Pivot detection
        ph_price, pl_price = self.detect_pivots(df)
        
        # RSI at pivot points
        ph_rsi = rsi.where(ph_price.notna())
        pl_rsi = rsi.where(pl_price.notna())
        
        # Forward fill for last pivot reference
        last_ph_price = ph_price.ffill()
        last_pl_price = pl_price.ffill()
        last_ph_rsi = ph_rsi.ffill()
        last_pl_rsi = pl_rsi.ffill()
        
        return {
            'htf_bias': htf_bias,
            'rsi': rsi,
            'last_ph_price': last_ph_price,
            'last_pl_price': last_pl_price,
            'last_ph_rsi': last_ph_rsi,
            'last_pl_rsi': last_pl_rsi,
            'close': df['close'],
            'high': df['high'],
            'low': df['low'],
        }
    
    def _calculate_risk_params(self, df, vars, idx, direction):
        """Calculate SL/TP with hard 10 USD risk cap"""
        if direction == 'long':
            entry = vars['close'].iloc[idx]
            last_low = vars['last_pl_price'].iloc[idx]
            if pd.isna(last_low):
                return None, None
            sl = last_low - self.spread_buffer
            risk = entry - sl
            if risk > self.max_risk_usd or risk <= 0:
                return None, None
            tp = entry + (risk * 2)
        else:
            entry = vars['close'].iloc[idx]
            last_high = vars['last_ph_price'].iloc[idx]
            if pd.isna(last_high):
                return None, None
            sl = last_high + self.spread_buffer
            risk = sl - entry
            if risk > self.max_risk_usd or risk <= 0:
                return None, None
            tp = entry - (risk * 2)
            
        return sl, tp
    
    def _check_divergence(self, vars, idx, direction):
        """Check for RSI divergence"""
        if direction == 'long':
            current_price = vars['close'].iloc[idx]
            current_rsi = vars['rsi'].iloc[idx]
            
            last_pl_price = vars['last_pl_price'].iloc[idx]
            last_pl_rsi = vars['last_pl_rsi'].iloc[idx]
            
            prev_pl_rsi = vars['last_pl_rsi'].iloc[idx-1] if idx > 0 else last_pl_rsi
            
            if pd.isna(last_pl_price) or pd.isna(last_pl_rsi):
                return False
            
            price_lower = current_price < last_pl_price
            rsi_higher = current_rsi > last_pl_rsi
            prev_rsi_lower = last_pl_rsi < prev_pl_rsi if not pd.isna(prev_pl_rsi) else False
            
            return price_lower and rsi_higher and prev_rsi_lower
            
        else:
            current_price = vars['close'].iloc[idx]
            current_rsi = vars['rsi'].iloc[idx]
            
            last_ph_price = vars['last_ph_price'].iloc[idx]
            last_ph_rsi = vars['last_ph_rsi'].iloc[idx]
            
            prev_ph_rsi = vars['last_ph_rsi'].iloc[idx-1] if idx > 0 else last_ph_rsi
            
            if pd.isna(last_ph_price) or pd.isna(last_ph_rsi):
                return False
            
            price_higher = current_price > last_ph_price
            rsi_lower = current_rsi < last_ph_rsi
            prev_rsi_higher = last_ph_rsi > prev_ph_rsi if not pd.isna(prev_ph_rsi) else False
            
            return price_higher and rsi_lower and prev_rsi_higher
    
    def entry_long(self, df, vars):
        """LONG Setup: HTF Bias + Liquidity Sweep + RSI Divergence + MSS"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        min_bars = max(self.pivot_lookback + 2, self.rsi_period + 2)
        
        for i in range(min_bars, n):
            # HTF Bias must be bullish
            if vars['htf_bias'].iloc[i] != 1:
                continue
            
            # Get pivot levels
            last_ph = vars['last_ph_price'].iloc[i]
            last_pl = vars['last_pl_price'].iloc[i]
            
            if pd.isna(last_pl) or pd.isna(last_ph):
                continue
            
            # Liquidity Sweep - Price breaks below pivot low
            current_low = vars['low'].iloc[i]
            sweep = current_low < last_pl
            
            # RSI Divergence
            divergence = self._check_divergence(vars, i, 'long')
            
            # MSS - Price closes above last pivot high
            mss = vars['close'].iloc[i] > last_ph
            
            # Risk Check
            sl, tp = self._calculate_risk_params(df, vars, i, 'long')
            if sl is None:
                continue
            
            # Entry: All conditions met
            if sweep and divergence and mss:
                result.iloc[i] = True
        
        return result
    
    def entry_short(self, df, vars):
        """SHORT Setup: HTF Bias + Liquidity Sweep + RSI Divergence + MSS"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        min_bars = max(self.pivot_lookback + 2, self.rsi_period + 2)
        
        for i in range(min_bars, n):
            # HTF Bias must be bearish
            if vars['htf_bias'].iloc[i] != -1:
                continue
            
            # Get pivot levels
            last_ph = vars['last_ph_price'].iloc[i]
            last_pl = vars['last_pl_price'].iloc[i]
            
            if pd.isna(last_ph) or pd.isna(last_pl):
                continue
            
            # Liquidity Sweep - Price breaks above pivot high
            current_high = vars['high'].iloc[i]
            sweep = current_high > last_ph
            
            # RSI Divergence
            divergence = self._check_divergence(vars, i, 'short')
            
            # MSS - Price closes below last pivot low
            mss = vars['close'].iloc[i] < last_pl
            
            # Risk Check
            sl, tp = self._calculate_risk_params(df, vars, i, 'short')
            if sl is None:
                continue
            
            # Entry: All conditions met
            if sweep and divergence and mss:
                result.iloc[i] = True
        
        return result
    
    def risk_model(self, df, vars):
        """Step 3: Dynamic Stop Loss and Take Profit with hard 1:2 RRR"""
        idx = df.index.get_loc(df.index[-1])
        
        if vars['htf_bias'].iloc[idx] == 1:
            sl, tp = self._calculate_risk_params(df, vars, idx, 'long')
        elif vars['htf_bias'].iloc[idx] == -1:
            sl, tp = self._calculate_risk_params(df, vars, idx, 'short')
        else:
            sl, tp = None, None
        
        return {'sl': sl, 'tp': tp}
    
    def exit(self, df, vars, trade):
        """Step 4: No dynamic exit - RRR enforced by risk_model"""
        return False