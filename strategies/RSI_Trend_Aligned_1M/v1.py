from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSI_Trend_Aligned_1M(Strategy):
    """
    Author: MCP Client
    Description: RSI-based trend-aligned strategy with 1:1 RRR for 1M timeframe.
    - Uses EMA 20/50 for trend filter
    - RSI 14 for entry signals (oversold in uptrend, overbought in downtrend)
    - ATR-based SL/TP with fixed 1:1 Reward:Risk ratio
    - Designed for high-quality trades with ~10 trades/day on XAUUSD
    """
    
    def define_variables(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Calculate all indicators globally using vectorized operations."""
        
        # RSI 14 calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs))
        
        # EMAs for trend filtering
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR for dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean()
        
        return {
            'rsi_14': rsi_14,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'atr_14': atr_14
        }
    
    def entry_long(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Long entry: Uptrend + RSI oversold turning up."""
        # Trend filter: uptrend (EMA 20 > EMA 50) and price above EMAs
        uptrend = (vars['ema_20'] > vars['ema_50']) & \
                  (df['close'] > vars['ema_20']) & \
                  (df['close'] > vars['ema_50'])
        
        # RSI signal: oversold (below 35) and turning up
        rsi_oversold = vars['rsi_14'] < 35
        rsi_turning_up = vars['rsi_14'] > vars['rsi_14'].shift(1)
        
        entry = uptrend & rsi_oversold & rsi_turning_up
        
        return entry.fillna(False)
    
    def entry_short(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Short entry: Downtrend + RSI overbought turning down."""
        # Trend filter: downtrend (EMA 20 < EMA 50) and price below EMAs
        downtrend = (vars['ema_20'] < vars['ema_50']) & \
                    (df['close'] < vars['ema_20']) & \
                    (df['close'] < vars['ema_50'])
        
        # RSI signal: overbought (above 65) and turning down
        rsi_overbought = vars['rsi_14'] > 65
        rsi_turning_down = vars['rsi_14'] < vars['rsi_14'].shift(1)
        
        entry = downtrend & rsi_overbought & rsi_turning_down
        
        return entry.fillna(False)
    
    def risk_model(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> dict[str, pd.Series]:
        """ATR-based SL/TP with fixed 1:1 RRR."""
        
        # SL distance: 2x ATR (adjustable via parameters)
        atr_multiplier = self.parameters.get('atr_sl_multiplier', 2.0)
        sl_distance = vars['atr_14'] * atr_multiplier
        
        # TP distance: 2x ATR (1:1 RRR - same as SL)
        tp_distance = sl_distance
        
        # For short entries (will be handled directionally by engine)
        # Note: Engine will apply these correctly based on direction
        
        return {
            'sl_distance': sl_distance,  # Use distance mode
            'tp_distance': tp_distance   # 1:1 RRR
        }
    
    def exit_long_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit long if price crosses below EMA 20 (trend reversal)."""
        exit = df['close'] < vars['ema_20']
        return exit.fillna(False)
    
    def exit_short_signal(self, df: pd.DataFrame, vars: dict[str, pd.Series]) -> pd.Series:
        """Exit short if price crosses above EMA 20 (trend reversal)."""
        exit = df['close'] > vars['ema_20']
        return exit.fillna(False)
    
    def exit(self, df: pd.DataFrame, vars: dict[str, pd.Series], trade: dict) -> bool:
        """Dynamic exit: RSI extreme reset (optional)."""
        # Default dynamic exit based on RSI extreme reset
        idx = trade['current_idx']
        if idx < 0 or idx >= len(df):
            return False
        
        if trade['direction'] == 'long':
            # Exit long if RSI reaches overbought (>70) (momentum reversal)
            if vars['rsi_14'][idx] > 70:
                return True
        elif trade['direction'] == 'short':
            # Exit short if RSI reaches oversold (<30) (momentum reversal)
            if vars['rsi_14'][idx] < 30:
                return True
        
        return False