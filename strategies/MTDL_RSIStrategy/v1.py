from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MTDL_RSIStrategy(Strategy):
    """Author: MCP Client | MTDL RSI Strategy | XAUUSD"""
    
    def __init__(self):
        # State management
        self.awaiting_mss = False
        self.last_setup_time = None
        self.setup_direction = None
        self.setup_price = None
        self.mss_triggered = False
        
        # Risk parameters
        self.max_risk_usd = 10.00
        self.spread_buffer = 0.05  # 5 cents for XAUUSD
    
    def _calculate_rsi(self, closes, period=14):
        """Calculate RSI using pure numpy/pandas"""
        closes = np.asarray(closes, dtype=np.float64)
        deltas = np.diff(closes)
        
        n = len(closes)
        rsi = np.full(n, np.nan)
        
        if len(deltas) < period:
            return pd.Series(rsi, index=range(n))
        
        # Calculate initial average gain and loss
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        # Calculate first RSI value
        if avg_loss == 0:
            rsi[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[period] = 100.0 - (100.0 / (1 + rs))
        
        # Calculate subsequent RSI values
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
    
    def _get_15m_data(self, df):
        """Convert 1M data to 15M candles with proper alignment"""
        if not isinstance(df.index, pd.DatetimeIndex):
            df_copy = df.copy()
            df_copy.index = pd.RangeIndex(start=0, stop=len(df), step=1)
            return df_copy
        
        return df.resample('15min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
    
    def detect_pivots(self, df):
        """Detects pivots using only past data with 2-bar confirmation delay"""
        n = len(df)
        pivot_highs = pd.Series(index=range(n), dtype='float64')
        pivot_lows = pd.Series(index=range(n), dtype='float64')
        
        high_vals = df['high'].values
        low_vals = df['low'].values
        
        for i in range(4, n):
            # High pivot check
            if (high_vals[i-4] < high_vals[i-3] and 
                high_vals[i-3] < high_vals[i-2] and 
                high_vals[i-2] > high_vals[i-1] and 
                high_vals[i-1] > high_vals[i]):
                pivot_highs.iloc[i] = high_vals[i-2]
            
            # Low pivot check
            if (low_vals[i-4] > low_vals[i-3] and 
                low_vals[i-3] > low_vals[i-2] and 
                low_vals[i-2] < low_vals[i-1] and 
                low_vals[i-1] < low_vals[i]):
                pivot_lows.iloc[i] = low_vals[i-2]
        
        return pivot_highs, pivot_lows
    
    def _check_divergence(self, df, vars, idx, direction):
        """Check for RSI divergence at a specific index"""
        current_price = df['close'].iloc[idx]
        current_rsi = vars['rsi'].iloc[idx]
        
        last_ph_price = vars['last_ph_price'].iloc[idx]
        last_pl_price = vars['last_pl_price'].iloc[idx]
        last_ph_rsi = vars['last_ph_rsi'].iloc[idx]
        last_pl_rsi = vars['last_pl_rsi'].iloc[idx]
        
        prev_ph_price = vars['last_ph_price'].iloc[idx-1] if idx > 0 else last_ph_price
        prev_pl_price = vars['last_pl_price'].iloc[idx-1] if idx > 0 else last_pl_price
        prev_ph_rsi = vars['last_ph_rsi'].iloc[idx-1] if idx > 0 else last_ph_rsi
        prev_pl_rsi = vars['last_pl_rsi'].iloc[idx-1] if idx > 0 else last_pl_rsi
        
        if direction == 'long':
            return (current_price < last_pl_price and 
                   current_rsi > last_pl_rsi and 
                   last_pl_rsi < prev_pl_rsi)
        else:
            return (current_price > last_ph_price and 
                   current_rsi < last_ph_rsi and 
                   last_ph_rsi > prev_ph_rsi)
    
    def define_variables(self, df):
        n = len(df)
        
        # HTF bias calculation
        df_15m = self._get_15m_data(df)
        ema_50_15m = df_15m['close'].ewm(span=50).mean()
        ema_200_15m = df_15m['close'].ewm(span=200).mean()
        bias_15m = pd.Series(np.where(ema_50_15m > ema_200_15m, 1, -1), 
                            index=df_15m.index)
        
        # Map 15M bias to 1M with shift for anti-lookahead
        bias_15m_aligned = bias_15m.reindex(range(n), method='ffill').shift(1)
        
        # RSI calculation using pure numpy/pandas
        closes = df['close'].values
        rsi = self._calculate_rsi(closes, 14)
        
        # Pivots
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
            'bias_15m': bias_15m_aligned,
            'rsi': rsi,
            'last_ph_price': last_ph_price,
            'last_pl_price': last_pl_price,
            'last_ph_rsi': last_ph_rsi,
            'last_pl_rsi': last_pl_rsi,
        }
    
    def _calculate_risk_params(self, df, vars, idx, direction):
        """Calculate risk parameters at a specific index"""
        if direction == 'long':
            entry = df['close'].iloc[idx]
            last_low = vars['last_pl_price'].iloc[idx]
            sl = last_low - self.spread_buffer
            risk = entry - sl
            if risk > self.max_risk_usd or risk <= 0:
                return None, None
            tp = entry + (risk * 2)
        else:
            entry = df['close'].iloc[idx]
            last_high = vars['last_ph_price'].iloc[idx]
            sl = last_high + self.spread_buffer
            risk = sl - entry
            if risk > self.max_risk_usd or risk <= 0:
                return None, None
            tp = entry - (risk * 2)
            
        return sl, tp
    
    def entry_long(self, df, vars):
        """Define exact conditions to enter a Long position"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        for i in range(n):
            # Check HTF bias
            if vars['bias_15m'].iloc[i] != 1:
                continue
            
            # Get pivot levels
            last_ph = vars['last_ph_price'].iloc[i]
            last_pl = vars['last_pl_price'].iloc[i]
            
            if pd.isna(last_pl) or pd.isna(last_ph):
                continue
            
            # Check for liquidity sweep
            current_low = df['low'].iloc[i]
            sweep = current_low < last_pl
            
            # Check for divergence
            divergence = self._check_divergence(df, vars, i, 'long')
            
            # Check for MSS (Market Structure Shift)
            mss = df['close'].iloc[i] > last_ph
            
            # Check risk
            sl, tp = self._calculate_risk_params(df, vars, i, 'long')
            if sl is None:
                continue
            
            # Entry condition: Sweep + Divergence + MSS confirmed
            if sweep and divergence and mss:
                result.iloc[i] = True
        
        return result
    
    def entry_short(self, df, vars):
        """Define exact conditions to enter a Short position"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        for i in range(n):
            # Check HTF bias
            if vars['bias_15m'].iloc[i] != -1:
                continue
            
            # Get pivot levels
            last_ph = vars['last_ph_price'].iloc[i]
            last_pl = vars['last_pl_price'].iloc[i]
            
            if pd.isna(last_ph) or pd.isna(last_pl):
                continue
            
            # Check for liquidity sweep
            current_high = df['high'].iloc[i]
            sweep = current_high > last_ph
            
            # Check for divergence
            divergence = self._check_divergence(df, vars, i, 'short')
            
            # Check for MSS (Market Structure Shift)
            mss = df['close'].iloc[i] < last_pl
            
            # Check risk
            sl, tp = self._calculate_risk_params(df, vars, i, 'short')
            if sl is None:
                continue
            
            # Entry condition: Sweep + Divergence + MSS confirmed
            if sweep and divergence and mss:
                result.iloc[i] = True
        
        return result
    
    def risk_model(self, df, vars):
        """Define dynamic Stop Loss (sl) and Take Profit (tp) logic"""
        idx = df.index.get_loc(df.index[-1])
        
        if vars['bias_15m'].iloc[idx] == 1:
            sl, tp = self._calculate_risk_params(df, vars, idx, 'long')
        else:
            sl, tp = self._calculate_risk_params(df, vars, idx, 'short')
        
        return {'sl': sl, 'tp': tp}
    
    def exit(self, df, vars, trade):
        """Dynamic exit logic - disabled for this strategy"""
        return False