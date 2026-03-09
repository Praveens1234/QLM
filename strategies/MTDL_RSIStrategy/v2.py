from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MTDL_RSIStrategy(Strategy):
    """Author: MCP Client | MTDL RSI Strategy | XAUUSD | Simplified for Testing"""
    
    def __init__(self):
        # Risk parameters
        self.max_risk_usd = 10.00
        self.spread_buffer = 0.05
    
    def _calculate_rsi(self, closes, period=14):
        """Calculate RSI using pure numpy/pandas"""
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
    
    def detect_pivots(self, df):
        """Detects pivots using rolling window"""
        n = len(df)
        pivot_highs = pd.Series(index=range(n), dtype='float64')
        pivot_lows = pd.Series(index=range(n), dtype='float64')
        
        high_vals = df['high'].values
        low_vals = df['low'].values
        
        # Simple 5-bar pivot detection
        for i in range(4, n):
            # High pivot: local maximum
            if (high_vals[i-2] >= high_vals[i-4] and 
                high_vals[i-2] >= high_vals[i-3] and 
                high_vals[i-2] >= high_vals[i-1] and 
                high_vals[i-2] >= high_vals[i]):
                pivot_highs.iloc[i] = high_vals[i-2]
            
            # Low pivot: local minimum
            if (low_vals[i-2] <= low_vals[i-4] and 
                low_vals[i-2] <= low_vals[i-3] and 
                low_vals[i-2] <= low_vals[i-1] and 
                low_vals[i-2] <= low_vals[i]):
                pivot_lows.iloc[i] = low_vals[i-2]
        
        return pivot_highs, pivot_lows
    
    def define_variables(self, df):
        n = len(df)
        
        # Simple trend bias using price relative to SMA
        sma_50 = df['close'].rolling(50).mean()
        bias = pd.Series(np.where(df['close'] > sma_50.shift(1), 1, -1), index=range(n))
        bias = bias.fillna(-1)  # Default to short bias if not enough data
        
        # RSI calculation
        closes = df['close'].values
        rsi = self._calculate_rsi(closes, 14)
        
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
            'bias': bias,
            'rsi': rsi,
            'sma_50': sma_50,
            'last_ph_price': last_ph_price,
            'last_pl_price': last_pl_price,
            'last_ph_rsi': last_ph_rsi,
            'last_pl_rsi': last_pl_rsi,
            'close': df['close'],
            'high': df['high'],
            'low': df['low'],
        }
    
    def _calculate_risk(self, df, vars, idx, direction):
        """Calculate risk parameters"""
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
    
    def entry_long(self, df, vars):
        """Long entry: RSI oversold + price bounce from low"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        for i in range(20, n):  # Start from bar 20 for RSI stability
            # Skip if no valid pivot
            if pd.isna(vars['last_pl_price'].iloc[i]) or pd.isna(vars['last_ph_price'].iloc[i]):
                continue
            
            # RSI oversold condition (RSI < 35)
            rsi_oversold = vars['rsi'].iloc[i] < 35
            
            # Price near recent low (within 0.5% of last pivot low)
            price_near_low = vars['close'].iloc[i] <= vars['last_pl_price'].iloc[i] * 1.005
            
            # Uptrend bias
            uptrend = vars['bias'].iloc[i] == 1
            
            # Risk check
            sl, tp = self._calculate_risk(df, vars, i, 'long')
            if sl is None:
                continue
            
            # Entry: RSI oversold + near support + uptrend
            if rsi_oversold and price_near_low and uptrend:
                result.iloc[i] = True
        
        return result
    
    def entry_short(self, df, vars):
        """Short entry: RSI overbought + price near high"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        for i in range(20, n):
            # Skip if no valid pivot
            if pd.isna(vars['last_ph_price'].iloc[i]) or pd.isna(vars['last_pl_price'].iloc[i]):
                continue
            
            # RSI overbought condition (RSI > 65)
            rsi_overbought = vars['rsi'].iloc[i] > 65
            
            # Price near recent high (within 0.5% of last pivot high)
            price_near_high = vars['close'].iloc[i] >= vars['last_ph_price'].iloc[i] * 0.995
            
            # Downtrend bias
            downtrend = vars['bias'].iloc[i] == -1
            
            # Risk check
            sl, tp = self._calculate_risk(df, vars, i, 'short')
            if sl is None:
                continue
            
            # Entry: RSI overbought + near resistance + downtrend
            if rsi_overbought and price_near_high and downtrend:
                result.iloc[i] = True
        
        return result
    
    def risk_model(self, df, vars):
        """Hard 1:2 RRR with 10 USD max risk"""
        idx = df.index.get_loc(df.index[-1])
        
        if vars['bias'].iloc[idx] == 1:
            sl, tp = self._calculate_risk(df, vars, idx, 'long')
        else:
            sl, tp = self._calculate_risk(df, vars, idx, 'short')
        
        return {'sl': sl, 'tp': tp}
    
    def exit(self, df, vars, trade):
        return False