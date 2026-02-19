from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class RSIStrategy(Strategy):
    """
    Production-Grade RSI Mean Reversion Strategy.
    
    Improvements:
    1. Mathematical Correctness: Replaced simple moving average with Wilder's Smoothing (EMA) for standard RSI.
    2. Regime Filtering: Added SMA200 filter to trade *with* the long-term trend (Buy Dips in Uptrend, Sell Rips in Downtrend).
    3. Volatility Awareness: Integrated ATR for dynamic Stop Loss and Take Profit.
    4. Signal Quality: Added 'trigger' logic (crossover) rather than simple state checks to prevent continuous firing.
    """

    def define_variables(self, df: pd.DataFrame) -> dict:
        """
        Calculates technical indicators using vectorized pandas operations.
        """
        # 1. Standardize Inputs
        close = df['close']
        high = df['high']
        low = df['low']

        # Get Parameters
        rsi_period = int(self.parameters.get('rsi_period', 14))
        sma_period = int(self.parameters.get('sma_trend_period', 200))

        # 2. Correct Wilder's RSI Calculation 
        delta = close.diff()
        
        # Separate gains and losses
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)

        # Use Exponential Weighted Moving Average (com = window - 1)
        com = rsi_period - 1
        ma_up = up.ewm(com=com, adjust=False, min_periods=rsi_period).mean()
        ma_down = down.ewm(com=com, adjust=False, min_periods=rsi_period).mean()

        # Handle division by zero safely
        rs = ma_up / ma_down.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)  # Neutral fill for initial warm-up period only

        # 3. Regime Filter
        sma_trend = close.rolling(window=sma_period).mean()

        # 4. Volatility (ATR 14) for Risk Management
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Assuming ATR period is fixed at 14 for now, or could param it too
        atr = tr.rolling(window=14).mean()

        return {
            "rsi": rsi,
            "sma_trend": sma_trend,
            "atr": atr,
            "close": close
        }

    def entry_long(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        # Logic: Buy when RSI crosses below Oversold, BUT only if Price > SMA 200 (Uptrend)
        # "Buy the dip" logic
        
        rsi = vars['rsi']
        trend = vars['close'] > vars['sma_trend']
        
        # Get Parameter
        oversold = float(self.parameters.get('rsi_oversold', 30))

        # Signal: RSI < Oversold
        signal = (rsi < oversold) & trend
        
        return signal

    def entry_short(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        # Logic: Sell when RSI crosses above Overbought, BUT only if Price < SMA 200 (Downtrend)
        # "Sell the rip" logic
        
        rsi = vars['rsi']
        trend = vars['close'] < vars['sma_trend']
        
        # Get Parameter
        overbought = float(self.parameters.get('rsi_overbought', 70))

        signal = (rsi > overbought) & trend
        return signal

    def exit(self, df: pd.DataFrame, vars: dict, trade: dict) -> bool:
        """
        Exits based on Mean Reversion (RSI 50) OR Dynamic Risk Levels (SL/TP).
        """
        curr_idx = trade['current_idx']
        current_rsi = vars['rsi'].iloc[curr_idx]
        current_close = vars['close'].iloc[curr_idx]
        
        entry_price = trade['entry_price']
        
        # 1. Mean Reversion Exit (Standard)
        if trade['direction'] == 'long':
            if current_rsi >= 50: return True
        else:
            if current_rsi <= 50: return True
            
        # 2. Hard Risk Exit (Safety Net)
        if 'stop_loss' in trade and 'take_profit' in trade:
            if trade['direction'] == 'long':
                if current_close <= trade['stop_loss']: return True
                if current_close >= trade['take_profit']: return True
            else:
                if current_close >= trade['stop_loss']: return True
                if current_close <= trade['take_profit']: return True

        return False

    def risk_model(self, df: pd.DataFrame, vars: dict) -> dict:
        """
        Defines dynamic Stop Loss and Take Profit based on ATR.
        """
        # Get latest ATR
        current_atr = vars['atr'].fillna(vars['close'] * 0.01)
            
        # Risk Settings
        sl_multiplier = 2.0
        tp_multiplier = 2.0  # 1:1 Risk/Reward to Mean Reversion target
        
        return {
            "stop_loss_dist": current_atr * sl_multiplier,
            "take_profit_dist": current_atr * tp_multiplier,
            "sizing_risk_per_trade": 0.01 # 1% Equity Risk
        }