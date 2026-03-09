from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MTDL_RSIStrategy(Strategy):
    """
    MTDL RSI Strategy - Clean Implementation
    Risk: Max $10 | RRR: 1:2
    """
    
    def __init__(self):
        self.max_risk_usd = 10.00
        self.spread_buffer = 0.05
        self.rsi_period = 14
    
    def _calculate_rsi(self, closes, period=14):
        """RSI calculation"""
        closes = np.asarray(closes, dtype=np.float64)
        deltas = np.diff(closes)
        n = len(closes)
        rsi = np.full(n, 50.0)
        
        if len(deltas) < period:
            return pd.Series(rsi, index=range(n))
        
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi[period] = 100 - (100 / (1 + rs))
        
        for i in range(period + 1, n):
            delta = closes[i] - closes[i - 1]
            gain = delta if delta > 0 else 0.0
            loss = -delta if delta < 0 else 0.0
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))
            else:
                rsi[i] = 100.0
        
        return pd.Series(rsi, index=range(n))
    
    def _get_trend(self, df):
        """Simple trend using 50/200 EMA on close price"""
        n = len(df)
        
        # Use 50/200 EMA on actual 1M data for trend
        ema_50 = df['close'].ewm(span=50, adjust=False).mean().values
        ema_200 = df['close'].ewm(span=200, adjust=False).mean().values
        
        trend = np.zeros(n)
        for i in range(200, n):
            trend[i] = 1 if ema_50[i] > ema_200[i] else -1
        
        return trend
    
    def detect_swings(self, df):
        """Simple swing detection"""
        n = len(df)
        swing_high = pd.Series(index=range(n), dtype='float64')
        swing_low = pd.Series(index=range(n), dtype='float64')
        
        high = df['high'].values
        low = df['low'].values
        
        for i in range(5, n):
            # Simple local extrema
            if high[i-2] >= high[i-3] and high[i-2] >= high[i-1]:
                swing_high.iloc[i] = high[i-2]
            if low[i-2] <= low[i-3] and low[i-2] <= low[i-1]:
                swing_low.iloc[i] = low[i-2]
        
        return swing_high, swing_low
    
    def define_variables(self, df):
        n = len(df)
        
        # Trend
        trend = self._get_trend(df)
        
        # RSI
        rsi = self._calculate_rsi(df['close'].values, self.rsi_period)
        
        # Swings
        sh, sl = self.detect_swings(df)
        
        # Forward fill with defaults
        last_sh = sh.ffill().bfill().fillna(df['high'])
        last_sl = sl.ffill().bfill().fillna(df['low'])
        
        # RSI at swings
        sh_rsi = rsi.where(sh.notna()).ffill().bfill().fillna(50)
        sl_rsi = rsi.where(sl.notna()).ffill().bfill().fillna(50)
        
        return {
            'trend': pd.Series(trend, index=range(n)),
            'rsi': rsi,
            'last_sh': last_sh,
            'last_sl': last_sl,
            'sh_rsi': sh_rsi,
            'sl_rsi': sl_rsi,
            'close': df['close'],
            'high': df['high'],
            'low': df['low'],
        }
    
    def _validate_risk(self, df, vars, idx, direction):
        """Calculate and validate SL/TP"""
        if direction == 'long':
            entry = vars['close'].iloc[idx]
            sl_price = vars['last_sl'].iloc[idx] - self.spread_buffer
            risk = entry - sl_price
            if risk <= 0 or risk > self.max_risk_usd:
                return None, None
            tp_price = entry + (risk * 2)
            return sl_price, tp_price
        else:
            entry = vars['close'].iloc[idx]
            sl_price = vars['last_sh'].iloc[idx] + self.spread_buffer
            risk = sl_price - entry
            if risk <= 0 or risk > self.max_risk_usd:
                return None, None
            tp_price = entry - (risk * 2)
            return sl_price, tp_price
    
    def entry_long(self, df, vars):
        """Long: Uptrend + RSI oversold + Near support"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        for i in range(200, n):  # Need 200 bars for EMA 200
            # Skip if risk validation fails first
            sl, tp = self._validate_risk(df, vars, i, 'long')
            if sl is None:
                continue
            
            # Uptrend
            if vars['trend'].iloc[i] != 1:
                continue
            
            # RSI oversold
            rsi_oversold = vars['rsi'].iloc[i] < 35
            
            # Near support (within 0.2% of swing low)
            near_support = vars['close'].iloc[i] <= vars['last_sl'].iloc[i] * 1.002
            
            if rsi_oversold and near_support:
                result.iloc[i] = True
        
        return result
    
    def entry_short(self, df, vars):
        """Short: Downtrend + RSI overbought + Near resistance"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        for i in range(200, n):
            # Skip if risk validation fails first
            sl, tp = self._validate_risk(df, vars, i, 'short')
            if sl is None:
                continue
            
            # Downtrend
            if vars['trend'].iloc[i] != -1:
                continue
            
            # RSI overbought
            rsi_overbought = vars['rsi'].iloc[i] > 65
            
            # Near resistance (within 0.2% of swing high)
            near_resistance = vars['close'].iloc[i] >= vars['last_sh'].iloc[i] * 0.998
            
            if rsi_overbought and near_resistance:
                result.iloc[i] = True
        
        return result
    
    def risk_model(self, df, vars):
        """SL/TP with risk validation"""
        idx = df.index.get_loc(df.index[-1])
        trend = vars['trend'].iloc[idx]
        
        if trend == 1:
            sl, tp = self._validate_risk(df, vars, idx, 'long')
        elif trend == -1:
            sl, tp = self._validate_risk(df, vars, idx, 'short')
        else:
            sl, tp = None, None
        
        return {'sl': sl, 'tp': tp}
    
    def exit(self, df, vars, trade):
        return False