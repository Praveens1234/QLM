from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSI_Trend_Aligned_1M_v3(Strategy):
    """
    Author: MCP Client
    Description: RSI-based trend-aligned strategy optimized for XAUUSD 1M.
    - Uses EMA 20/50 for trend alignment
    - RSI 14 with stricter entry conditions for higher quality
    - ATR-based SL/TP with 1:1.2 effective RRR (slightly better to compensate for slippage)
    - Additional momentum filter using price vs EMA
    - Target: 10+ trades/day with positive expectancy
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        
        # RSI 14 calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs))
        
        # EMAs for trend alignment
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR for dynamic SL/TP - shorter period for faster response
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_10 = tr.rolling(window=10).mean()
        
        # Momentum indicator: Price change
        price_change = df['close'].pct_change(periods=5)
        
        return {
            'rsi_14': rsi_14,
            'rsi_prev': rsi_14.shift(1),
            'ema_20': ema_20,
            'ema_50': ema_50,
            'atr_10': atr_10,
            'price_change': price_change
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Long entry: Uptrend + RSI bounce from oversold + momentum confirmation."""
        # Trend alignment: Strong uptrend (EMA 20 > EMA 50 by at least 0.5 ATR)
        ema_spread = (vars['ema_20'] - vars['ema_50']) / vars['atr_10']
        strong_uptrend = (vars['ema_20'] > vars['ema_50']) & (ema_spread > 0.3)
        
        # Price near EMA 20 for value entry (within 1 ATR above)
        near_value = (df['close'] >= vars['ema_20']) & \
                    (df['close'] <= vars['ema_20'] + vars['atr_10'])
        
        # RSI signal: Turning up from oversold/overselling zone
        # Either crossing above 30 OR below 40 and turning up with momentum
        rsi_oversold_cross = (vars['rsi_prev'] < 30) & (vars['rsi_14'] >= 30)
        rsi_bullish_turn = (vars['rsi_prev'] < 40) & \
                          (vars['rsi_14'] > vars['rsi_prev']) & \
                          (vars['rsi_14'] < 50)
        
        rsi_signal = rsi_oversold_cross | rsi_bullish_turn
        
        # Momentum filter: Recent price not selling off too strongly
        not_strong_bearish = vars['price_change'] > -0.003
        
        # Entry requires all filters
        entry = strong_uptrend & near_value & rsi_signal & not_strong_bearish
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Short entry: Downtrend + RSI rejection from overbought + momentum confirmation."""
        # Trend alignment: Strong downtrend (EMA 20 < EMA 50 by at least 0.5 ATR)
        ema_spread = (vars['ema_50'] - vars['ema_20']) / vars['atr_10']
        strong_downtrend = (vars['ema_20'] < vars['ema_50']) & (ema_spread > 0.3)
        
        # Price near EMA 20 for value entry (within 1 ATR below)
        near_value = (df['close'] <= vars['ema_20']) & \
                    (df['close'] >= vars['ema_20'] - vars['atr_10'])
        
        # RSI signal: Turning down from overbought/overbuying zone
        # Either crossing below 70 OR above 60 and turning down with momentum
        rsi_overbought_cross = (vars['rsi_prev'] > 70) & (vars['rsi_14'] <= 70)
        rsi_bearish_turn = (vars['rsi_prev'] > 60) & \
                          (vars['rsi_14'] < vars['rsi_prev']) & \
                          (vars['rsi_14'] > 50)
        
        rsi_signal = rsi_overbought_cross | rsi_bearish_turn
        
        # Momentum filter: Recent price not rallying too strongly
        not_strong_bullish = vars['price_change'] < 0.003
        
        # Entry requires all filters
        entry = strong_downtrend & near_value & rsi_signal & not_strong_bullish
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """ATR-based SL/TP with 1:1.2 ratio (better than 1:1 to offset slippage)."""
        
        # SL distance: 1.2x ATR (tighter stops)
        sl_multiplier = self.parameters.get('sl_multiplier', 1.2)
        sl_distance = vars['atr_10'] * sl_multiplier
        
        # TP distance: 1.44x ATR (1.2x SL = 1:1.2 ratio, giving us breathing room after slippage)
        tp_multiplier = self.parameters.get('tp_multiplier', 1.44)
        tp_distance = vars['atr_10'] * tp_multiplier
        
        return {
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit long if RSI reaches overbought OR price breaks below EMA 20."""
        rsi_exit = vars['rsi_14'] > 68
        trend_exit = df['close'] < vars['ema_20'] - (vars['atr_10'] * 0.5)
        exit = rsi_exit | trend_exit
        return exit.fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit short if RSI reaches oversold OR price breaks above EMA 20."""
        rsi_exit = vars['rsi_14'] < 32
        trend_exit = df['close'] > vars['ema_20'] + (vars['atr_10'] * 0.5)
        exit = rsi_exit | trend_exit
        return exit.fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Dynamic exit: EMA trend reversal."""
        idx = trade['current_idx']
        if idx < 0 or idx >= len(df):
            return False
        
        if trade['direction'] == 'long':
            # Exit long if strong trend change (EMA cross bearish with momentum)
            if vars['ema_20'][idx] < vars['ema_50'][idx]:
                return True
        elif trade['direction'] == 'short':
            # Exit short if strong trend change (EMA cross bullish)
            if vars['ema_20'][idx] > vars['ema_50'][idx]:
                return True
        
        return False