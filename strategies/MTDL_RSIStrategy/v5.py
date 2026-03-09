from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MTDL_RSIStrategy(Strategy):
    """
    Multi Timeframe Divergence And Liquidity (MTDL) RSI Strategy
    Target: XAUUSD | Risk: Max $10 | RRR: 1:2
    """
    
    def __init__(self):
        # Parameters
        self.max_risk_usd = 10.00
        self.spread_buffer = 0.05
        self.rsi_period = 14
        self.ema_fast = 50
        self.ema_slow = 200
    
    def _calculate_rsi(self, closes, period=14):
        """Wilder's RSI calculation"""
        closes = np.asarray(closes, dtype=np.float64)
        deltas = np.diff(closes)
        n = len(closes)
        rsi = np.full(n, 50.0)  # Default neutral
        
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
    
    def _calculate_ema(self, values, period):
        """Calculate EMA"""
        alpha = 2.0 / (period + 1)
        ema = np.zeros(len(values))
        ema[0] = values[0]
        for i in range(1, len(values)):
            ema[i] = alpha * values[i] + (1 - alpha) * ema[i-1]
        return ema
    
    def _get_trend(self, df):
        """Get trend from pseudo 15M candles"""
        n = len(df)
        idx_15m = list(range(14, n, 15))
        
        if len(idx_15m) < self.ema_slow:
            return np.zeros(n)
        
        closes_15m = df['close'].iloc[idx_15m].values
        ema_fast = self._calculate_ema(closes_15m, self.ema_fast)
        ema_slow = self._calculate_ema(closes_15m, self.ema_slow)
        
        if len(ema_fast) < 2:
            return np.zeros(n)
        
        trend = 1 if ema_fast[-2] > ema_slow[-2] else -1
        return np.full(n, trend)
    
    def detect_swings(self, df):
        """Detect swing highs and lows"""
        n = len(df)
        swing_high = pd.Series(index=range(n), dtype='float64')
        swing_low = pd.Series(index=range(n), dtype='float64')
        
        high = df['high'].values
        low = df['low'].values
        
        for i in range(5, n):
            # Swing high
            if high[i-2] >= high[i-5:i-2].max() and high[i-2] >= high[i-1:i+1].max():
                swing_high.iloc[i] = high[i-2]
            # Swing low
            if low[i-2] <= low[i-5:i-2].min() and low[i-2] <= low[i-1:i+1].min():
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
        
        # Forward fill
        last_sh = sh.ffill().fillna(df['high'])
        last_sl = sl.ffill().fillna(df['low'])
        
        # RSI at swings
        sh_rsi = rsi.where(sh.notna()).ffill().fillna(50)
        sl_rsi = rsi.where(sl.notna()).ffill().fillna(50)
        
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
    
    def _check_risk(self, df, vars, idx, direction):
        """Verify trade meets risk criteria"""
        if direction == 'long':
            entry = vars['close'].iloc[idx]
            sl = vars['last_sl'].iloc[idx] - self.spread_buffer
            risk = entry - sl
            if risk <= 0 or risk > self.max_risk_usd:
                return None, None
            tp = entry + (risk * 2)
            return sl, tp
        else:
            entry = vars['close'].iloc[idx]
            sl = vars['last_sh'].iloc[idx] + self.spread_buffer
            risk = sl - entry
            if risk <= 0 or risk > self.max_risk_usd:
                return None, None
            tp = entry - (risk * 2)
            return sl, tp
    
    def _has_divergence(self, vars, idx, direction):
        """Check RSI divergence"""
        if direction == 'long':
            rsi_now = vars['rsi'].iloc[idx]
            rsi_at_sl = vars['sl_rsi'].iloc[idx]
            return rsi_now > rsi_at_sl + 3  # 3 RSI points divergence
        else:
            rsi_now = vars['rsi'].iloc[idx]
            rsi_at_sh = vars['sh_rsi'].iloc[idx]
            return rsi_now < rsi_at_sh - 3
    
    def entry_long(self, df, vars):
        """Long: Uptrend + Near support + RSI divergence"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        min_idx = max(self.ema_slow, 50)
        
        for i in range(min_idx, n):
            # 1. Uptrend
            if vars['trend'].iloc[i] != 1:
                continue
            
            # 2. Near support
            price = vars['close'].iloc[i]
            support = vars['last_sl'].iloc[i]
            near_support = price <= support * 1.002
            
            # 3. RSI divergence
            divergence = self._has_divergence(vars, i, 'long')
            
            # 4. Risk check
            sl, tp = self._check_risk(df, vars, i, 'long')
            if sl is None:
                continue
            
            if near_support and divergence:
                result.iloc[i] = True
        
        return result
    
    def entry_short(self, df, vars):
        """Short: Downtrend + Near resistance + RSI divergence"""
        n = len(df)
        result = pd.Series([False] * n, index=range(n))
        
        min_idx = max(self.ema_slow, 50)
        
        for i in range(min_idx, n):
            # 1. Downtrend
            if vars['trend'].iloc[i] != -1:
                continue
            
            # 2. Near resistance
            price = vars['close'].iloc[i]
            resistance = vars['last_sh'].iloc[i]
            near_resistance = price >= resistance * 0.998
            
            # 3. RSI divergence
            divergence = self._has_divergence(vars, i, 'short')
            
            # 4. Risk check
            sl, tp = self._check_risk(df, vars, i, 'short')
            if sl is None:
                continue
            
            if near_resistance and divergence:
                result.iloc[i] = True
        
        return result
    
    def risk_model(self, df, vars):
        """Dynamic SL/TP"""
        idx = df.index.get_loc(df.index[-1])
        trend = vars['trend'].iloc[idx]
        
        if trend == 1:
            sl, tp = self._check_risk(df, vars, idx, 'long')
        elif trend == -1:
            sl, tp = self._check_risk(df, vars, idx, 'short')
        else:
            sl, tp = None, None
        
        return {'sl': sl, 'tp': tp}
    
    def exit(self, df, vars, trade):
        return False