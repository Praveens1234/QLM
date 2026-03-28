from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class MomentumBreakout_v1(Strategy):
    """
    Author: MCP Client (AI Agent)
    Description: MOMENTUM BREAKOUT - Follow strong momentum with tight risk.
    
    KEY INSIGHT:
    - XAUUSD is trending (2624 to 4063 in our dataset = 54% gain)
    - Previous mean-reversion approaches failed
    - We need to RIDE THE TREND, not fight it
    
    STRATEGY:
    1. Identify momentum breakouts (price breaking recent highs/lows)
    2. Enter on pullback to breakout level
    3. Tight stops, trail profits
    
    GOAL: Achieve 35%+ win rate with 1:2+ RRR
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate momentum and breakout indicators."""
        
        # ========== 1. BREAKOUT DETECTION ==========
        # Recent range
        lookback = 20
        recent_high = df['high'].rolling(lookback).max().shift(1)
        recent_low = df['low'].rolling(lookback).min().shift(1)
        
        # Breakout signals
        breakout_up = df['close'] > recent_high
        breakout_down = df['close'] < recent_low
        
        # ========== 2. MOMENTUM STRENGTH ==========
        # Rate of change
        roc_5 = df['close'].pct_change(5) * 100
        roc_10 = df['close'].pct_change(10) * 100
        
        # Strong momentum
        strong_up_momentum = roc_5 > 0.1  # 0.1% in 5 bars
        strong_down_momentum = roc_5 < -0.1
        
        # ========== 3. PULLBACK DETECTION ==========
        # After breakout, look for pullback to retest level
        breakout_up_confirmed = breakout_up.rolling(3).max().astype(bool)
        breakout_down_confirmed = breakout_down.rolling(3).max().astype(bool)
        
        # Pullback to recent high/low
        pullback_to_high = (df['low'] <= recent_high * 1.002) & (df['close'] > recent_high * 0.998)
        pullback_to_low = (df['high'] >= recent_low * 0.998) & (df['close'] < recent_low * 1.002)
        
        # ========== 4. TREND FILTER ==========
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        ema_100 = df['close'].ewm(span=100, adjust=False).mean()
        
        uptrend = (ema_20 > ema_50) & (ema_50 > ema_100)
        downtrend = (ema_20 < ema_50) & (ema_50 < ema_100)
        
        # ========== 5. VOLUME-LIKE CONFIRMATION ==========
        # Use range as volume proxy
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # Range expansion
        range_ratio = tr / atr
        expanding = range_ratio > 1.5
        
        # ========== 6. ENTRY ZONE ==========
        # Define safe entry zones
        safe_long_zone = df['close'] > ema_20
        safe_short_zone = df['close'] < ema_20
        
        return {
            'recent_high': recent_high,
            'recent_low': recent_low,
            'breakout_up': breakout_up,
            'breakout_down': breakout_down,
            'roc_5': roc_5,
            'roc_10': roc_10,
            'strong_up_momentum': strong_up_momentum,
            'strong_down_momentum': strong_down_momentum,
            'breakout_up_confirmed': breakout_up_confirmed,
            'breakout_down_confirmed': breakout_down_confirmed,
            'pullback_to_high': pullback_to_high,
            'pullback_to_low': pullback_to_low,
            'uptrend': uptrend,
            'downtrend': downtrend,
            'atr': atr,
            'expanding': expanding,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'ema_100': ema_100,
            'safe_long_zone': safe_long_zone,
            'safe_short_zone': safe_short_zone
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        LONG: Breakout + Pullback + Uptrend + Range expansion.
        """
        
        # OPTION 1: Fresh breakout with momentum
        fresh_breakout = vars['breakout_up'] & vars['strong_up_momentum'] & vars['expanding']
        
        # OPTION 2: Pullback entry after confirmed breakout
        pullback_entry = vars['breakout_up_confirmed'].shift(1).fillna(False) & vars['pullback_to_high'] & vars['uptrend']
        
        # OPTION 3: Trend continuation
        trend_continuation = vars['uptrend'] & vars['strong_up_momentum'] & vars['safe_long_zone']
        
        # Combine: Any valid entry type
        entry = fresh_breakout | pullback_entry | trend_continuation
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """
        SHORT: Breakout + Pullback + Downtrend + Range expansion.
        """
        
        fresh_breakout = vars['breakout_down'] & vars['strong_down_momentum'] & vars['expanding']
        pullback_entry = vars['breakout_down_confirmed'].shift(1).fillna(False) & vars['pullback_to_low'] & vars['downtrend']
        trend_continuation = vars['downtrend'] & vars['strong_down_momentum'] & vars['safe_short_zone']
        
        entry = fresh_breakout | pullback_entry | trend_continuation
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """
        1:2.5 RRR - Favorable for trend following.
        """
        sl_distance = vars['atr'] * 1.2
        tp_distance = vars['atr'] * 3.0
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit on trend break."""
        trend_broken = vars['ema_20'] < vars['ema_50']
        momentum_lost = vars['roc_5'] < -0.05
        
        return (trend_broken | momentum_lost).fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit on trend break."""
        trend_broken = vars['ema_20'] > vars['ema_50']
        momentum_lost = vars['roc_5'] > 0.05
        
        return (trend_broken | momentum_lost).fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Fallback exit."""
        idx = trade['current_idx']
        
        if trade['direction'] == 'long':
            if vars['ema_20'].iloc[idx] < vars['ema_50'].iloc[idx]:
                return True
        else:
            if vars['ema_20'].iloc[idx] > vars['ema_50'].iloc[idx]:
                return True
        
        return False