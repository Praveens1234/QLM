from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MTDL_RSIStrategy(Strategy):
    """
    MTDL RSI Strategy - Vectorized & QLM Compliant
    Risk: Max $10 | RRR: 1:2
    """
    
    def __init__(self, parameters=None):
        super().__init__(parameters)
        self.max_risk_usd = 10.00
        self.spread_buffer = 0.05
        self.rsi_period = 14
    
    def _calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """RSI calculation (Wilder's Smoothing) appropriately vectorized."""
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        alpha = 1 / self.rsi_period
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    def _get_trend(self, df: pd.DataFrame) -> pd.Series:
        """Simple trend using 50/200 EMA on close price"""
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        ema_200 = df['close'].ewm(span=200, adjust=False).mean()
        
        trend = pd.Series(0.0, index=df.index)
        trend[ema_50 > ema_200] = 1.0
        trend[ema_50 < ema_200] = -1.0
        return trend
    
    def detect_swings(self, df: pd.DataFrame):
        """Simple swing detection correctly shifted globally."""
        high = df['high']
        low = df['low']
        
        # Local extrema logic strictly based on shifting to avoid lookahead bias
        is_swing_high = (high.shift(2) >= high.shift(3)) & (high.shift(2) >= high.shift(1)) & (high.shift(2) >= high.shift(4))
        is_swing_low = (low.shift(2) <= low.shift(3)) & (low.shift(2) <= low.shift(1)) & (low.shift(2) <= low.shift(4))
        
        sh = pd.Series(np.nan, index=df.index)
        sh[is_swing_high] = high.shift(2)[is_swing_high]
        
        sl = pd.Series(np.nan, index=df.index)
        sl[is_swing_low] = low.shift(2)[is_swing_low]
        
        return sh, sl
    
    def define_variables(self, df: pd.DataFrame):
        trend = self._get_trend(df)
        rsi = self._calculate_rsi(df)
        sh, sl = self.detect_swings(df)
        
        last_sh = sh.ffill().fillna(df['high'])
        last_sl = sl.ffill().fillna(df['low'])
        
        sh_rsi = rsi.where(sh.notna()).ffill().fillna(50)
        sl_rsi = rsi.where(sl.notna()).ffill().fillna(50)
        
        # --- Pre-calculate SL, TP & Validity exactly once spanning the sequence ---
        
        # Long Models
        sl_long = last_sl - self.spread_buffer
        risk_long_usd = df['close'] - sl_long
        valid_risk_long = (risk_long_usd > 0) & (risk_long_usd <= self.max_risk_usd)
        tp_long = df['close'] + (risk_long_usd * 2)
        
        # Short Models
        sl_short = last_sh + self.spread_buffer
        risk_short_usd = sl_short - df['close']
        valid_risk_short = (risk_short_usd > 0) & (risk_short_usd <= self.max_risk_usd)
        tp_short = df['close'] - (risk_short_usd * 2)
        
        return {
            'trend': trend,
            'rsi': rsi,
            'last_sh': last_sh,
            'last_sl': last_sl,
            'sh_rsi': sh_rsi,
            'sl_rsi': sl_rsi,
            'sl_long': sl_long,
            'tp_long': tp_long,
            'valid_risk_long': valid_risk_long,
            'sl_short': sl_short,
            'tp_short': tp_short,
            'valid_risk_short': valid_risk_short,
            'close': df['close']
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Long: Uptrend + RSI oversold + Near support"""
        uptrend = vars['trend'] == 1.0
        rsi_oversold = vars['rsi'] < 35
        near_support = vars['close'] <= (vars['last_sl'] * 1.002)
        valid_risk = vars['valid_risk_long']
        has_history = pd.Series(np.arange(len(df)) >= 200, index=df.index)
        
        entry = uptrend & rsi_oversold & near_support & valid_risk & has_history
        return entry.fillna(False).astype(bool)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Short: Downtrend + RSI overbought + Near resistance"""
        downtrend = vars['trend'] == -1.0
        rsi_overbought = vars['rsi'] > 65
        near_resistance = vars['close'] >= (vars['last_sh'] * 0.998)
        valid_risk = vars['valid_risk_short']
        has_history = pd.Series(np.arange(len(df)) >= 200, index=df.index)
        
        entry = downtrend & rsi_overbought & near_resistance & valid_risk & has_history
        return entry.fillna(False).astype(bool)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """SL/TP appropriately vectorized out across DataFrame"""
        trend = vars['trend'].fillna(0)
        
        # Merge sl based dynamically on trend column.
        sl = np.where(trend == 1.0, vars['sl_long'], vars['sl_short'])
        tp = np.where(trend == 1.0, vars['tp_long'], vars['tp_short'])
        
        return {
            'sl': pd.Series(sl, index=df.index).bfill().ffill().fillna(df['close'] * 0.99),
            'tp': pd.Series(tp, index=df.index).bfill().ffill().fillna(df['close'] * 1.01)
        }
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        return False
